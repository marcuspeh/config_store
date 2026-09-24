import type { ReactElement } from "react";
import { Plus, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";

// Top bar shown on every page (per PRD §5).
//
// For Task 1 the cache stats + Refresh button are placeholders that
// show "—". Task 10 wires these up to `useHealth` with a 30s poll.

export function TopBar(): ReactElement {
  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3 shadow-sm">
      <div className="flex items-center gap-3">
        <Link
          to="/"
          className="text-lg font-semibold text-slate-900 hover:text-slate-700"
        >
          Config Store
        </Link>
        <span className="text-sm text-slate-400" aria-label="Cache stats">
          <span className="font-mono">—</span> projects ·{" "}
          <span className="font-mono">—</span> keys
        </span>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled
          aria-label="Refresh cache"
          title="Refresh cache (wired up in Task 10)"
          className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
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
