import { useMutation, useQueryClient, type UseMutationResult } from "@tanstack/react-query";
import { createConfig, refreshCache, updateConfig } from "../api/configs";
import { queryKeys } from "./queryKeys";
import type { ConfigResponse, ConfigWriteRequest } from "../api/types";

// Mutations that create / update a config. Each one invalidates the
// affected caches so subsequent reads see the new value without a
// manual refetch. The optimistic write is intentionally NOT applied
// here — Task 8 / Task 9 will add it for the specific flows that
// benefit (edit page, create page).

interface CreateConfigArgs {
  project: string;
  key: string;
  body: ConfigWriteRequest;
}

interface UpdateConfigArgs {
  project: string;
  key: string;
  body: ConfigWriteRequest;
}

export function useCreateConfig(): UseMutationResult<
  ConfigResponse,
  Error,
  CreateConfigArgs
> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ project, key, body }: CreateConfigArgs) =>
      createConfig(project, key, body),
    onSuccess: (_data, { project }) => {
      void qc.invalidateQueries({ queryKey: queryKeys.configs(project) });
      void qc.invalidateQueries({ queryKey: queryKeys.projects() });
    },
  });
}

export function useUpdateConfig(): UseMutationResult<
  ConfigResponse,
  Error,
  UpdateConfigArgs
> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ project, key, body }: UpdateConfigArgs) =>
      updateConfig(project, key, body),
    onSuccess: (data, { project, key }) => {
      // Replace the cached single-config entry with the server's
      // authoritative response so subsequent renders stay consistent.
      qc.setQueryData(queryKeys.config(project, key), data);
      // The list-row preview may also have changed (different value
      // preview), so drop the list cache too.
      void qc.invalidateQueries({ queryKey: queryKeys.configs(project) });
    },
  });
}

// `useRefreshCache` calls POST /refresh and then invalidates every
// query — the backend will have re-synced from MongoDB so all cached
// values may now be stale. The top-bar Refresh button uses this.
export function useRefreshCache(): UseMutationResult<unknown, Error, void> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: refreshCache,
    onSuccess: () => {
      void qc.invalidateQueries();
    },
  });
}
