"""ClientWatcher: poll-driven rebuilder for typed config clients."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Callable, Generic, Optional, TypeVar

from .client import ConfigClient, ConfigNotFoundError, ConfigStoreError

logger = logging.getLogger(__name__)


ConfigT = TypeVar("ConfigT")
ClientT = TypeVar("ClientT")


InitClient = Callable[[Any, "ConfigT"], "asyncio.Future[ClientT] | ClientT"]


class _Closeable:
    """Protocol-style mixin used only for `isinstance` checks against close/aclose."""


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _close_if_possible(value: Any) -> None:
    if value is None:
        return
    aclose = getattr(value, "aclose", None)
    if callable(aclose):
        result = aclose()
        if inspect.isawaitable(result):
            await result
        return
    close = getattr(value, "close", None)
    if callable(close):
        result = close()
        if inspect.isawaitable(result):
            await result


def _coerce_config(raw: str, config_type: Any) -> Any:
    """Parse a raw Mongo `value` string into the user's config object.

    Behavior:
    - If `raw` parses as JSON and matches `config_type`, return the parsed value.
    - If `raw` parses as JSON but is a dict and `config_type` is constructible
      from kwargs, build it via `config_type(**parsed)`.
    - If `raw` does NOT parse as JSON (plain text, empty string, etc.) and
      `config_type` is `str`, return `raw` unchanged. This lets callers store
      literal strings in Mongo without double-JSON-encoding them.
    - Otherwise return the parsed JSON value as-is and let `init_client` raise
      a clear error if the shape is wrong.
    """
    if not raw:
        # Empty payload — pass through; init_client decides what to do.
        return raw

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Non-JSON content (plain text, empty, or otherwise unparseable).
        # Pass it through; `init_client` can raise a clear error if the type
        # doesn't match, but we don't force callers to double-encode strings.
        return raw

    if isinstance(parsed, config_type):
        return parsed
    if isinstance(parsed, dict):
        try:
            return config_type(**parsed)  # type: ignore[call-arg]
        except Exception:
            pass
    return parsed


@dataclass
class _State(Generic[ClientT]):
    value: Optional[ClientT] = None
    last_raw: Optional[str] = None


class ClientWatcher(Generic[ConfigT, ClientT]):
    """Polls `client.get(key)` and rebuilds a typed client on every change.

    Usage::

        async with await ClientWatcher.new(
            MyConfig,
            init_client,
            client=store,
            key="my-service",
        ) as watcher:
            svc = watcher.get()
            await svc.do_work()
    """

    def __init__(
        self,
        config_type: type[ConfigT],
        init_client: InitClient[ConfigT, ClientT],
        client: ConfigClient,
        key: str,
        poll_interval: float = 60.0,
        initial_value: Optional[ClientT] = None,
        initial_raw: Optional[str] = None,
    ) -> None:
        self._config_type = config_type
        self._init_client = init_client
        self._client = client
        self._key = key
        self._poll_interval = poll_interval
        self._state: _State[ClientT] = _State(value=initial_value, last_raw=initial_raw)
        self._lock = asyncio.Lock()
        self._task: Optional[asyncio.Task[None]] = None
        self._stopped = asyncio.Event()

    @classmethod
    async def new(
        cls,
        config_type: type[ConfigT],
        init_client: InitClient[ConfigT, ClientT],
        *,
        client: ConfigClient,
        key: str,
        poll_interval: float = 60.0,
    ) -> "ClientWatcher[ConfigT, ClientT]":
        """Build a watcher primed with the current config value.

        Mirrors the Go SDK: does the first fetch eagerly so callers can
        use `watcher.get()` immediately after construction.
        """
        raw = await client.get(key)
        parsed = _coerce_config(raw, config_type)

        initial = await _maybe_await(init_client(client, parsed))
        watcher = cls(
            config_type=config_type,
            init_client=init_client,
            client=client,
            key=key,
            poll_interval=poll_interval,
            initial_value=initial,
            initial_raw=raw,
        )
        watcher.start()
        return watcher

    async def __aenter__(self) -> "ClientWatcher[ConfigT, ClientT]":
        # `new()` already auto-starts the poll loop, so entering the context
        # manager is a no-op (you get the watcher back as-is). Exiting triggers
        # shutdown via `aclose()`.
        if self._task is None:
            self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    def start(self) -> None:
        if self._task is not None:
            raise RuntimeError("ClientWatcher already started")
        self._stopped.clear()
        self._task = asyncio.create_task(self._run(), name=f"config-watcher:{self._key}")

    async def aclose(self) -> None:
        if self._task is None:
            return
        self._stopped.set()
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

        await _close_if_possible(self._state.value)
        self._state.value = None

    def get(self) -> ClientT:
        if self._state.value is None:
            raise RuntimeError("ClientWatcher has no current value")
        return self._state.value

    async def _run(self) -> None:
        try:
            while not self._stopped.is_set():
                try:
                    await asyncio.wait_for(self._stopped.wait(), timeout=self._poll_interval)
                    return  # stop requested
                except asyncio.TimeoutError:
                    pass

                try:
                    await self._tick()
                except ConfigNotFoundError as e:
                    logger.warning("config key %s/%s not found: %s", self._client._project, self._key, e)
                except ConfigStoreError as e:
                    logger.warning("failed to watch %s/%s: %s", self._client._project, self._key, e)
                except Exception:  # noqa: BLE001
                    logger.exception("unexpected error in ClientWatcher for %s/%s", self._client._project, self._key)
        except asyncio.CancelledError:
            raise

    async def _tick(self) -> None:
        raw = await self._client.get(self._key)

        if raw == self._state.last_raw:
            return

        parsed = _coerce_config(raw, self._config_type)

        new_value = await _maybe_await(self._init_client(self._client, parsed))

        async with self._lock:
            if raw == self._state.last_raw:
                # Lost the race against another tick that already applied this value.
                await _close_if_possible(new_value)
                return
            prev = self._state.value
            self._state.value = new_value
            self._state.last_raw = raw

        await _close_if_possible(prev)
