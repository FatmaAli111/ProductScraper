"""Command line interface for the scraper."""
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from app.infrastructure.config.settings import OutputSettings, Settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="product-scraper",
        description="Scrape e-commerce stores and export products for Salla.",
    )
    parser.add_argument("--config", default="config.yaml", help="Path to the YAML configuration file.")
    parser.add_argument("--scraper", default=None, help="Override the scraper selected in the config.")
    parser.add_argument("--output", default=None, help="Override the output directory.")
    parser.add_argument("--threads", type=int, default=None, help="Override the number of download threads.")
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Resume from the last interrupted run (overrides config).",
    )
    parser.add_argument("--no-progress", action="store_true", help="Disable progress bars.")
    return parser


def apply_overrides(settings: Settings, args: argparse.Namespace) -> Settings:
    """Merge validated CLI arguments into the loaded settings."""
    overrides: dict[str, object] = {}

    if args.output is not None:
        out_dir = Path(args.output)
        overrides["output"] = OutputSettings(
            directory=out_dir,
            images_dir=out_dir / "images",
            excel_file=out_dir / "products.xlsx",
            state_file=out_dir / "state.json",
            products_cache=out_dir / "products_cache.json",
            log_file=out_dir / "scraper.log",
        )

    if args.scraper is not None:
        overrides["scraper"] = replace(settings.scraper, name=args.scraper)

    if args.threads is not None:
        overrides["download"] = replace(settings.download, threads=args.threads)

    if args.resume is not None:
        overrides["resume"] = args.resume

    if args.no_progress:
        overrides["ui"] = replace(settings.ui, show_progress=False)

    return replace(settings, **overrides) if overrides else settings
