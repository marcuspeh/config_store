import type { ReactElement } from "react";
import { Plus, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { useHealth } from "../hooks/queries";
import { useRefreshCache } from "../hooks/mutations";
import { extractErrorMessage } from "../api/client";

// Top bar shown on every page (per PRD §5).
//
// - Cache stats come from `useHealth`, which polls /health every 30s.
// - The Refresh button calls POST /refresh and invalidates all caches.
//   On Task 5 the only invalidated cache is the projects list, but
//   later tasks (configs, detail) will pick this up automatically.
export function TopBar(): ReactElement {
  const health = useHealth();
  const refresh = useRefreshCache();

  const projects = health.data?.stats.projects_loaded ?? null;
  const keys = health.data?.stats.cache_keys_total ?? null;

  function handleRefresh() {
    refresh.mutate(undefined, {
      onSuccess: () => toast.success("Cache refreshed"),
      onError: (err) =>
        toast.error(`Refresh failed: ${extractErrorMessage(err)}`),
    });
  }

  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3 shadow-sm">
      <div className="flex items-center gap-3">
        <Link
          to="/"
          className="text-lg font-semibold text-slate-900 hover:text-slate-700"
        >
          Config Store
        </Link>
        <span className="text-sm text-slate-500" aria-label="Cache stats">
          <span className="font-mono">
            {projects === null ? "—" : projects}
          </span>{" "}
          projects ·{" "}
          <span className="font-mono">{keys === null ? "—" : keys}</span> keys
        </span>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleRefresh}
          disabled={refresh.isPending}
          aria-label="Refresh cache"
          className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw
            className={`h-4 w-4 ${refresh.isPending ? "animate-spin" : ""}`}
            aria-hidden="true"
          />
          Refresh
        </button>
        <Link
          to="/projects/new"
          className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          New Config
        </Link>
      </div>
    </header>
  );
}
