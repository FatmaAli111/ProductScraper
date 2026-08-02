"""Shared scraping logic for every storefront."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from decimal import Decimal
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.application.ports.scraper import ScraperPort
from app.domain.entities.product import Product
from app.infrastructure.config.settings import ScraperSettings
from app.infrastructure.http.http_client import HttpClient
from app.infrastructure.utils.parsing import clean_text, parse_price
from app.infrastructure.utils.urls import normalize_product_url


class BaseScraper(ScraperPort, ABC):
    """Provides discovery, pagination and parsing helpers to all scrapers."""

    def __init__(
        self,
        http: HttpClient,
        settings: ScraperSettings,
        logger: logging.Logger,
    ) -> None:
        self._http = http
        self._settings = settings
        self._logger = logger
        self._selectors = settings.selectors
        self._image_attribute = settings.image_attribute

    # ------------------------------------------------------------------
    # Product URL discovery
    # ------------------------------------------------------------------
    def discover_product_urls(self, category_urls: Sequence[str]) -> list[str]:
        discovered: set[str] = set()
        for category_url in category_urls:
            for page_url in self._category_pages(category_url):
                soup = self._http.get_soup(page_url)
                for raw_url in self._extract_product_links(soup, page_url):
                    normalized = normalize_product_url(raw_url)
                    if normalized:
                        discovered.add(normalized)
        return sorted(discovered)

    def _category_pages(self, category_url: str) -> Iterator[str]:
        """Yield the category page and every paginated page after it."""
        yield category_url
        pagination = self._settings.pagination
        if not pagination.enabled or not pagination.next_selector:
            return
        current = category_url
        for _ in range(pagination.max_pages - 1):
            soup = self._http.get_soup(current)
            next_link = soup.select_one(pagination.next_selector)
            href = next_link.get("href") if next_link else None
            if not href:
                break
            next_url = normalize_product_url(urljoin(current, href))
            if not next_url or next_url == current:
                break
            yield next_url
            current = next_url

    def _extract_product_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        selector = self._selectors.get("product_link", "a[href]")
        anchors = soup.select(selector)
        return [urljoin(base_url, anchor.get("href")) for anchor in anchors if anchor.get("href")]

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------
    def _text(self, soup: BeautifulSoup, selector: str, *, default: str = "") -> str:
        node = soup.select_one(selector) if selector else None
        return clean_text(node.get_text(" ", strip=True)) if node else default

    def _list_texts(self, soup: BeautifulSoup, selector: str) -> list[str]:
        if not selector:
            return []
        values: list[str] = []
        for node in soup.select(selector):
            text = clean_text(node.get_text(" ", strip=True))
            if text:
                values.append(text)
        return values

    def _price(self, soup: BeautifulSoup, selector: str) -> Decimal | None:
        return parse_price(self._text(soup, selector))

    def _image_urls(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        selector = self._selectors.get("images", "")
        if not selector:
            return []
        urls: list[str] = []
        for node in soup.select(selector):
            src = node.get(self._image_attribute) or node.get("src")
            if src:
                urls.append(urljoin(base_url, str(src)))
        return urls

    def _available(self, soup: BeautifulSoup) -> bool:
        selector = self._selectors.get("availability", "")
        if not selector:
            return True
        if selector.startswith("!"):
            return soup.select_one(selector[1:]) is None
        node = soup.select_one(selector)
        if node is None:
            return True
        text = clean_text(node.get_text(" ", strip=True))
        return text.lower() not in {"out of stock", "unavailable", "sold out"}

    # ------------------------------------------------------------------
    # Per-site contract
    # ------------------------------------------------------------------
    @abstractmethod
    def scrape_product(self, url: str) -> Product:
        """Fetch a product page and return a fully populated product."""
