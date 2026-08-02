"""Composition root and CLI entry point."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from app.application.services.progress import ProgressReporter
from app.application.use_cases.scrape_products import ScrapeProductsUseCase
from app.infrastructure.config.settings import Settings, SettingsLoader
from app.infrastructure.http.http_client import HttpClient
from app.infrastructure.scrapers.registry import build_scraper
from app.infrastructure.storage.excel_exporter import ExcelExporter
from app.infrastructure.storage.image_downloader import ImageDownloader
from app.infrastructure.storage.image_storage import ImageStorage
from app.infrastructure.storage.json_state_repository import JsonStateRepository
from app.infrastructure.storage.product_repository import JsonProductRepository
from app.presentation.cli import apply_overrides, build_parser
from app.presentation.logger import configure_logging


def bootstrap(settings: Settings) -> ScrapeProductsUseCase:
    """Wire the dependency graph (composition root)."""
    logger = configure_logging(settings.logging, settings.output.log_file)
    logger.info("Initializing scraper '%s'", settings.scraper.name)

    http_client = HttpClient(settings.http, logger)
    scraper = build_scraper(settings.scraper, http_client, logger)
    storage = ImageStorage(settings.output)
    state = JsonStateRepository(settings.output.state_file)
    repository = JsonProductRepository(settings.output.products_cache)
    image_downloader = ImageDownloader(
        http_client,
        storage,
        state,
        settings.download,
        settings.output,
        ProgressReporter(settings.ui.show_progress),
        logger,
    )
    exporter = ExcelExporter(settings.output, logger)
    progress = ProgressReporter(settings.ui.show_progress)

    return ScrapeProductsUseCase(
        scraper=scraper,
        image_downloader=image_downloader,
        repository=repository,
        exporter=exporter,
        state=state,
        progress=progress,
        settings=settings,
        logger=logger,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = SettingsLoader(Path(args.config)).load()
    settings = apply_overrides(settings, args)

    use_case = bootstrap(settings)
    try:
        exported = use_case.execute()
    except KeyboardInterrupt:
        print("\nInterrupted. Re-run with the same config to resume.", file=sys.stderr)
        return 130
    except Exception as exc:
        logging.getLogger("product_scraper").exception("Fatal error: %s", exc)
        return 1

    print(f"\nDone. Products exported to: {exported}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
