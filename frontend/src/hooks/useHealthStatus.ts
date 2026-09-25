import { useEffect, useState } from "react";
import { useHealth } from "./queries";
import type { HealthResponse } from "../api/types";

// Threshold for "stale" — PRD §7.3: a subtle staleness indicator
// should kick in when the last successful fetch errored AND we still
// have a last-known-good value to fall back on. We don't gate on age
// because the 30s poll cadence + 60s threshold means there's always
// a ~30s window where the indicator would be visible even though the
// backend is healthy — which would be noise.
const STALE_AFTER_MS = 60_000;

export interface HealthStatus {
  // Last known good response, or `null` if we never got one.
  data: HealthResponse | null;
  // True while the query is fetching for the first time and we have
  // no data to show yet.
  isInitialLoading: boolean;
  // True when the query errored but we still have a last-known-good
  // `data` to fall back on. The top-bar should show the stale pill in
  // this state.
  isStale: boolean;
  // True when the query errored AND we have nothing to fall back on
  // (no successful fetch in this session).
  isError: boolean;
  // Timestamp of the last successful fetch (ms epoch), or `null`.
  lastUpdatedAt: number | null;
  // Wall-clock `Date.now()` (ms epoch), re-ticked every 15s so callers
  // re-render when they compute "minutes since last update" labels.
  now: number;
  // True when the last successful fetch is older than the staleness
  // threshold. Currently unused by the top-bar (which gates on `isStale`
  // instead) but exposed for future polish.
  isAgeStale: boolean;
}

// Derives a stable "stale / erroring / initial loading" view from the
// `useHealth` query. The PRD's last-known-good fallback requirement
// is satisfied here: `data` always reflects the most recent successful
// response, even when the latest fetch errored, because React Query
// only clears `data` when `gcTime` expires (left at the default 5 min).
export function useHealthStatus(): HealthStatus {
  const health = useHealth();
  const [now, setNow] = useState(() => Date.now());

  // Re-evaluate staleness every 15s without remounting. Without this
  // hook the "stale" pill would only flip on the next poll cycle
  // (every 30s) which is jittery.
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 15_000);
    return () => window.clearInterval(id);
  }, []);

  const lastUpdatedAt = health.dataUpdatedAt > 0 ? health.dataUpdatedAt : null;
  const age = lastUpdatedAt ? now - lastUpdatedAt : null;
  const isAgeStale = age !== null && age > STALE_AFTER_MS;

  // We're "stale" when the query is currently in an error state AND
  // we still have a last-known-good `data` to show.
  const isStale = health.isError && health.data !== undefined;

  return {
    data: health.data ?? null,
    isInitialLoading: health.isPending && !health.data,
    isStale,
    isError: health.isError && !health.data,
    lastUpdatedAt,
    now,
    isAgeStale,
  };
}
