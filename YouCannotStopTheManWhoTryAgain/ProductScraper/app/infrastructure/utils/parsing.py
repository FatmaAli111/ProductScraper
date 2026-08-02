"""Text and price parsing helpers."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_SPACE_RE = re.compile(r"\s+")
_NUMBER_RE = re.compile(
    r"[+-]?\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?|[+-]?\d+(?:[.,]\d+)?"
)

# Arabic-Indic (٠-٩) and Extended Arabic-Indic (۰-۹) digits, plus the Arabic
# thousands separator (٬). Salla renders prices with these characters.
_DIGIT_TRANSLATION = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def to_ascii_digits(value: str) -> str:
    """Translate Arabic-Indic digits to ASCII and drop the Arabic separator."""
    if not value:
        return ""
    return value.translate(_DIGIT_TRANSLATION).replace("٬", "")


def clean_text(value: str) -> str:
    """Collapse all whitespace runs into a single space and strip edges."""
    if not value:
        return ""
    return _SPACE_RE.sub(" ", value).strip()


def parse_price(value: str) -> Decimal | None:
    """Extract the first currency number from a string.

    Handles both ``1,299.00`` (US) and ``19,99`` (EU) separators.
    """
    text = clean_text(value)
    if not text:
        return None
    match = _NUMBER_RE.search(text)
    if not match:
        return None
    raw = match.group(0).replace(" ", "")
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None
