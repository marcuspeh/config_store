"""Initialise the logging-sdk (logging_system SDK) for this service.

Wires the stdlib ``logging`` root logger through
:class:`loggingsdk.LoggingHandler` so any ``logger.info(...)`` call
already in the codebase routes to the centralised logging pipeline
without modification.

Two safety nets:

* If the SDK can't be imported (e.g. running tests without the sibling
  repo on the Python path), we fall back to plain stderr logging.
* If Kafka is unreachable when the producer is constructed, we still
  keep the handler installed — ``ConfluentProducer.produce`` is
  non-blocking and delivery failures are reported through the SDK's
  ``stats`` counter and stderr, never as exceptions in the call site.
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


_client: Optional["loggingsdk.Client"] = None
"""The shared loggersdk.Client. ``None`` when the SDK is unavailable or
``log_disabled`` is set."""


def setup_logging() -> Optional["loggingsdk.Client"]:
    """Configure stdlib ``logging`` to route through the SDK.

    Returns the constructed :class:`loggingsdk.Client` (or ``None`` if
    the SDK is disabled). Idempotent — calling it twice returns the
    existing client.
    """
    global _client

    settings = get_settings()

    # Configure stderr first so we always have *some* output, even if
    # the SDK can't be imported or Kafka isn't reachable yet.
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        ),
    )

    root = logging.getLogger()
    root.setLevel(_parse_level(settings.log_level))
    # Drop any handlers added by `logging.basicConfig` (or by previous
    # `setup_logging` calls in the same process — tests).
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(stderr_handler)

    if settings.log_disabled or loggingsdk is None:
        return None

    if _client is not None:
        return _client

    _client = Client(
        bootstrap=settings.log_kafka_brokers,
        project=settings.log_project,
        topic=settings.log_topic,
        async_capacity=settings.log_async_capacity,
        flush_interval=settings.log_flush_interval,
        min_level=ParseLevel(settings.log_level.upper())[0],
    )
    root.addHandler(LoggingHandler(_client))
    return _client


def get_client() -> Optional["loggingsdk.Client"]:
    """Return the shared SDK client (constructs one on first call)."""
    if _client is None:
        setup_logging()
    return _client


def shutdown_logging() -> None:
    """Flush + close the SDK. Safe to call when the SDK is disabled."""
    global _client
    if _client is not None:
        try:
            _client.close()
        finally:
            _client = None


def _parse_level(name: str) -> int:
    """Map a level name (case-insensitive) to a stdlib level constant."""
    return {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARN": logging.WARNING,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "FATAL": logging.CRITICAL,
        "CRITICAL": logging.CRITICAL,
    }.get(name.upper(), logging.INFO)