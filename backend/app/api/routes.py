import logging

from fastapi import APIRouter, Depends, HTTPException

from app.core.models import ConfigResponse, HealthResponse
from app.services.config_service import ConfigService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_config_service() -> ConfigService:
    """FastAPI dependency that exposes the singleton ConfigService."""
    from app.main import config_service  # local import to avoid circulars

    return config_service


@router.get("/health", response_model=HealthResponse)
async def health(svc: ConfigService = Depends(get_config_service)):
    return HealthResponse(
        status="ok",
        stats=await svc.get_stats(),
    )


@router.get("/config/{project}/{key}", response_model=ConfigResponse)
async def get_config(
    project: str,
    key: str,
    svc: ConfigService = Depends(get_config_service),
):
    value = await svc.get_config(project, key)
    if value is None:
        raise HTTPException(
            status_code=404,
            detail=f"Config not found for project '{project}' and key '{key}'",
        )

    return ConfigResponse(project=project, key=key, value=value)


@router.post("/refresh", response_model=HealthResponse)
async def refresh_cache(svc: ConfigService = Depends(get_config_service)):
    """Manually trigger a cache refresh."""
    try:
        logger.info("Manual cache refresh triggered")
        await svc.sync_from_remote()
        return HealthResponse(
            status="refreshed",
            stats=await svc.get_stats(),
        )
    except Exception as e:
        logger.error(f"Manual cache refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))