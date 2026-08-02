"""Tests for settings loading."""
from __future__ import annotations

from pathlib import Path

from app.infrastructure.config.settings import SettingsLoader


def test_settings_loads_from_yaml(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        "\n".join(
            [
                "resume: false",
                "scraper:",
                "  name: template",
                "  category_urls:",
                "    - https://x.test/cat",
                "  max_products: 25",
                "  browser:",
                "    channel: chrome",
                "    headless: false",
                "  selectors:",
                "    name: h1.title",
                "http:",
                "  retries: 5",
            ]
        ),
        encoding="utf-8",
    )

    settings = SettingsLoader(config).load()

    assert settings.resume is False
    assert settings.scraper.name == "template"
    assert settings.scraper.category_urls == ["https://x.test/cat"]
    assert settings.scraper.selectors["name"] == "h1.title"
    assert settings.scraper.max_products == 25
    assert settings.scraper.browser.channel == "chrome"
    assert settings.scraper.browser.headless is False
    assert settings.http.retries == 5
    assert settings.download.threads == 8


def test_missing_config_raises(tmp_path: Path) -> None:
    missing = tmp_path / "nope.yaml"
    try:
        SettingsLoader(missing).load()
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("Expected FileNotFoundError")


def test_output_paths_resolve_relative_to_config(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text("", encoding="utf-8")

    settings = SettingsLoader(config).load()

    assert settings.output.directory == tmp_path / "output"
    assert settings.output.excel_file == tmp_path / "output" / "products.xlsx"
