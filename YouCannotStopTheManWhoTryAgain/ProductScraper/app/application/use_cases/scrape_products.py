"""Main scraping orchestration use case."""
from __future__ import annotations

import logging
from pathlib import Path

from app.application.ports.exporter import ExporterPort
from app.application.ports.image_downloader import ImageDownloaderPort
from app.application.ports.scraper import ScraperPort
from app.application.ports.state_repository import StateRepositoryPort
from app.application.services.progress import ProgressReporter
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

    def execute(self) -> Path:
        """Run the full pipeline and return the exported file path."""
        self._state.load()

        if self._settings.resume:
            self._logger.info("Resume mode enabled; previously saved products will be reused.")
        else:
            self._repository.clear()
            self._state.reset()
            self._state.save()

        product_urls = self._scraper.discover_product_urls(self._settings.scraper.category_urls)
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
        bar = self._progress.products(len(pending))
        try:
            for url in pending:
                bar.set_description_str(f"Scraping {url}")
                product = self._scrape_one(url)
                if product is None:
                    continue
                image_paths = self._image_downloader.download(product)
                product.images = [str(path) for path in image_paths]
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
