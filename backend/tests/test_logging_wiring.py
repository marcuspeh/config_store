"""Tests for the logging-system SDK integration."""

from __future__ import annotations

import builtins
import logging
import re

import loggingsdk
import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app import logging_setup as logging_pkg
from app.config import settings as settings_pkg
from app.logging_setup import client as get_log_client
from app.logging_setup import setup_logging
from app.middleware.access_log import AccessLogMiddleware
from app.middleware.correlation import CorrelationIdMiddleware


@pytest.fixture(autouse=True)
def disable_logging_sdk(monkeypatch):
    monkeypatch.setenv("LOG_DISABLED", "1")


def test_setup_logging_installs_stderr_handler():
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    setup_logging()
    setup_logging()  # idempotent

    kinds = {type(h).__name__ for h in root.handlers}
    assert "StreamHandler" in kinds


def test_setup_logging_constructs_client_when_enabled(monkeypatch):
    monkeypatch.setenv("LOG_DISABLED", "0")
    monkeypatch.setenv("LOG_KAFKA_BROKERS", "127.0.0.1:1")
    monkeypatch.setenv("LOG_PROJECT", "config_store")

    settings_pkg.get_settings.cache_clear()

    logging_pkg._client_instance = None
    try:
        c = logging_pkg.setup_logging()
        assert c is not None
        assert c.project == "config_store"
    finally:
        logging_pkg.shutdown_logging()


@pytest.mark.asyncio
async def test_correlation_middleware_binds_log_id_per_request():
    seen_ids: list[str] = []

    async def echo(request: Request) -> PlainTextResponse:
        seen_ids.append(loggingsdk.current_log_id())
        return PlainTextResponse(loggingsdk.current_log_id())

    app = Starlette(
        middleware=[Middleware(CorrelationIdMiddleware)],
        routes=[Route("/", echo)],
    )
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    request_id = response.headers.get("X-Request-ID")
    assert request_id, "response should echo the id"
    assert seen_ids == [request_id]


@pytest.mark.asyncio
async def test_correlation_middleware_generates_sdk_style_id():
    async def echo(request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    app = Starlette(
        middleware=[Middleware(CorrelationIdMiddleware)],
        routes=[Route("/", echo)],
    )
    client = TestClient(app)
    response = client.get("/")

    request_id = response.headers.get("X-Request-ID", "")
    assert re.fullmatch(r"\d{8}-\d{4}-[0-9a-z]{6}", request_id), request_id


@pytest.mark.asyncio
async def test_correlation_middleware_honors_inbound_request_id():
    async def echo(request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    app = Starlette(
        middleware=[Middleware(CorrelationIdMiddleware)],
        routes=[Route("/", echo)],
    )
    client = TestClient(app)
    response = client.get("/", headers={"X-Request-ID": "caller-supplied-42"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "caller-supplied-42"


def test_setup_logging_noop_when_sdk_unavailable(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "loggingsdk" or name.startswith("loggingsdk."):
            raise ImportError("simulated sdk missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(logging_pkg, "loggingsdk", None)
    monkeypatch.setattr(logging_pkg, "Client", None)
    monkeypatch.setattr(logging_pkg, "LoggingHandler", None)
    monkeypatch.setattr(logging_pkg, "ParseLevel", None)

    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    result = setup_logging()

    assert result is None
    assert any(type(h).__name__ == "StreamHandler" for h in root.handlers)


def test_client_accessor_returns_null_when_disabled():
    log = get_log_client()
    log.info("hi")
    log.error("oops")
    assert hasattr(log, "project")


def test_access_log_middleware_skips_health(monkeypatch):
    class FakeClient:
        def __init__(self):
            self.calls: list[str] = []

        def info(self, fmt: str, *args):
            self.calls.append(fmt)

        def error(self, fmt: str, *args):
            self.calls.append(fmt)

    fake = FakeClient()
    monkeypatch.setattr("app.middleware.access_log.client", lambda: fake)

    async def ok(request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    app = Starlette(
        middleware=[Middleware(AccessLogMiddleware)],
        routes=[Route("/health", ok), Route("/ok", ok)],
    )
    test_client = TestClient(app)
    assert test_client.get("/health").status_code == 200
    assert fake.calls == []

    test_client.get("/ok")
    assert fake.calls


def test_access_log_middleware_invokes_client_info_and_error(monkeypatch):
    class FakeClient:
        def __init__(self):
            self.calls: list[tuple[str, str]] = []

        def info(self, fmt: str, *args):
            self.calls.append(("info", fmt))

        def error(self, fmt: str, *args):
            self.calls.append(("error", fmt))

    fake = FakeClient()
    monkeypatch.setattr("app.middleware.access_log.client", lambda: fake)

    async def ok(request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    async def boom(request: Request) -> PlainTextResponse:
        return PlainTextResponse("boom", status_code=500)

    app = Starlette(
        middleware=[Middleware(AccessLogMiddleware)],
        routes=[Route("/ok", ok), Route("/boom", boom)],
    )
    test_client = TestClient(app)
    test_client.get("/ok")
    test_client.get("/boom")

    levels = [c[0] for c in fake.calls]
    assert "info" in levels
    assert "error" in levels
    messages = " ".join(c[1] for c in fake.calls)
    assert "request completed" in messages
    assert "request failed" in messages