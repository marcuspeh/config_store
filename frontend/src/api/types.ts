// Shared API types. Mirrors the backend Pydantic models.

export interface CacheStats {
  projects_loaded: number;
  cache_keys_total: number;
}

export interface HealthResponse {
  status: string;
  stats: CacheStats;
}

export interface ProjectSummary {
  project: string;
  config_count: number;
}

export interface ConfigListItem {
  config_key: string;
  value: string;
}

export interface ConfigResponse {
  project: string;
  key: string;
  value: string;
}

export interface ConfigWriteRequest {
  value: string;
}
