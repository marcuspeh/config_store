import type { ReactElement, ReactNode } from "react";
import clsx from "clsx";
import { useMediaQuery } from "../hooks/useMediaQuery";

// Shared breakpoint constant (PRD §11). We re-declare it here rather
// than import from MonacoEditor to keep the components decoupled.
const MOBILE_BREAKPOINT = "(max-width: 767px)";

interface ResponsiveTableProps<T> {
  rows: T[];
  getRowKey: (row: T) => string;
  // Wide-viewport rendering: a single `<tr>` element.
  renderRow: (row: T) => ReactElement;
  // Narrow-viewport rendering: one card per row. Receives `index` so
  // call sites can stagger if they want to.
  renderCard: (row: T, index: number) => ReactElement;
  className?: string;
  // Optional empty-state. Rendered inside the same container as the
  // rows, centred.
  emptyState?: ReactNode;
}

// Renders the table on viewports >= 768px and stacked cards below.
// Both renderings are kept in the DOM as siblings under a single
// container so SSR + responsive CSS don't have to coordinate; we hide
// the irrelevant one with `hidden md:block` / `md:hidden` instead of
// returning early (early-return on viewport would cause hydration
// mismatches in Vite + React Router apps).
export function ResponsiveTable<T>({
  rows,
  getRowKey,
  renderRow,
  renderCard,
  className,
  emptyState,
}: ResponsiveTableProps<T>): ReactElement {
  const isNarrow = useMediaQuery(MOBILE_BREAKPOINT);

  if (rows.length === 0 && emptyState) {
    return <div className={className}>{emptyState}</div>;
  }

  return (
    <div className={clsx(className)}>
      {/* Wide viewport: real <table>. */}
      <div className="hidden overflow-hidden rounded-lg border border-slate-200 bg-white md:block">
        <table className="w-full text-sm">
          <tbody>
            {rows.map((row) => (
              <tr key={getRowKey(row)}>{renderRow(row)}</tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Narrow viewport: stacked cards. `isNarrow` isn't used here for
          rendering — we let CSS handle the visibility — but reading it
          keeps the component subscribed to viewport changes for any
          future logic that needs it (e.g. lazy-loading more rows). */}
      <ul
        className={clsx(
          "space-y-2 md:hidden",
          isNarrow ? "" : "hidden",
        )}
        aria-label="List"
      >
        {rows.map((row, index) => (
          <li
            key={getRowKey(row)}
            className="rounded-lg border border-slate-200 bg-white p-3"
          >
            {renderCard(row, index)}
          </li>
        ))}
      </ul>
    </div>
  );
}
