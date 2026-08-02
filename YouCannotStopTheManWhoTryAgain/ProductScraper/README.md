# Product Scraper

A production-ready desktop scraping application that crawls e-commerce stores,
downloads original-quality product images, and exports everything into an
Excel file (`products.xlsx`) ready to be imported into **Salla**.

Built as a real, reusable software project: Clean Architecture, SOLID, fully
typed, logged, resumable, and designed so that adding a new storefront is a
one-file change.

## Features

- Category page crawling with optional pagination
- Per-product page scraping (name, SKU, description, prices, category, brand,
  tags, variants, colors, sizes, availability, weight, dimensions, URL)
- Original-quality gallery images downloaded into `output/images/<Product Name>/`
- Parallel image downloads via `ThreadPoolExecutor`
- Retry with exponential backoff on transient failures (429/5xx/network)
- **Resume capability**: interrupted runs continue where they left off
- **No duplicated downloads**: already-scraped products and existing image
  files are skipped automatically
- Progress bars via `tqdm`
- Structured logging to console and `output/scraper.log`
- Excel export via `openpyxl` (image paths only, never embedded images)
- Config-driven via `config.yaml` with a pluggable scraper registry

## Requirements

- Windows / macOS / Linux
- Python 3.12+

## Installation

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
```

On macOS/Linux the activation command is `source .venv/bin/activate`.

## Usage

```powershell
.venv\Scripts\python -m app.main
```

Options:

| Flag | Description |
| --- | --- |
| `--config PATH` | Path to the YAML configuration file (default `config.yaml`) |
| `--scraper NAME` | Override the scraper selected in the config |
| `--output DIR` | Override the output directory |
| `--threads N` | Override the number of image download threads |
| `--resume` / `--no-resume` | Enable / disable resume mode |
| `--no-progress` | Hide progress bars |

Example:

```powershell
.venv\Scripts\python -m app.main --scraper template --threads 16 --output output --resume
```

## Configuration

Everything lives in [`config.yaml`](config.yaml):

- `resume` — reuse previously saved progress
- `scraper.name` — which scraper implementation to use
- `scraper.category_urls` — the category pages to start from
- `scraper.pagination` — follow "next page" links (with a safety cap)
- `scraper.selectors` — CSS selectors the `template` scraper uses
- `http` — user-agent, timeout, SSL verification, retries and backoff
- `download` — concurrency, timeouts, gallery cap
- `output` — where everything is written
- `logging` — log level and format
- `ui.show_progress` — toggle progress bars

## Output

```
output/
├── images/
│   └── <Product Name>/
│       ├── 01_original.jpg
│       ├── 02_gallery.jpg
│       └── ...
├── products.xlsx
├── state.json            # progress tracker (used for resume)
├── products_cache.json   # scraped product data (survives restarts)
└── scraper.log
```

`products.xlsx` contains one row per product with columns: Name, SKU,
Description, Price, Sale Price, Category, Brand, Tags, Colors, Sizes,
Availability, Weight, Dimensions, Product URL, **Images** (relative paths,
newline-separated — no images are embedded), and Variants (JSON).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ presentation/  cli.py · logger.py · main.py (composition)   │
├─────────────────────────────────────────────────────────────┤
│ application/   use_cases/scrape_products.py                 │
│                ports/ (scraper, image_downloader, exporter, │
│                       state_repository) · services/progress │
├─────────────────────────────────────────────────────────────┤
│ domain/        entities (Product, ProductVariant)           │
│                repositories/product_repository.py           │
├─────────────────────────────────────────────────────────────┤
│ infrastructure/ http/ · scrapers/ · storage/ · config/      │
└─────────────────────────────────────────────────────────────┘
```

Dependencies point **inward**: the application layer depends on interfaces
(ports) defined in the application layer, and the infrastructure layer
provides concrete adapters. The domain layer has no imports from any
framework.

## Adding a new website scraper

Adding another storefront takes one new file plus config.

1. Create `app/infrastructure/scrapers/example.py`:

```python
import logging

from app.domain.entities.product import Product
from app.infrastructure.config.settings import ScraperSettings
from app.infrastructure.http.http_client import HttpClient
from app.infrastructure.scrapers.base import BaseScraper
from app.infrastructure.scrapers.registry import register


@register("example")  # this name goes in config.yaml -> scraper.name
class ExampleScraper(BaseScraper):

    def __init__(self, http: HttpClient, settings: ScraperSettings, logger: logging.Logger) -> None:
        super().__init__(http, settings, logger)

    def scrape_product(self, url: str) -> Product:
        soup = self._http.get_soup(url)
        return Product(
            name=self._text(soup, self._selectors.get("name", "")),
            sku=self._text(soup, self._selectors.get("sku", "")),
            url=url,
            description=self._text(soup, self._selectors.get("description", "")),
            price=self._price(soup, self._selectors.get("price", "")),
            sale_price=self._price(soup, self._selectors.get("sale_price", "")),
            category=self._text(soup, self._selectors.get("category", "")),
            brand=self._text(soup, self._selectors.get("brand", "")),
            tags=self._list_texts(soup, self._selectors.get("tags", "")),
            colors=self._list_texts(soup, self._selectors.get("colors", "")),
            sizes=self._list_texts(soup, self._selectors.get("sizes", "")),
            availability=self._available(soup),
            weight=self._text(soup, self._selectors.get("weight", "")),
            dimensions=self._text(soup, self._selectors.get("dimensions", "")),
            image_urls=self._image_urls(soup, url),
        )
```

2. In `config.yaml`, set `scraper.name: example` and point `category_urls` at
   the store. Product link discovery, pagination, image downloading, resume,
   de-duplication and export are inherited from `BaseScraper` and the pipeline.

## How resume works

- After each successful product, `state.json` and `products_cache.json` are
  updated.
- On restart with `resume: true`, products already in the cache are re-exported
  and product pages marked as scraped are skipped.
- Images already on disk (or marked in state) are never downloaded twice.

## Development

```powershell
.venv\Scripts\python -m pytest
```

Run the test suite with:

```powershell
.venv\Scripts\python -m pytest -q
```
