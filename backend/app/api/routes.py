import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.models import (
    ConfigListItem,
    ConfigResponse,
    ConfigWriteRequest,
    HealthResponse,
    ProjectSummary,
)
from app.database.repositories.config import (
    ConfigAlreadyExists,
    ConfigNotFound,
)
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


@router.get("/projects", response_model=list[ProjectSummary])
async def list_projects(svc: ConfigService = Depends(get_config_service)):
    """List every distinct project with its config count.

    Rows are sorted by project name ASC for stable UI ordering.
    """
    rows = await svc.list_projects()
    return [ProjectSummary(project=p, config_count=c) for p, c in rows]


@router.get(
    "/projects/{project}/configs",
    response_model=list[ConfigListItem],
)
async def list_project_configs(
    project: str,
    svc: ConfigService = Depends(get_config_service),
):
    """List every config (key + value) in the given project.

    Returns an empty list — not 404 — when the project has no rows so
    the frontend can render a stable empty state.
    """
    rows = await svc.list_configs(project)
    return [ConfigListItem(config_key=k, value=v) for k, v in rows]


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


@router.post(
    "/config/{project}/{key}",
    response_model=ConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_config(
    project: str,
    key: str,
    body: ConfigWriteRequest,
    svc: ConfigService = Depends(get_config_service),
):
    """Create a new config. Returns 409 if (project, key) already exists.

    Writes through to MongoDB then MySQL — see
    `ConfigService.create_config`. Subsequent reads see the new row
    immediately because every read goes through the repo.
    """
    try:
        await svc.create_config(project, key, body.value)
    except ConfigAlreadyExists:
        # Surface as 409 so the frontend can render the "use Edit
        # instead" link from the PRD.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Config already exists for project '{project}' and key '{key}'",
        )
    except Exception as e:
        logger.error(f"Create config failed for {project}/{key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    return ConfigResponse(project=project, key=key, value=body.value)


@router.put("/config/{project}/{key}", response_model=ConfigResponse)
async def update_config(
    project: str,
    key: str,
    body: ConfigWriteRequest,
    svc: ConfigService = Depends(get_config_service),
):
    """Update an existing config. Returns 404 if (project, key) is missing.

    Does not upsert — the frontend's create flow is responsible for
    POST, this endpoint is strictly for the edit flow.
    """
    try:
        await svc.update_config(project, key, body.value)
    except ConfigNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config not found for project '{project}' and key '{key}'",
        )
    except Exception as e:
        logger.error(f"Update config failed for {project}/{key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    return ConfigResponse(project=project, key=key, value=body.value)