"""File system layout and persistence for downloaded images."""
from __future__ import annotations

import re
from pathlib import Path

from app.infrastructure.config.settings import OutputSettings

_IMAGE_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".avif",
    ".bmp",
    ".tiff",
}
_CONTENT_TYPE_SUFFIX = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/avif": ".avif",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
}


class ImageStorage:
    """Owns where image files live on disk.

    Layout: ``output/images/<Product Name>_<SKU>/main.jpg`` plus
    ``gallery_01.jpg``, ``gallery_02.jpg``, ... for the remaining images.
    """

    _INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
    _MAX_NAME_LENGTH = 120

    def __init__(self, settings: OutputSettings) -> None:
        self._settings = settings

    def product_directory(self, product_name: str, sku: str, product_id: str) -> Path:
        """Return ``output/images/<Product Name>_<SKU>/`` (SKU or product id)."""
        identifier = sku or product_id or "product"
        folder = f"{product_name}_{identifier}"
        return self._settings.images_dir / self.sanitize(folder)

    def image_filename(self, index: int, url: str, content_type: str | None) -> str:
        """Return ``main.jpg`` for the first image and ``gallery_XX.jpg`` after."""
        extension = self._extension_for(url, content_type)
        if index <= 1:
            return f"main{extension}"
        return f"gallery_{index - 1:02d}{extension}"

    def save(self, path: Path, data: bytes) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    @classmethod
    def sanitize(cls, name: str) -> str:
        cleaned = cls._INVALID_CHARS.sub("_", name).strip(" .")
        cleaned = cleaned[: cls._MAX_NAME_LENGTH].rstrip(" .")
        return cleaned or "product"

    @staticmethod
    def _extension_for(url: str, content_type: str | None) -> str:
        suffix = Path(url.split("?", 1)[0]).suffix.lower()
        if suffix in _IMAGE_SUFFIXES:
            return suffix
        if content_type:
            extension = _CONTENT_TYPE_SUFFIX.get(content_type.split(";", 1)[0].strip().lower())
            if extension:
                return extension
        return ".jpg"
