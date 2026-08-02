"""Image downloader contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.domain.entities.product import Product


class ImageDownloaderPort(ABC):
    """Downloads every image of a product into its own folder."""

    @abstractmethod
    def download(self, product: Product) -> list[Path]:
        """Download all product images and return their relative paths."""
