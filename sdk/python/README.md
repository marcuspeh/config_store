# config_store Python SDK

Async-first client for the `config_store` service.

## Install

From this repo (no PyPI release yet):

```bash
# pip
pip install "config-store-sdk @ git+https://github.com/marcuspeh/config_store.git@main#subdirectory=sdk/python"

# uv
uv add "config-store-sdk @ git+https://github.com/marcuspeh/config_store.git@main#subdirectory=sdk/python"
```

Pin to a tag or commit SHA for reproducibility:

```bash
uv add "config-store-sdk @ git+https://github.com/marcuspeh/config_store.git@v0.1.0#subdirectory=sdk/python"
```

## Quick start

```python
import asyncio
from config_store import ConfigClient, ClientWatcher

class MyServiceConfig:
    url: str
    token: str = ""

async def init_service(client: ConfigClient, cfg: MyServiceConfig) -> "MyService":
    return MyService(cfg.url, cfg.token)

async def main():
    async with ConfigClient("my-project", base_url="http://localhost:6002") as client:
        watcher = await ClientWatcher.new(
            MyServiceConfig,
            init_service,
            client=client,
            key="my-service",
            poll_interval=60.0,
        )
        try:
            svc = watcher.get()
            await svc.do_work()
        finally:
            await watcher.aclose()

asyncio.run(main())
```

## Value contract — read this

`ConfigClient.get(key)` returns the **raw string stored in MongoDB's `value` field, byte-for-byte.** No JSON parsing happens on the SDK side.

`ClientWatcher` is **tolerant** about what comes back:

- JSON that matches `config_type` → parsed into the typed object.
- JSON that's a dict but `config_type` is constructible → `config_type(**parsed)`.
- Non-JSON (plain text, empty string, anything that doesn't parse) → the raw string is passed through to `init_client` unchanged. This is what lets you store a literal `https://api.example.com` in Mongo and consume it as a `str` from the watcher.

So:

- For **plain-text** configs (URL, secret, key): store the literal value in Mongo, declare `config_type=str` in `ClientWatcher.new`, and use the raw string directly.
- For **structured** configs: store a JSON object in Mongo, declare a dataclass / pydantic model / TypedDict as `config_type`, and the watcher will populate it for you.
- For **ad-hoc** reads where you want the raw bytes: use `client.get(key)` and parse it yourself.

## Errors

- `ConfigNotFoundError` — key not present.
- `ConfigStoreError` — network failure, non-2xx response, malformed body.

`ClientWatcher` logs and continues on transient errors; it never crashes the poll loop.

## Run the tests

```bash
uv sync --extra test
uv run pytest
```
