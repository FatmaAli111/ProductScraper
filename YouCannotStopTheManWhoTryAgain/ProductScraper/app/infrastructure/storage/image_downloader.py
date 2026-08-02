"""Concurrent image downloader with resume and de-duplication."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.application.ports.image_downloader import ImageDownloaderPort
from app.application.ports.state_repository import StateRepositoryPort
from app.application.services.progress import ProgressReporter
from app.domain.entities.product import Product
from app.infrastructure.config.settings import DownloadSettings, OutputSettings
from app.infrastructure.http.http_client import HttpClient
from app.infrastructure.storage.image_storage import ImageStorage


class ImageDownloader(ImageDownloaderPort):
    """Downloads every gallery image using a thread pool."""

    def __init__(
        self,
        http: HttpClient,
        storage: ImageStorage,
        state: StateRepositoryPort,
        settings: DownloadSettings,
        output: OutputSettings,
        progress: ProgressReporter,
        logger: logging.Logger,
    ) -> None:
        self._http = http
        self._storage = storage
        self._state = state
        self._settings = settings
        self._output = output
        self._progress = progress
        self._logger = logger

    def download(self, product: Product) -> list[Path]:
        """Download all images of a product, skipping work already done."""
        unique_urls = list(dict.fromkeys(product.image_urls))
        urls = unique_urls[: self._settings.max_images_per_product]
        if not urls:
            return []

        directory = self._storage.product_directory(product.name)
        pending: list[tuple[int, str]] = []
        for index, url in enumerate(urls, start=1):
            if not self._state.is_image_downloaded(product.url, url):
                pending.append((index, url))

        if not pending:
            self._logger.debug("All images already downloaded for %s", product.name)
            return []

        self._logger.info("Downloading %d image(s) for %s", len(pending), product.name)
        downloaded: list[Path] = []
        bar = self._progress.images(
            len(pending),
            description=f"Images: {product.name[:40]}",
        )
        try:
            with ThreadPoolExecutor(max_workers=self._settings.threads) as pool:
                futures = {
                    pool.submit(self._download_one, product, directory, index, url): (index, url)
                    for index, url in pending
                }
                for future in as_completed(futures):
                    relative = future.result()
                    if relative is not None:
                        downloaded.append(relative)
                    bar.update(1)
        finally:
            bar.close()

        return sorted(downloaded)

    def _download_one(
        self,
        product: Product,
        directory: Path,
        index: int,
        url: str,
    ) -> Path | None:
        try:
            data, content_type = self._http.get_bytes(url, timeout=self._settings.timeout)
        except Exception as exc:
            self._logger.error("Failed to download %s: %s", url, exc)
            return None

        path = self._storage.resolve_path(directory, index, url, content_type)
        if path.exists():
            self._logger.debug("Image already on disk, skipping %s", path)
        else:
            self._storage.save(path, data)

        self._state.mark_image_downloaded(product.url, url)
        return self._relative(path)

    def _relative(self, path: Path) -> Path:
        try:
            return path.relative_to(self._output.directory)
        except ValueError:
            return path
