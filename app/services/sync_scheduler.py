import asyncio
import logging

from app.services.config_service import ConfigService

logger = logging.getLogger(__name__)


class SyncScheduler:
    """Background task that periodically calls ConfigService.sync_from_remote."""

    def __init__(self, service: ConfigService, interval: int) -> None:
        self._service = service
        self._interval = interval
        self._task: asyncio.Task | None = None

    async def _loop(self) -> None:
        while True:
            try:
                await self._service.sync_from_remote()
            except Exception as e:  # noqa: BLE001 — defensive long-running loop
                logger.error(f"Periodic sync failed: {e}")
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