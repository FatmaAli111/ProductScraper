"""Scraper implementations. Importing this package registers all scrapers."""
from app.infrastructure.scrapers.base import BaseScraper
from app.infrastructure.scrapers.registry import SCRAPERS, build_scraper, register
from app.infrastructure.scrapers.salla import SallaScraper
from app.infrastructure.scrapers.template import TemplateScraper

__all__ = ["SCRAPERS", "BaseScraper", "SallaScraper", "TemplateScraper", "build_scraper", "register"]
