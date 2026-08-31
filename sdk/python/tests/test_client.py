"""Tests for ConfigClient using httpx.MockTransport (no network)."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from config_store import ConfigClient, ConfigNotFoundError, ConfigStoreError


@pytest.mark.asyncio
async def test_get_hits_remote_on_first_call_and_caches_after():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"value": '"hello"'})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = ConfigClient("proj", http_client=http)

        assert await client.get("k") == '"hello"'
        assert await client.get("k") == '"hello"'
        assert await client.get("k") == '"hello"'

    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_cache_respects_ttl():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"value": "v1"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = ConfigClient("proj", cache_ttl=0.05, http_client=http)
        assert await client.get("k") == "v1"
        assert await client.get("k") == "v1"
        await asyncio.sleep(0.1)
        assert await client.get("k") == "v1"

    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_404_raises_config_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "nope"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = ConfigClient("proj", http_client=http)
        with pytest.raises(ConfigNotFoundError) as exc:
            await client.get("missing")
    assert exc.value.project == "proj"
    assert exc.value.key == "missing"


@pytest.mark.asyncio
async def test_500_raises_config_store_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = ConfigClient("proj", http_client=http)
        with pytest.raises(ConfigStoreError):
            await client.get("k")


@pytest.mark.asyncio
async def test_unexpected_shape_raises_config_store_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["nope"])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = ConfigClient("proj", http_client=http)
        with pytest.raises(ConfigStoreError):
            await client.get("k")


@pytest.mark.asyncio
async def test_clear_cache_forces_refetch():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"value": "v"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = ConfigClient("proj", http_client=http)
        await client.get("k")
        await client.get("k")
        client.clear_cache()
        await client.get("k")

    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_url_uses_project_and_key():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"value": "v"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = ConfigClient("my-project", base_url="http://config-store:6002", http_client=http)
        await client.get("my-key")

    assert seen["url"] == "http://config-store:6002/config/my-project/my-key"
