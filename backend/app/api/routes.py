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
from app.logging_setup import client
from app.services.config_service import ConfigService

log = client()

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
    """List every distinct project with its config count."""
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
    """List every config (key + value) in the given project."""
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
        log.info("get config not found project=%s key=%s", project, key)
        raise HTTPException(
            status_code=404,
            detail=f"Config not found for project '{project}' and key '{key}'",
        )
    return ConfigResponse(project=project, key=key, value=value)


@router.post("/refresh", response_model=HealthResponse)
async def refresh_cache(svc: ConfigService = Depends(get_config_service)):
    """Manually trigger a cache refresh."""
    log.info("refresh cache triggered via api")
    try:
        await svc.sync_from_remote()
        return HealthResponse(
            status="refreshed",
            stats=await svc.get_stats(),
        )
    except Exception as e:
        log.error("refresh cache failed error=%s", e)
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
    """Create a new config. Returns 409 if (project, key) already exists."""
    try:
        await svc.create_config(project, key, body.value)
    except ConfigAlreadyExists:
        log.info("create config conflict project=%s key=%s", project, key)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Config already exists for project '{project}' and key '{key}'",
        )
    except Exception as e:
        log.error("create config failed project=%s key=%s error=%s", project, key, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    return ConfigResponse(project=project, key=key, value=body.value)


@router.delete(
    "/config/{project}/{key}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_config(
    project: str,
    key: str,
    svc: ConfigService = Depends(get_config_service),
):
    """Delete a (project, key) config. 204 on success, 404 if missing."""
    try:
        await svc.delete_config(project, key)
    except ConfigNotFound:
        log.info("delete config not found project=%s key=%s", project, key)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config not found for project '{project}' and key '{key}'",
        )
    except Exception as e:
        log.error("delete config failed project=%s key=%s error=%s", project, key, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    return None


@router.put("/config/{project}/{key}", response_model=ConfigResponse)
async def update_config(
    project: str,
    key: str,
    body: ConfigWriteRequest,
    svc: ConfigService = Depends(get_config_service),
):
    """Update an existing config. Returns 404 if (project, key) is missing."""
    try:
        await svc.update_config(project, key, body.value)
    except ConfigNotFound:
        log.info("update config not found project=%s key=%s", project, key)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config not found for project '{project}' and key '{key}'",
        )
    except Exception as e:
        log.error("update config failed project=%s key=%s error=%s", project, key, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    return ConfigResponse(project=project, key=key, value=body.value)