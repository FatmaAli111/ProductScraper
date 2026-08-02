"""Concurrent image downloader with resume, retries and de-duplication."""
from __future__ import annotations

import logging
import re
import time
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
    """Downloads every gallery image using a thread pool.

    Files land in ``output/images/<Product Name>_<SKU>/`` as ``main.jpg``
    followed by ``gallery_01.jpg``, ``gallery_02.jpg``, ...
    """

    _PRODUCT_ID_RE = re.compile(r"/p(\d+)")

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
        self._failed_count = 0

    @property
    def failed_count(self) -> int:
        return self._failed_count

    def download(self, product: Product) -> list[Path]:
        """Download all images of a product, skipping work already done."""
        unique_urls = list(dict.fromkeys(product.image_urls))
        urls = unique_urls[: self._settings.max_images_per_product]
        if not urls:
            return []

        product_id = self._product_id(product.url)
        directory = self._storage.product_directory(product.name, product.sku, product_id)

        pending: list[tuple[int, str]] = []
        for index, url in enumerate(urls, start=1):
            if not self._state.is_image_downloaded(product.url, url):
                pending.append((index, url))

        if not pending:
            self._logger.debug("All images already downloaded for %s", product.name)
            return self._local_paths(directory, urls)

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

        return self._merge(downloaded, directory, urls)

    def _download_one(
        self,
        product: Product,
        directory: Path,
        index: int,
        url: str,
    ) -> Path | None:
        for attempt in range(self._settings.retries):
            try:
                data, content_type = self._http.get_bytes(url, timeout=self._settings.timeout)
                path = directory / self._storage.image_filename(index, url, content_type)
                if path.exists():
                    self._logger.debug("Image already on disk, skipping %s", path)
                else:
                    self._storage.save(path, data)
            except OSError as exc:
                # Transient file locks (e.g. antivirus scans) on Windows.
                self._logger.warning(
                    "Could not write image for %s (attempt %d/%d): %s",
                    url,
                    attempt + 1,
                    self._settings.retries,
                    exc,
                )
                time.sleep(1.5 * (attempt + 1))
                continue
            except Exception as exc:
                self._failed_count += 1
                self._logger.error("Failed to download %s: %s", url, exc)
                return None

            self._state.mark_image_downloaded(product.url, url)
            return self._relative(path)

        self._failed_count += 1
        self._logger.error("Giving up on %s after %d attempts.", url, self._settings.retries)
        return None

    def _local_paths(self, directory: Path, urls: list[str]) -> list[Path]:
        """Reconstruct the local files for already-downloaded galleries."""
        paths: list[Path] = []
        for index, url in enumerate(urls, start=1):
            path = directory / self._storage.image_filename(index, url, None)
            if path.exists():
                paths.append(self._relative(path))
        return paths

    def _merge(self, downloaded: list[Path], directory: Path, urls: list[str]) -> list[Path]:
        """Order the local files by gallery position, main image first."""
        files = {path.name: path for path in downloaded}
        ordered: list[Path] = []
        for index, url in enumerate(urls, start=1):
            name = self._storage.image_filename(index, url, None)
            if name in files:
                ordered.append(files[name])
        return ordered

    @staticmethod
    def _product_id(url: str) -> str:
        match = ImageDownloader._PRODUCT_ID_RE.search(url)
        return match.group(1) if match else ""

    def _relative(self, path: Path) -> Path:
        try:
            return path.relative_to(self._output.directory)
        except ValueError:
            return path
