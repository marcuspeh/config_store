import type { ReactElement, ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

// Centered empty-state block. Used on every list page (PRD §6.1, §6.2,
// §6.5) when the underlying query returns [].
export function EmptyState({
  title,
  description,
  action,
}: EmptyStateProps): ReactElement {
  return (
    <div
      role="status"
      className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-slate-300 bg-white px-6 py-16 text-center"
    >
      <h2 className="text-base font-medium text-slate-900">{title}</h2>
      {description ? (
        <p className="max-w-sm text-sm text-slate-500">{description}</p>
      ) : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
