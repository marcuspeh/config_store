import logging
import asyncio
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

# Load environment variables from .env file
load_dotenv(".env")

from models import ConfigResponse, HealthResponse  # noqa: E402
from config_manager import ConfigManager  # noqa: E402
from settings import settings  # noqa: E402

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
    sync_task = asyncio.create_task(sync_cache_periodically(settings.SYNC_INTERVAL))
    yield
    # Cleanup
    sync_task.cancel()
    await config_manager.close()

app = FastAPI(title="Config Store", lifespan=lifespan)

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        stats=await config_manager.get_stats()
    )

@app.get("/config/{project}/{key}", response_model=ConfigResponse)
async def get_config(project: str, key: str):
    value = await config_manager.get_config(project, key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Config not found for project '{project}' and key '{key}'")

    return ConfigResponse(
        project=project,
        key=key,
        value=value
    )

@app.post("/refresh", response_model=HealthResponse)
async def refresh_cache():
    """Manually trigger a cache refresh."""
    try:
        logger.info("Manual cache refresh triggered")
        await config_manager.sync_from_remote()
        return HealthResponse(
            status="refreshed",
            stats=await config_manager.get_stats()
        )
    except Exception as e:
        logger.error(f"Manual cache refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("CONFIG_STORE_PORT", "6002")))