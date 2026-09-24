import { apiClient } from "./client";
import type {
  ConfigListItem,
  ConfigResponse,
  ConfigWriteRequest,
  HealthResponse,
  ProjectSummary,
} from "./types";

// Thin typed wrappers around the backend endpoints. Each function maps
// 1:1 to a route in backend/app/api/routes.py and the §7 PRD surface.
//
// These functions are wired up in Task 1 but the underlying backend
// endpoints for projects/configs CRUD don't exist yet — Phase B adds
// them. Until then, callers should expect the axios request to fail
// with a connection error.

export async function listProjects(): Promise<ProjectSummary[]> {
  const res = await apiClient.get<ProjectSummary[]>("/projects");
  return res.data;
}

export async function listConfigs(project: string): Promise<ConfigListItem[]> {
  const res = await apiClient.get<ConfigListItem[]>(
    `/projects/${encodeURIComponent(project)}/configs`,
  );
  return res.data;
}

export async function getConfig(
  project: string,
  key: string,
): Promise<ConfigResponse> {
  const res = await apiClient.get<ConfigResponse>(
    `/config/${encodeURIComponent(project)}/${encodeURIComponent(key)}`,
  );
  return res.data;
}

export async function createConfig(
  project: string,
  key: string,
  body: ConfigWriteRequest,
): Promise<ConfigResponse> {
  const res = await apiClient.post<ConfigResponse>(
    `/config/${encodeURIComponent(project)}/${encodeURIComponent(key)}`,
    body,
  );
  return res.data;
}

export async function updateConfig(
  project: string,
  key: string,
  body: ConfigWriteRequest,
): Promise<ConfigResponse> {
  const res = await apiClient.put<ConfigResponse>(
    `/config/${encodeURIComponent(project)}/${encodeURIComponent(key)}`,
    body,
  );
  return res.data;
}

export async function refreshCache(): Promise<HealthResponse> {
  const res = await apiClient.post<HealthResponse>("/refresh");
  return res.data;
}

export async function getHealth(): Promise<HealthResponse> {
  const res = await apiClient.get<HealthResponse>("/health");
  return res.data;
}
