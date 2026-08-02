"""Tests for URL normalization."""
from __future__ import annotations

from app.infrastructure.utils.urls import normalize_product_url


def test_lowercases_scheme_and_host() -> None:
    assert normalize_product_url("HTTP://Shop.COM/Product/1") == "http://shop.com/Product/1"


def test_keeps_query_string() -> None:
    assert normalize_product_url("https://shop.com/p/1?color=red") == "https://shop.com/p/1?color=red"


def test_drops_fragment() -> None:
    assert normalize_product_url("https://shop.com/p/1#reviews") == "https://shop.com/p/1"


def test_rejects_invalid_urls() -> None:
    assert normalize_product_url("") == ""
    assert normalize_product_url("/relative/path") == ""
