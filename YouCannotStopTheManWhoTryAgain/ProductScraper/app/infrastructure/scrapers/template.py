"""Config-driven reference scraper.

Subclass :class:`BaseScraper` and override :meth:`scrape_product` to support
a real storefront. This class shows the pattern: read CSS selectors from
config.yaml and map them onto the Product entity.
"""
from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from app.domain.entities.product import Product
from app.infrastructure.config.settings import ScraperSettings
from app.infrastructure.http.http_client import HttpClient
from app.infrastructure.scrapers.base import BaseScraper
from app.infrastructure.scrapers.registry import register
from app.infrastructure.utils.parsing import clean_text


@register("template")
class TemplateScraper(BaseScraper):
    """Generic, selector-driven scraper that mirrors config.yaml."""

    def __init__(self, http: HttpClient, settings: ScraperSettings, logger: logging.Logger) -> None:
        super().__init__(http, settings, logger)

    def scrape_product(self, url: str) -> Product:
        soup = self._http.get_soup(url)
        return self._build_product(soup, url)

    def _build_product(self, soup: BeautifulSoup, url: str) -> Product:
        selectors = self._selectors
        return Product(
            name=self._text(soup, selectors.get("name", "")),
            sku=self._text(soup, selectors.get("sku", "")),
            url=url,
            description=clean_text(self._text(soup, selectors.get("description", ""))),
            price=self._price(soup, selectors.get("price", "")),
            sale_price=self._price(soup, selectors.get("sale_price", "")),
            category=self._text(soup, selectors.get("category", "")),
            brand=self._text(soup, selectors.get("brand", "")),
            tags=self._list_texts(soup, selectors.get("tags", "")),
            colors=self._list_texts(soup, selectors.get("colors", "")),
            sizes=self._list_texts(soup, selectors.get("sizes", "")),
            availability=self._available(soup),
            weight=self._text(soup, selectors.get("weight", "")),
            dimensions=self._text(soup, selectors.get("dimensions", "")),
            image_urls=self._image_urls(soup, url),
        )
