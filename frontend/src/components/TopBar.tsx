import type { ReactElement } from "react";
import { Plus, RefreshCw, AlertTriangle } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { useHealthStatus } from "../hooks/useHealthStatus";
import { useRefreshCache } from "../hooks/mutations";
import { extractErrorMessage } from "../api/client";

// Top bar shown on every page (PRD §5).
//
// Stats come from `useHealthStatus`, which:
//   - polls /health every 30s,
//   - keeps the last-known-good response on transient errors so the
//     numbers don't flicker to "—",
//   - exposes `isStale` so we can render a subtle warning pill.
//
// The Refresh button calls POST /refresh and invalidates all caches
// (see `useRefreshCache`).
export function TopBar(): ReactElement {
  const health = useHealthStatus();
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

  // Three visual modes:
  //   1. `isError` (no data ever)  → "—" placeholders + "Offline" pill.
  //   2. `isStale` (errored but have last-known-good) → real numbers + amber "Stale" pill.
  //   3. Healthy → real numbers, no pill.
  const statsText =
    health.isInitialLoading
      ? "Loading…"
      : `${projects ?? "—"} projects · ${keys ?? "—"} keys`;

  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3 shadow-sm">
      <div className="flex items-center gap-3">
        <Link
          to="/"
          className="text-lg font-semibold text-slate-900 hover:text-slate-700"
        >
          Config Store
        </Link>
        <span
          className={`flex items-center gap-1.5 text-sm ${
            health.isError ? "text-slate-400" : "text-slate-500"
          }`}
          aria-label="Cache stats"
          title={
            health.lastUpdatedAt
              ? `Last updated ${new Date(health.lastUpdatedAt).toLocaleTimeString()}`
              : "Never updated"
          }
        >
          <span>{statsText}</span>
          {health.isError ? (
            <span
              className="inline-flex items-center gap-1 rounded bg-slate-200 px-1.5 py-0.5 text-xs font-medium text-slate-700"
              title="Health endpoint unreachable"
            >
              <AlertTriangle className="h-3 w-3" aria-hidden="true" />
              Offline
            </span>
          ) : health.isStale ? (
            <span
              className="inline-flex items-center gap-1 rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-800"
              title="Using last-known-good stats — latest /health fetch failed"
            >
              <AlertTriangle className="h-3 w-3" aria-hidden="true" />
              Stale
            </span>
          ) : null}
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
