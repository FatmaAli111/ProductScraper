"""HTTP client with retries and BeautifulSoup helpers."""
from __future__ import annotations

import logging
from typing import Any

import requests
from bs4 import BeautifulSoup
from requests import Response

from app.infrastructure.config.settings import HttpSettings
from app.infrastructure.http.retry import HttpClientError, HttpStatusError, retry_call


class HttpClient:
    """Session wrapper that retries transient failures transparently."""

    def __init__(self, settings: HttpSettings, logger: logging.Logger) -> None:
        self._settings = settings
        self._logger = logger
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": settings.user_agent})
        self._session.headers.update(settings.headers)
        self._session.verify = settings.verify_ssl

    def get(self, url: str, *, timeout: int | None = None, **kwargs: Any) -> Response:
        """Perform a GET request with automatic retries."""
        return retry_call(
            self._settings.retries,
            self._request,
            url,
            logger=self._logger,
            backoff=self._settings.retry_backoff,
            max_backoff=self._settings.max_retry_delay,
            timeout=timeout or self._settings.timeout,
            **kwargs,
        )

    def _request(self, url: str, *, timeout: int, **kwargs: Any) -> Response:
        response = self._session.get(url, timeout=timeout, **kwargs)
        if response.status_code == 429 or response.status_code >= 500:
            raise HttpStatusError(response.status_code, url)
        if response.status_code >= 400:
            raise HttpClientError(response.status_code, url)
        return response

    def get_soup(self, url: str, *, timeout: int | None = None) -> BeautifulSoup:
        """GET a page and parse it with lxml."""
        response = self.get(url, timeout=timeout)
        return BeautifulSoup(response.text, "lxml")

    def get_bytes(self, url: str, *, timeout: int | None = None) -> tuple[bytes, str | None]:
        """GET raw bytes (used for image downloads)."""
        response = self.get(url, timeout=timeout)
        return response.content, response.headers.get("Content-Type")

    def close(self) -> None:
        self._session.close()
