import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from app.api.routes import router as api_router
from app.config.settings import get_settings
from app.database.session import close_db, init_db
from app.logging_setup import client, log_id_scope, setup_logging, shutdown_logging
from app.middleware.access_log import AccessLogMiddleware
from app.middleware.correlation import CorrelationIdMiddleware
from app.services.config_service import ConfigService
from app.services.sync_scheduler import SyncScheduler

setup_logging()
log = client()

config_service = ConfigService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    scheduler: SyncScheduler | None = None
    try:
        await init_db()
        log.info("Database initialized")

        with log_id_scope() as log_id:
            log.info("Startup sync starting log_id=%s", log_id)
            await config_service.sync_from_remote()

        scheduler = SyncScheduler(config_service, settings.sync_interval)
        scheduler.start()
        log.info(
            "Periodic sync scheduler started interval=%ds", settings.sync_interval,
        )
        yield
    finally:
        if scheduler is not None:
            await scheduler.stop()
        await close_db()
        shutdown_logging()


app = FastAPI(title="Config Store", lifespan=lifespan)
# Correlation is added last so it wraps access logging and the id is bound first.
app.add_middleware(AccessLogMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.include_router(api_router)


if __name__ == "__main__":
    load_dotenv(".env")
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("CONFIG_STORE_PORT", "6002")))
