import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import {
  getConfig,
  getHealth,
  listConfigs,
  listProjects,
} from "../api/configs";
import { queryKeys } from "./queryKeys";
import type {
  ConfigListItem,
  ConfigResponse,
  HealthResponse,
  ProjectSummary,
} from "../api/types";

// Thin React Query wrappers around the typed API functions. Pages
// import these instead of touching `useQuery` directly so caching,
// invalidation, and staleTime policies live in one place.

export function useProjects(): UseQueryResult<ProjectSummary[]> {
  return useQuery({
    queryKey: queryKeys.projects(),
    queryFn: listProjects,
  });
}

export function useProjectConfigs(
  project: string,
): UseQueryResult<ConfigListItem[]> {
  return useQuery({
    queryKey: queryKeys.configs(project),
    queryFn: () => listConfigs(project),
    enabled: project.length > 0,
  });
}

export function useConfig(
  project: string,
  key: string,
): UseQueryResult<ConfigResponse> {
  return useQuery({
    queryKey: queryKeys.config(project, key),
    queryFn: () => getConfig(project, key),
    enabled: project.length > 0 && key.length > 0,
  });
}

// 30s poll matches PRD §10 decision 4. `useHealth` is intentionally
// separate from `useProjects` so the polling cadence can diverge from
// the on-mount-only data queries.
export function useHealth(): UseQueryResult<HealthResponse> {
  return useQuery({
    queryKey: queryKeys.health(),
    queryFn: getHealth,
    refetchInterval: 30_000,
  });
}
