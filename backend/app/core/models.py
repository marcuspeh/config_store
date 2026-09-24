from pydantic import BaseModel

class ConfigResponse(BaseModel):
    project: str
    key: str
    value: str

class CacheStats(BaseModel):
    projects_loaded: int
    cache_keys_total: int

class HealthResponse(BaseModel):
    status: str
    stats: CacheStats

class ProjectSummary(BaseModel):
    """One row in the GET /projects response."""
    project: str
    config_count: int

class ConfigListItem(BaseModel):
    """One row in the GET /projects/{project}/configs response."""
    config_key: str
    value: str

class ConfigWriteRequest(BaseModel):
    """Request body for POST /config/{project}/{key} and PUT /config/{project}/{key}.

    `language` was intentionally removed — the PRD treats value as
    opaque text in v1 (no language column, no parsing).
    """
    value: str