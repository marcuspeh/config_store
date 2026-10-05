from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

# Load environment variables from .env file
load_dotenv(".env")

from app.api.routes import router as api_router  # noqa: E402
from app.config.settings import get_settings  # noqa: E402
from app.database.session import close_db, init_db  # noqa: E402
from app.logging_setup import client, setup_logging, shutdown_logging  # noqa: E402
from app.middleware.access_log import AccessLogMiddleware  # noqa: E402
from app.middleware.correlation import CorrelationIdMiddleware  # noqa: E402
from app.services.config_service import ConfigService  # noqa: E402
from app.services.sync_scheduler import SyncScheduler  # noqa: E402

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
# Correlation id is added last so it wraps the access-log middleware and
# the generated id is already bound when the request/response logs fire.
app.add_middleware(AccessLogMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.include_router(api_router)


if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("CONFIG_STORE_PORT", "6002")))