"""Tests for text and price parsing helpers."""
from __future__ import annotations

from decimal import Decimal

from app.infrastructure.utils.parsing import clean_text, parse_price, to_ascii_digits


def test_to_ascii_digits_arabic_indic() -> None:
    assert to_ascii_digits("١٬٩٤٠") == "1940"


def test_to_ascii_digits_extended_arabic_indic() -> None:
    assert to_ascii_digits("۰۱۲۳۴۵۶۷۸۹") == "0123456789"


def test_to_ascii_digits_passthrough_ascii() -> None:
    assert to_ascii_digits("1940") == "1940"


def test_to_ascii_digits_empty() -> None:
    assert to_ascii_digits("") == ""


def test_parse_price_with_arabic_indic_digits() -> None:
    assert parse_price(to_ascii_digits("١٬٩٤٠")) == Decimal("1940")



def test_clean_text_collapses_whitespace() -> None:
    assert clean_text("  Hello   world\n there ") == "Hello world there"


def test_clean_text_empty() -> None:
    assert clean_text("") == ""
    assert clean_text(None or "") == ""


def test_parse_price_us_format() -> None:
    assert parse_price("$1,299.00") == Decimal("1299.00")


def test_parse_price_eu_format() -> None:
    assert parse_price("19,99 EUR") == Decimal("19.99")


def test_parse_price_with_thousands_and_cents() -> None:
    assert parse_price("Price: 45,999.50 SAR") == Decimal("45999.50")


def test_parse_price_missing() -> None:
    assert parse_price("") is None


def test_parse_price_garbage() -> None:
    assert parse_price("N/A") is None
