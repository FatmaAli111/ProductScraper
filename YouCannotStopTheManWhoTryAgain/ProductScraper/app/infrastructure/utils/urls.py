"""URL normalization helpers."""
from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


def normalize_product_url(url: str) -> str:
    """Normalize a product URL for de-duplication.

    Lowercases scheme and host, keeps the query string (some stores need it),
    and drops fragments.
    """
    if not url:
        return ""
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return ""
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, "")
    )
