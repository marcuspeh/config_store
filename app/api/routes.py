import logging

from fastapi import APIRouter, Depends, HTTPException

from app.core.config_manager import ConfigManager
from app.core.models import ConfigResponse, HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def get_config_manager() -> ConfigManager:
    """FastAPI dependency that exposes the singleton ConfigManager."""
    from app.main import config_manager  # local import to avoid circulars

    return config_manager


@router.get("/health", response_model=HealthResponse)
async def health(manager: ConfigManager = Depends(get_config_manager)):
    return HealthResponse(
        status="ok",
        stats=await manager.get_stats(),
    )


@router.get("/config/{project}/{key}", response_model=ConfigResponse)
async def get_config(project: str, key: str, manager: ConfigManager = Depends(get_config_manager)):
    value = await manager.get_config(project, key)
    if value is None:
        raise HTTPException(
            status_code=404,
            detail=f"Config not found for project '{project}' and key '{key}'",
        )

    return ConfigResponse(project=project, key=key, value=value)


@router.post("/refresh", response_model=HealthResponse)
async def refresh_cache(manager: ConfigManager = Depends(get_config_manager)):
    """Manually trigger a cache refresh."""
    try:
        logger.info("Manual cache refresh triggered")
        await manager.sync_from_remote()
        return HealthResponse(
            status="refreshed",
            stats=await manager.get_stats(),
        )
    except Exception as e:
        logger.error(f"Manual cache refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))