"""File-backed product repository (survives restarts)."""
from __future__ import annotations

import json
import threading
from collections.abc import Sequence
from pathlib import Path

from app.domain.entities.product import Product
from app.domain.repositories.product_repository import ProductRepository


class JsonProductRepository(ProductRepository):
    """Persists products to a JSON cache between scrape and export.

    This is what makes resume mode lossless: products scraped in a previous
    run are re-exported together with the new ones.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._products: list[Product] = []
        self.load()

    def load(self) -> None:
        if not self._path.exists():
            return
        data = json.loads(self._path.read_text(encoding="utf-8"))
        self._products = [Product.from_dict(item) for item in data if isinstance(item, dict)]

    def save(self, product: Product) -> None:
        with self._lock:
            self._products.append(product)
            self._flush()

    def get_all(self) -> Sequence[Product]:
        with self._lock:
            return list(self._products)

    def count(self) -> int:
        return len(self._products)

    def clear(self) -> None:
        with self._lock:
            self._products = []
            self._flush()

    def _flush(self) -> None:
        payload = [product.as_dict() for product in self._products]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_name(f"{self._path.name}.tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._path)
