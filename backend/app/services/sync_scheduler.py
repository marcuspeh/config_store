import asyncio

from app.logging_setup import client, log_id_scope
from app.services.config_service import ConfigService

log = client()


class SyncScheduler:
    """Background task that periodically calls ConfigService.sync_from_remote."""

    def __init__(self, service: ConfigService, interval: int) -> None:
        self._service = service
        self._interval = interval
        self._task: asyncio.Task | None = None

    async def _loop(self) -> None:
        # No request scope out here, so each iteration gets its own log id.
        while True:
            with log_id_scope() as log_id:
                log.info(
                    "periodic sync starting interval=%ds log_id=%s",
                    self._interval,
                    log_id,
                )
                try:
                    await self._service.sync_from_remote()
                except Exception as e:  # noqa: BLE001 — keep the loop alive
                    log.error(
                        "periodic sync failed error=%s",
                        e,
                    )
            await asyncio.sleep(self._interval)

    def start(self) -> None:
        """Spawn the background loop. Safe to call once per app lifetime."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """Cancel the background loop and wait for it to settle."""
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
