"""Typed settings loaded from config.yaml."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(slots=True)
class PaginationSettings:
    enabled: bool = False
    next_selector: str = ""
    max_pages: int = 10


@dataclass(slots=True)
class BrowserSettings:
    channel: str = "chrome"
    headless: bool = True
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
    viewport_width: int = 1366
    viewport_height: int = 900
    locale: str = "ar-SA"
    navigation_timeout: int = 60000
    action_timeout: int = 15000
    wait_after_load_ms: int = 4000
    retries: int = 3
    retry_backoff: float = 1.0


@dataclass(slots=True)
class ScraperSettings:
    name: str = "template"
    category_urls: list[str] = field(default_factory=list)
    pagination: PaginationSettings = field(default_factory=PaginationSettings)
    selectors: dict[str, str] = field(default_factory=dict)
    image_attribute: str = "src"
    max_products: int = 0
    browser: BrowserSettings = field(default_factory=BrowserSettings)


@dataclass(slots=True)
class HttpSettings:
    user_agent: str = "ProductScraper/1.0"
    timeout: int = 30
    verify_ssl: bool = True
    headers: dict[str, str] = field(default_factory=dict)
    retries: int = 3
    retry_backoff: float = 1.0
    max_retry_delay: float = 30.0


@dataclass(slots=True)
class DownloadSettings:
    threads: int = 8
    timeout: int = 60
    retries: int = 3
    max_images_per_product: int = 30


@dataclass(slots=True)
class OutputSettings:
    directory: Path = Path("output")
    images_dir: Path = Path("output/images")
    excel_file: Path = Path("output/products.xlsx")
    state_file: Path = Path("output/state.json")
    products_cache: Path = Path("output/products_cache.json")
    log_file: Path = Path("output/scraper.log")


@dataclass(slots=True)
class LoggingSettings:
    level: str = "INFO"
    format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


@dataclass(slots=True)
class UiSettings:
    show_progress: bool = True


@dataclass(slots=True)
class Settings:
    scraper: ScraperSettings = field(default_factory=ScraperSettings)
    http: HttpSettings = field(default_factory=HttpSettings)
    download: DownloadSettings = field(default_factory=DownloadSettings)
    output: OutputSettings = field(default_factory=OutputSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    ui: UiSettings = field(default_factory=UiSettings)
    resume: bool = True


class SettingsLoader:
    """Builds a :class:`Settings` object from a YAML file."""

    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path
        self._root = config_path.parent

    def load(self) -> Settings:
        if not self._config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self._config_path}")
        raw = yaml.safe_load(self._config_path.read_text(encoding="utf-8")) or {}
        return Settings(
            scraper=self._scraper(raw.get("scraper", {})),
            http=self._http(raw.get("http", {})),
            download=self._download(raw.get("download", {})),
            output=self._output(raw.get("output", {})),
            logging=self._logging(raw.get("logging", {})),
            ui=self._ui(raw.get("ui", {})),
            resume=bool(raw.get("resume", True)),
        )

    def _scraper(self, data: object) -> ScraperSettings:
        section = _section(data)
        return ScraperSettings(
            name=str(section.get("name", "template")),
            category_urls=[str(url) for url in _list(section.get("category_urls"))],
            pagination=self._pagination(_section(section.get("pagination"))),
            selectors=_str_dict(section.get("selectors")),
            image_attribute=str(section.get("image_attribute", "src")),
            max_products=int(section.get("max_products", 0)),
            browser=self._browser(_section(section.get("browser"))),
        )

    @staticmethod
    def _browser(data: dict[str, object]) -> BrowserSettings:
        return BrowserSettings(
            channel=str(data.get("channel", "chrome")),
            headless=bool(data.get("headless", True)),
            user_agent=str(data.get("user_agent", BrowserSettings.user_agent)),
            viewport_width=int(data.get("viewport_width", 1366)),
            viewport_height=int(data.get("viewport_height", 900)),
            locale=str(data.get("locale", "ar-SA")),
            navigation_timeout=int(data.get("navigation_timeout", 60000)),
            action_timeout=int(data.get("action_timeout", 15000)),
            wait_after_load_ms=int(data.get("wait_after_load_ms", 4000)),
            retries=int(data.get("retries", 3)),
            retry_backoff=float(data.get("retry_backoff", 1.0)),
        )

    @staticmethod
    def _pagination(data: dict[str, object]) -> PaginationSettings:
        return PaginationSettings(
            enabled=bool(data.get("enabled", False)),
            next_selector=str(data.get("next_selector", "")),
            max_pages=int(data.get("max_pages", 10)),
        )

    @staticmethod
    def _http(data: object) -> HttpSettings:
        section = _section(data)
        return HttpSettings(
            user_agent=str(section.get("user_agent", "ProductScraper/1.0")),
            timeout=int(section.get("timeout", 30)),
            verify_ssl=bool(section.get("verify_ssl", True)),
            headers=_str_dict(section.get("headers")),
            retries=int(section.get("retries", 3)),
            retry_backoff=float(section.get("retry_backoff", 1.0)),
            max_retry_delay=float(section.get("max_retry_delay", 30.0)),
        )

    @staticmethod
    def _download(data: object) -> DownloadSettings:
        section = _section(data)
        return DownloadSettings(
            threads=int(section.get("threads", 8)),
            timeout=int(section.get("timeout", 60)),
            retries=int(section.get("retries", 3)),
            max_images_per_product=int(section.get("max_images_per_product", 30)),
        )

    def _output(self, data: object) -> OutputSettings:
        section = _section(data)
        return OutputSettings(
            directory=self._path(section, "directory", "output"),
            images_dir=self._path(section, "images_dir", "output/images"),
            excel_file=self._path(section, "excel_file", "output/products.xlsx"),
            state_file=self._path(section, "state_file", "output/state.json"),
            products_cache=self._path(section, "products_cache", "output/products_cache.json"),
            log_file=self._path(section, "log_file", "output/scraper.log"),
        )

    @staticmethod
    def _logging(data: object) -> LoggingSettings:
        section = _section(data)
        return LoggingSettings(
            level=str(section.get("level", "INFO")),
            format=str(section.get("format", "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")),
        )

    @staticmethod
    def _ui(data: object) -> UiSettings:
        section = _section(data)
        return UiSettings(show_progress=bool(section.get("show_progress", True)))

    def _path(self, section: dict[str, object], key: str, default: str) -> Path:
        path = Path(str(section.get(key, default)))
        return path if path.is_absolute() else (self._root / path)


def _section(data: object) -> dict[str, object]:
    return data if isinstance(data, dict) else {}


def _list(data: object) -> list[object]:
    return data if isinstance(data, list) else []


def _str_dict(data: object) -> dict[str, str]:
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items()}
