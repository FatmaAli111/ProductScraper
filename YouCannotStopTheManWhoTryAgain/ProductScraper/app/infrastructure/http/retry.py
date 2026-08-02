"""Retry helpers built on tenacity."""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, TypeVar

import requests
from tenacity import (
    Retrying,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

T = TypeVar("T")


class HttpStatusError(Exception):
    """Raised for HTTP status codes worth retrying (429, 5xx)."""

    def __init__(self, status_code: int, url: str) -> None:
        self.status_code = status_code
        self.url = url
        super().__init__(f"HTTP {status_code} for {url}")


class HttpClientError(Exception):
    """Raised for permanent HTTP failures (4xx). Not retried."""

    def __init__(self, status_code: int, url: str) -> None:
        self.status_code = status_code
        self.url = url
        super().__init__(f"HTTP {status_code} for {url}")


_RETRYABLE_EXCEPTIONS = (requests.RequestException, TimeoutError, HttpStatusError)


def retry_call(
    attempts: int,
    fn: Callable[..., T],
    *args: Any,
    logger: logging.Logger | None = None,
    backoff: float = 1.0,
    max_backoff: float = 30.0,
    **kwargs: Any,
) -> T:
    """Invoke ``fn`` retrying transient failures with exponential backoff."""
    before_sleep = None
    if logger is not None:
        before_sleep = before_sleep_log(logger, logging.WARNING)
    retrying = Retrying(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=backoff, max=max_backoff),
        retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
        before_sleep=before_sleep,
        reraise=True,
    )
    return retrying(fn, *args, **kwargs)
