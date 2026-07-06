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
