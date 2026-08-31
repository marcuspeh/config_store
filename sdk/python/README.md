# config_store Python SDK

Async-first client for the `config_store` service.

## Install

```bash
pip install -e .[test]
```

## Quick start

```python
import asyncio
from config_store import ConfigClient, ClientWatcher

class MyServiceConfig:
    url: str

async def init_service(ctx, cfg: MyServiceConfig):
    # build whatever client/connection cfg describes
    return SomeClient(cfg.url)

async def main():
    async with ConfigClient("my-project", base_url="http://localhost:6002") as client:
        async with await ClientWatcher.new(
            MyServiceConfig,
            init_service,
            client=client,
            key="my-service",
            poll_interval=60.0,
        ) as watcher:
            svc = watcher.get()
            await svc.do_work()
```

The SDK mirrors the Go SDK: a TTL'd in-memory cache for raw values, plus a
`ClientWatcher` that polls every `poll_interval` seconds and rebuilds your
typed client whenever the underlying config changes. The previous client is
closed (if it implements `aclose()` / `close()`) before the new one is swapped in.
