"""Async + sync HTTP client for the config_store service."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx


class ConfigStoreError(Exception):
    """Base error for the SDK."""


class ConfigNotFoundError(ConfigStoreError):
    """Raised when the remote reports the config key does not exist."""

    def __init__(self, project: str, key: str) -> None:
        super().__init__(f"config key not found: {project}/{key}")
        self.project = project
        self.key = key


@dataclass
class _CacheEntry:
    value: str
    expires_at: float


class _TTLCache:
    """Tiny size-bounded TTL cache. Not thread-safe; the sync client guards it with a lock."""

    def __init__(self, max_size: int, ttl_seconds: float) -> None:
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._entries: dict[str, _CacheEntry] = {}
        self._order: list[str] = []  # insertion order for LRU eviction

    def get(self, key: str) -> Optional[str]:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            self._evict(key)
            return None
        return entry.value

    def put(self, key: str, value: str) -> None:
        if key in self._entries:
            self._entries[key].value = value
            self._entries[key].expires_at = time.monotonic() + self._ttl
            return
        if len(self._entries) >= self._max_size:
            oldest = self._order.pop(0)
            self._entries.pop(oldest, None)
        self._entries[key] = _CacheEntry(value=value, expires_at=time.monotonic() + self._ttl)
        self._order.append(key)

    def _evict(self, key: str) -> None:
        self._entries.pop(key, None)
        try:
            self._order.remove(key)
        except ValueError:
            pass

    def clear(self) -> None:
        self._entries.clear()
        self._order.clear()


_DEFAULT_BASE_URL = "http://localhost:6002"
_DEFAULT_CACHE_SIZE = 10
_DEFAULT_CACHE_TTL = 60.0
_DEFAULT_TIMEOUT = 10.0


class _BaseClient:
    def __init__(
        self,
        project: str,
        base_url: str = _DEFAULT_BASE_URL,
        cache_size: int = _DEFAULT_CACHE_SIZE,
        cache_ttl: float = _DEFAULT_CACHE_TTL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        if not project:
            raise ValueError("project must be non-empty")
        self._project = project
        self._base_url = base_url.rstrip("/")
        self._cache = _TTLCache(cache_size, cache_ttl)
        self._timeout = timeout

    def _url(self, key: str) -> str:
        return f"{self._base_url}/config/{self._project}/{key}"

    def _raise_for_status(self, response: httpx.Response, key: str) -> None:
        if response.status_code == 404:
            raise ConfigNotFoundError(self._project, key)
        if response.status_code >= 400:
            raise ConfigStoreError(
                f"config_store returned status {response.status_code} for "
                f"{self._project}/{key}: {response.text}"
            )

    def _decode_value(self, response: httpx.Response) -> str:
        data = response.json()
        if not isinstance(data, dict) or "value" not in data:
            raise ConfigStoreError(
                f"unexpected response shape from config_store: {data!r}"
            )
        return data["value"]


class ConfigClient(_BaseClient):
    """Async client for the config_store service."""

    def __init__(
        self,
        project: str,
        base_url: str = _DEFAULT_BASE_URL,
        cache_size: int = _DEFAULT_CACHE_SIZE,
        cache_ttl: float = _DEFAULT_CACHE_TTL,
        timeout: float = _DEFAULT_TIMEOUT,
        *,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        super().__init__(project, base_url, cache_size, cache_ttl, timeout)
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self) -> "ConfigClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def get(self, key: str) -> str:
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        response = await self._http.get(self._url(key))
        self._raise_for_status(response, key)
        value = self._decode_value(response)
        self._cache.put(key, value)
        return value

    def clear_cache(self) -> None:
        self._cache.clear()


class SyncConfigClient(_BaseClient):
    """Synchronous wrapper around the async client."""

    def __init__(
        self,
        project: str,
        base_url: str = _DEFAULT_BASE_URL,
        cache_size: int = _DEFAULT_CACHE_SIZE,
        cache_ttl: float = _DEFAULT_CACHE_TTL,
        timeout: float = _DEFAULT_TIMEOUT,
        *,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        super().__init__(project, base_url, cache_size, cache_ttl, timeout)
        self._owns_client = http_client is None
        self._http = http_client or httpx.Client(timeout=timeout)
        self._loop = asyncio.new_event_loop()

    def __enter__(self) -> "SyncConfigClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        try:
            if self._owns_client:
                self._http.close()
        finally:
            self._loop.close()

    def get(self, key: str) -> str:
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        response = self._http.get(self._url(key))
        self._raise_for_status(response, key)
        value = self._decode_value(response)
        self._cache.put(key, value)
        return value

    def clear_cache(self) -> None:
        self._cache.clear()
