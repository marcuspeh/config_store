import type { ReactElement } from "react";

interface SkeletonRowProps {
  columns?: number;
}

// Generic skeleton row used in list-page loading states. Renders a
// flex row of `columns` animated grey bars so the table has stable
// dimensions while the real data is loading (PRD §6.1: "Loading:
// skeleton rows (5 placeholders)").
export function SkeletonRow({
  columns = 2,
}: SkeletonRowProps): ReactElement {
  return (
    <div
      aria-hidden="true"
      className="flex items-center gap-4 border-b border-slate-100 px-4 py-3"
    >
      {Array.from({ length: columns }).map((_, i) => (
        <div
          key={i}
          className="h-4 flex-1 animate-pulse rounded bg-slate-200"
        />
      ))}
    </div>
  );
}
