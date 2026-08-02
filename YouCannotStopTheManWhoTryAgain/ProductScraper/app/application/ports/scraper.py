"""Scraper contract implemented by every storefront adapter."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.domain.entities.product import Product


class ScraperPort(ABC):
    """Contract every website scraper must satisfy."""

    name: str

    @abstractmethod
    def discover_product_urls(self, category_urls: Sequence[str]) -> list[str]:
        """Return the full, de-duplicated list of product page URLs.

        This includes pagination crawling for every category URL passed in.
        """

    @abstractmethod
    def scrape_product(self, url: str) -> Product:
        """Fetch and parse a single product page into a :class:`Product`."""
