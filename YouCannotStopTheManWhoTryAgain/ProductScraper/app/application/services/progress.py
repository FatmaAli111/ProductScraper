"""Progress bar adapter."""
from __future__ import annotations

from tqdm import tqdm


class ProgressReporter:
    """Thin adapter around tqdm so rendering can be toggled or swapped."""

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled

    def products(self, total: int, *, initial: int = 0) -> tqdm:
        """Progress bar for the product scraping loop."""
        return tqdm(
            total=total,
            initial=initial,
            desc="Scraping products",
            unit="product",
            disable=not self._enabled,
        )

    def images(self, total: int, *, description: str = "Downloading images") -> tqdm:
        """Progress bar for the image download loop."""
        return tqdm(
            total=total,
            desc=description,
            unit="image",
            disable=not self._enabled,
        )
