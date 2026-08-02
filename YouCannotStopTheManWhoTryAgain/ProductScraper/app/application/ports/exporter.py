"""Exporter contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path

from app.domain.entities.product import Product


class ExporterPort(ABC):
    """Serializes a collection of products into an import file."""

    @abstractmethod
    def export(self, products: Sequence[Product]) -> Path:
        """Write the products to a file and return the file path."""
