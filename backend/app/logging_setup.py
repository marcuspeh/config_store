"""Central logging setup for the logging-system SDK.

Call sites use :func:`client` instead of stdlib ``logging.getLogger`` so
events flow through the Kafka pipeline. Stdlib logging still gets a stderr
handler, and ``LoggingHandler`` is attached to the root logger so
third-party libraries are forwarded too.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

from app.config.settings import get_settings

try:
    import loggingsdk
    from loggingsdk import Client, LoggingHandler, ParseLevel
except Exception:  # pragma: no cover - SDK unavailable
    loggingsdk = None  # type: ignore[assignment]
    Client = None  # type: ignore[assignment]
    LoggingHandler = None  # type: ignore[assignment]
    ParseLevel = None  # type: ignore[assignment]

# Shared SDK client. None when the SDK is unavailable or disabled.
_client_instance: Optional["loggingsdk.Client"] = None


class _NullClient:
    """No-op stand-in so call sites never need to guard against None."""

    @property
    def project(self) -> str:  # pragma: no cover - read for tests
        return ""

    def debug(self, *_args, **_kwargs) -> None: pass
    def info(self, *_args, **_kwargs) -> None: pass
    def warn(self, *_args, **_kwargs) -> None: pass
    def error(self, *_args, **_kwargs) -> None: pass
    def fatal(self, *_args, **_kwargs) -> None: pass
    def close(self, *_args, **_kwargs) -> None: pass


def setup_logging() -> Optional["loggingsdk.Client"]:
    """Configure stdlib logging and build the SDK client. Idempotent."""
    global _client_instance

    settings = get_settings()

    # Stderr first so there is always some output, even without the SDK.
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        ),
    )

    root = logging.getLogger()
    root.setLevel(_parse_level(settings.log_level))
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(stderr_handler)

    if settings.log_disabled or loggingsdk is None:
        return None

    if _client_instance is not None:
        return _client_instance

    _client_instance = Client(
        bootstrap=settings.log_kafka_brokers,
        project=settings.log_project,
        topic=settings.log_topic,
        async_capacity=settings.log_async_capacity,
        flush_interval=settings.log_flush_interval,
        min_level=ParseLevel(settings.log_level.upper())[0],
    )
    root.addHandler(LoggingHandler(_client_instance))
    return _client_instance


def client():
    """Return the shared SDK client, building it on first call."""
    if _client_instance is None:
        setup_logging()
    return _client_instance if _client_instance is not None else _NullClient()


def shutdown_logging() -> None:
    """Flush and close the SDK. Safe to call when it is disabled."""
    global _client_instance
    if _client_instance is not None:
        try:
            _client_instance.close()
        finally:
            _client_instance = None


def _parse_level(name: str) -> int:
    return {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARN": logging.WARNING,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "FATAL": logging.CRITICAL,
        "CRITICAL": logging.CRITICAL,
    }.get(name.upper(), logging.INFO)
