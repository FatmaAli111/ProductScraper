"""Logging setup."""
from __future__ import annotations

import logging
from pathlib import Path

from app.infrastructure.config.settings import LoggingSettings


def configure_logging(settings: LoggingSettings, log_file: Path | None) -> logging.Logger:
    """Configure console + file logging and return the application logger."""
    root = logging.getLogger()
    if root.handlers:
        return logging.getLogger("product_scraper")

    root.setLevel(settings.level.upper())
    formatter = logging.Formatter(settings.format)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    return logging.getLogger("product_scraper")
