"""Scraper registry: makes adding a new website a one-file change."""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from app.application.ports.scraper import ScraperPort

if TYPE_CHECKING:
    from app.infrastructure.config.settings import ScraperSettings
    from app.infrastructure.http.http_client import HttpClient

SCRAPERS: dict[str, type[ScraperPort]] = {}


def register(name: str) -> Callable[[type[ScraperPort]], type[ScraperPort]]:
    """Class decorator that registers a scraper under a config name."""

    def decorator(cls: type[ScraperPort]) -> type[ScraperPort]:
        SCRAPERS[name] = cls
        cls.name = name
        return cls

    return decorator


def build_scraper(
    settings: ScraperSettings,
    http: HttpClient,
    logger: logging.Logger,
) -> ScraperPort:
    """Instantiate the scraper selected in the configuration."""
    import app.infrastructure.scrapers as _  # noqa: F401  (trigger registration)

    try:
        scraper_cls = SCRAPERS[settings.name]
    except KeyError:
        available = ", ".join(sorted(SCRAPERS))
        raise ValueError(f"Unknown scraper '{settings.name}'. Available scrapers: {available}") from None
    return scraper_cls(http, settings, logger)
