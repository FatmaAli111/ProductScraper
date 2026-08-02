"""JSON-backed scrape state (resume support)."""
from __future__ import annotations

import json
import threading
from collections import defaultdict
from pathlib import Path

from app.application.ports.state_repository import StateRepositoryPort


class JsonStateRepository(StateRepositoryPort):
    """Persists progress in a JSON file so runs can be resumed."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._scraped_products: set[str] = set()
        self._images: dict[str, set[str]] = defaultdict(set)
        self._lock = threading.Lock()

    def load(self) -> None:
        if not self._path.exists():
            return
        data = json.loads(self._path.read_text(encoding="utf-8"))
        self._scraped_products = set(data.get("scraped_products", []))
        self._images = defaultdict(
            set,
            {key: set(value) for key, value in data.get("images", {}).items()},
        )

    def reset(self) -> None:
        with self._lock:
            self._scraped_products.clear()
            self._images.clear()

    def save(self) -> None:
        with self._lock:
            payload = {
                "scraped_products": sorted(self._scraped_products),
                "images": {
                    key: sorted(value) for key, value in self._images.items()
                },
            }
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_name(f"{self._path.name}.tmp")
            tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self._path)

    def is_product_scraped(self, url: str) -> bool:
        return url in self._scraped_products

    def mark_product_scraped(self, url: str) -> None:
        with self._lock:
            self._scraped_products.add(url)

    def is_image_downloaded(self, product_url: str, image_url: str) -> bool:
        return image_url in self._images.get(product_url, set())

    def mark_image_downloaded(self, product_url: str, image_url: str) -> None:
        with self._lock:
            self._images[product_url].add(image_url)
