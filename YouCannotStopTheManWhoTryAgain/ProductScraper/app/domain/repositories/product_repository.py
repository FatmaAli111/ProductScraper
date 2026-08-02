"""Repository contracts for persisting scraped products."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.domain.entities.product import Product


class ProductRepository(ABC):
    """Port for storing products between scrape and export steps."""

    @abstractmethod
    def save(self, product: Product) -> None:
        """Persist a single product."""

    @abstractmethod
    def get_all(self) -> Sequence[Product]:
        """Return every stored product."""

    @abstractmethod
    def count(self) -> int:
        """Return the number of stored products."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all stored products."""
