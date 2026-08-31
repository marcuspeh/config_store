"""Tests for ClientWatcher using httpx.MockTransport."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Iterator, List

import httpx
import pytest

from config_store import ConfigClient, ClientWatcher


@dataclass
class FakeCfg:
    url: str
    token: str = ""


class FakeService:
    def __init__(self, cfg: FakeCfg) -> None:
        self.cfg = cfg
        self.closed = False
        self.aclose_called = False

    async def aclose(self) -> None:
        self.aclose_called = True
        self.closed = True

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def async_http() -> Iterator[httpx.AsyncClient]:
    # Default: three sequential values that exercise no-change, change, no-change.
    queue = [json.dumps({"url": "https://a", "token": "t1"}),
             json.dumps({"url": "https://a", "token": "t1"}),  # same → skip
             json.dumps({"url": "https://b", "token": "t2"}),  # changed → rebuild
             json.dumps({"url": "https://b", "token": "t2"})]  # same → skip

    def handler(request: httpx.Request) -> httpx.Response:
        if not queue:
            return httpx.Response(200, json={"value": queue[-1]})
        return httpx.Response(200, json={"value": queue.pop(0)})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    try:
        yield client
    finally:
        # nothing to close; MockTransport has no connection pool
        pass


@pytest.mark.asyncio
async def test_watcher_initializes_and_get_returns_current_value(async_http: httpx.AsyncClient) -> None:
    client = ConfigClient("proj", http_client=async_http)

    async def init(_http: ConfigClient, cfg: FakeCfg) -> FakeService:
        return FakeService(cfg)

    watcher = await ClientWatcher.new(
        FakeCfg,
        init,  # type: ignore[arg-type]
        client=client,
        key="svc",
    )

    assert isinstance(watcher.get(), FakeService)
    assert watcher.get().cfg.url == "https://a"

    await watcher.aclose()


@pytest.mark.asyncio
async def test_watcher_closes_previous_client_on_change(async_http: httpx.AsyncClient) -> None:
    client = ConfigClient("proj", cache_ttl=0.01, http_client=async_http)

    instances: List[FakeService] = []

    async def init(_http: ConfigClient, cfg: FakeCfg) -> FakeService:
        svc = FakeService(cfg)
        instances.append(svc)
        return svc

    watcher = await ClientWatcher.new(
        FakeCfg,
        init,  # type: ignore[arg-type]
        client=client,
        key="svc",
        poll_interval=0.05,
    )

    # The initial fetch in `new()` populates the cache; we want to exercise the
    # rebuild path, so clear the cache so each poll tick hits the transport.
    client.clear_cache()

    # Wait through enough ticks for the change to be observed. The fixture
    # returns the same value twice then a new value, so we expect exactly one
    # rebuild (initial + one rebuild when the value changes).
    for _ in range(60):
        if len(instances) >= 2 and instances[0].closed:
            break
        await asyncio.sleep(0.05)

    assert len(instances) == 2, f"expected exactly 2 instances (initial + 1 rebuild), got {len(instances)}"
    assert instances[0].closed, "first client should have been closed when replaced"
    assert instances[0].aclose_called, "async close path should be preferred"
    assert watcher.get().cfg.url == "https://b"
    assert watcher.get() is instances[1]

    await watcher.aclose()
    assert instances[-1].closed, "aclose() must close the final client"


@pytest.mark.asyncio
async def test_watcher_does_not_rebuild_when_unchanged(async_http: httpx.AsyncClient) -> None:
    client = ConfigClient("proj", http_client=async_http)

    instances: List[FakeService] = []

    async def init(_http: ConfigClient, cfg: FakeCfg) -> FakeService:
        svc = FakeService(cfg)
        instances.append(svc)
        return svc

    watcher = await ClientWatcher.new(
        FakeCfg,
        init,  # type: ignore[arg-type]
        client=client,
        key="svc",
        poll_interval=0.05,
    )

    # Don't clear the cache here: the queue returns the same value every fetch,
    # so the watcher must observe zero rebuilds even though it polls repeatedly.
    await asyncio.sleep(0.3)
    await watcher.aclose()

    # The fixture's first call (during `new()`) populates the cache; subsequent
    # ticks all hit the cache and see no change. Exactly 1 instance total.
    assert len(instances) == 1


@pytest.mark.asyncio
async def test_watcher_context_manager_lifecycle(async_http: httpx.AsyncClient) -> None:
    client = ConfigClient("proj", http_client=async_http)

    async def init(_http: ConfigClient, cfg: FakeCfg) -> FakeService:
        return FakeService(cfg)

    async with await ClientWatcher.new(
        FakeCfg,
        init,  # type: ignore[arg-type]
        client=client,
        key="svc",
        poll_interval=0.05,
    ) as watcher:
        assert isinstance(watcher.get(), FakeService)

    # After exit, get() should raise.
    with pytest.raises(RuntimeError):
        watcher.get()


@pytest.mark.asyncio
async def test_watcher_handles_remote_errors_without_crashing() -> None:
    state = {"n": 0, "fail_n": 2}

    def handler(request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        if state["n"] == state["fail_n"]:
            return httpx.Response(500, text="boom")
        return httpx.Response(200, json={"value": json.dumps({"url": "https://a", "token": "t1"})})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ConfigClient("proj", http_client=http)

    async def init(_http: ConfigClient, cfg: FakeCfg) -> FakeService:
        return FakeService(cfg)

    watcher = await ClientWatcher.new(
        FakeCfg,
        init,  # type: ignore[arg-type]
        client=client,
        key="svc",
        poll_interval=0.05,
    )

    # Let it tick through the error.
    await asyncio.sleep(0.2)

    # The watcher must still be functional and have the initial value.
    assert watcher.get().cfg.url == "https://a"

    await watcher.aclose()
