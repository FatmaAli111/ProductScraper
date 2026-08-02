"""Main scraping orchestration use case."""
from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from app.application.ports.exporter import ExporterPort
from app.application.ports.image_downloader import ImageDownloaderPort
from app.application.ports.scraper import ScraperPort
from app.application.ports.state_repository import StateRepositoryPort
from app.application.services.progress import ProgressReporter
from app.domain.entities.product import Product
from app.domain.repositories.product_repository import ProductRepository
from app.infrastructure.config.settings import Settings
from app.infrastructure.http.retry import retry_call


class ScrapeProductsUseCase:
    """Orchestrates discover -> scrape -> download -> export."""

    def __init__(
        self,
        *,
        scraper: ScraperPort,
        image_downloader: ImageDownloaderPort,
        repository: ProductRepository,
        exporter: ExporterPort,
        state: StateRepositoryPort,
        progress: ProgressReporter,
        settings: Settings,
        logger: logging.Logger,
    ) -> None:
        self._scraper = scraper
        self._image_downloader = image_downloader
        self._repository = repository
        self._exporter = exporter
        self._state = state
        self._progress = progress
        self._settings = settings
        self._logger = logger
        self._failed_products = 0

    def execute(self) -> Path:
        """Run the full pipeline and return the exported file path."""
        started = time.monotonic()
        try:
            return self._run()
        finally:
            close = getattr(self._scraper, "close", None)
            if callable(close):
                close()
            self._report(time.monotonic() - started)

    def _run(self) -> Path:
        self._state.load()

        if self._settings.resume:
            self._logger.info("Resume mode enabled; previously saved products will be reused.")
        else:
            self._clear_output()
            self._repository.clear()
            self._state.reset()
            self._state.save()

        product_urls = self._scraper.discover_product_urls(self._settings.scraper.category_urls)
        max_products = self._settings.scraper.max_products
        if max_products:
            product_urls = product_urls[:max_products]
        remaining = [url for url in product_urls if not self._state.is_product_scraped(url)]
        self._logger.info(
            "Discovered %d product URLs (%d already done, %d pending).",
            len(product_urls),
            len(product_urls) - len(remaining),
            len(remaining),
        )

        if remaining:
            self._scrape_pending(remaining)

        exported = self._exporter.export(self._repository.get_all())
        self._logger.info("Exported %d products to %s.", self._repository.count(), exported)
        return exported

    def _scrape_pending(self, pending: list[str]) -> None:
        seen_skus: set[str] = set()
        bar = self._progress.products(len(pending))
        try:
            for url in pending:
                bar.set_description_str(f"Scraping {url}")
                product = self._scrape_one(url)
                if product is None:
                    self._failed_products += 1
                    bar.update(1)
                    continue

                if product.sku in seen_skus:
                    self._logger.warning("Skipping duplicate SKU %s (%s).", product.sku, url)
                    self._state.mark_product_scraped(url)
                    self._state.save()
                    bar.update(1)
                    continue
                seen_skus.add(product.sku)

                image_paths = self._image_downloader.download(product)
                product.images = [str(path) for path in image_paths]
                self._attach_local_paths(product, image_paths)
                self._repository.save(product)
                self._state.mark_product_scraped(url)
                self._state.save()
                bar.update(1)
        except KeyboardInterrupt:
            self._state.save()
            self._logger.warning("Interrupted. Re-run with the same config to resume.")
            raise
        finally:
            bar.close()

    def _attach_local_paths(self, product: Product, image_paths: list[Path]) -> None:
        if not image_paths:
            return
        first = image_paths[0]
        folder = first.parent
        base = Path(self._settings.output.directory).name
        product.local_folder = f"{base}/{folder.as_posix()}/"
        product.main_image = first.name
        product.gallery_images = [path.name for path in image_paths[1:]]

    def _scrape_one(self, url: str):
        """Scrape a product page with retries, swallowing recoverable errors."""
        try:
            return retry_call(
                self._settings.http.retries,
                self._scraper.scrape_product,
                url,
                logger=self._logger,
                backoff=self._settings.http.retry_backoff,
                max_backoff=self._settings.http.max_retry_delay,
            )
        except Exception as exc:
            self._logger.error("Skipping %s: %s", url, exc)
            return None

    def _clear_output(self) -> None:
        """Wipe previous artifacts so a fresh run starts clean."""
        output = self._settings.output
        for path in [output.images_dir, output.excel_file, output.products_cache, output.state_file]:
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                elif path.exists():
                    path.unlink()
            except OSError as exc:
                self._logger.warning("Could not clear %s: %s", path, exc)

    def _report(self, elapsed: float) -> None:
        products = self._repository.get_all()
        images_downloaded = sum(len(product.images) for product in products)
        failed_images = getattr(self._image_downloader, "failed_count", 0)
        category_url = self._settings.scraper.category_urls[0] if self._settings.scraper.category_urls else ""
        lines = [
            "",
            "=" * 60,
            "SCRAPING REPORT",
            "=" * 60,
            f"Category URL        : {category_url}",
            f"Products Requested  : {self._settings.scraper.max_products}",
            f"Products Downloaded : {len(products)}",
            f"Images Downloaded   : {images_downloaded}",
            f"Failed Products     : {self._failed_products}",
            f"Failed Images       : {failed_images}",
            f"Elapsed Time        : {self._format_duration(elapsed)}",
            f"Excel Path          : {self._settings.output.excel_file}",
            f"Images Path         : {self._settings.output.images_dir}",
            "=" * 60,
        ]
        print("\n".join(lines))
        self._logger.info("Report: %d products, %d images, %d failed products, %d failed images.",
                          len(products), images_downloaded, self._failed_products, failed_images)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        seconds = int(seconds)
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
