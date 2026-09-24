import type { ReactElement } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import clsx from "clsx";

export type SortDir = "asc" | "desc";

interface SortableHeaderProps {
  label: string;
  columnKey: string;
  activeColumn: string | null;
  activeDir: SortDir | null;
  onSort: (columnKey: string) => void;
}

// Table header cell that toggles between asc/desc/no-sort states when
// clicked. Visual cue shows the active column + direction (PRD §6.1
// sort requirement).
export function SortableHeader({
  label,
  columnKey,
  activeColumn,
  activeDir,
  onSort,
}: SortableHeaderProps): ReactElement {
  const isActive = activeColumn === columnKey;
  const dir = isActive ? activeDir : null;

  return (
    <th
      scope="col"
      className="border-b border-slate-200 px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-slate-500"
    >
      <button
        type="button"
        onClick={() => onSort(columnKey)}
        className={clsx(
          "inline-flex items-center gap-1 rounded hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400",
          isActive && "text-slate-900",
        )}
        aria-sort={
          dir === "asc" ? "ascending" : dir === "desc" ? "descending" : "none"
        }
      >
        <span>{label}</span>
        {dir === "asc" ? (
          <ChevronUp className="h-3 w-3" aria-hidden="true" />
        ) : dir === "desc" ? (
          <ChevronDown className="h-3 w-3" aria-hidden="true" />
        ) : null}
      </button>
    </th>
  );
}
