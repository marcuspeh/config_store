import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

# Load environment variables from .env file
load_dotenv(".env")

from app.api.routes import router as api_router  # noqa: E402
from app.config.settings import get_settings  # noqa: E402
from app.database.session import close_db, init_db  # noqa: E402
from app.logging_setup import setup_logging, shutdown_logging  # noqa: E402
from app.middleware.correlation import CorrelationIdMiddleware  # noqa: E402
from app.services.config_service import ConfigService  # noqa: E402
from app.services.sync_scheduler import SyncScheduler  # noqa: E402

# Install the logging-sdk handler as the first thing we do so every
# subsequent log call (init_db, sync, scheduler) is routed to Kafka.
setup_logging()
logger = logging.getLogger(__name__)

config_service = ConfigService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    scheduler: SyncScheduler | None = None
    try:
        await init_db()
        logger.info("Database initialized")

        # Initial sync from remote
        await config_service.sync_from_remote()

        # Start background sync loop
        scheduler = SyncScheduler(config_service, settings.sync_interval)
        scheduler.start()
        logger.info(
            f"Periodic sync scheduler started (interval={settings.sync_interval}s)"
        )
        yield
    finally:
        if scheduler is not None:
            await scheduler.stop()
        await close_db()
        # Drain the SDK so the in-flight queue is flushed before exit.
        shutdown_logging()


app = FastAPI(title="Config Store", lifespan=lifespan)
# Correlation id has to come before the routes so route handlers can
# `log_id_var.get()` and emit with the per-request id.
app.add_middleware(CorrelationIdMiddleware)
app.include_router(api_router)


if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("CONFIG_STORE_PORT", "6002")))