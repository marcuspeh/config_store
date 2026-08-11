import logging
import asyncio
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

# Load environment variables from .env file
load_dotenv(".env")

from app.api.routes import router  # noqa: E402
from app.core.config_manager import ConfigManager  # noqa: E402
from app.config.settings import settings  # noqa: E402

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config_manager = ConfigManager()


async def sync_cache_periodically(interval: int):
    """Background task to refresh the cache periodically."""
    while True:
        try:
            await config_manager.sync_from_remote()
        except Exception as e:
            logger.error(f"Periodic sync failed: {e}")
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize managers and database
    await config_manager.init()

    # Initial sync from remote
    await config_manager.sync_from_remote()

    # Start background task
    sync_task = asyncio.create_task(sync_cache_periodically(settings.sync_interval))
    yield
    # Cleanup
    sync_task.cancel()
    await config_manager.close()


app = FastAPI(title="Config Store", lifespan=lifespan)
app.include_router(router)


if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("CONFIG_STORE_PORT", "6002")))