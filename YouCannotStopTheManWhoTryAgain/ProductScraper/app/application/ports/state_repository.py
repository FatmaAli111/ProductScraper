"""Scrape progress state contract (resume support)."""
from __future__ import annotations

from abc import ABC, abstractmethod


class StateRepositoryPort(ABC):
    """Tracks what has already been done so a run can be resumed."""

    @abstractmethod
    def load(self) -> None:
        """Load previously persisted state from disk."""

    @abstractmethod
    def reset(self) -> None:
        """Forget all previously recorded state."""

    @abstractmethod
    def save(self) -> None:
        """Persist the current state to disk."""

    @abstractmethod
    def is_product_scraped(self, url: str) -> bool:
        """Return True if the product page has already been scraped."""

    @abstractmethod
    def mark_product_scraped(self, url: str) -> None:
        """Record that a product page has been scraped."""

    @abstractmethod
    def is_image_downloaded(self, product_url: str, image_url: str) -> bool:
        """Return True if the image has already been downloaded."""

    @abstractmethod
    def mark_image_downloaded(self, product_url: str, image_url: str) -> None:
        """Record that an image has been downloaded."""
