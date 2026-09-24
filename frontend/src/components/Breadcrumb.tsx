import type { ReactElement, ReactNode } from "react";
import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";

export interface BreadcrumbItem {
  label: string;
  to?: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
  actions?: ReactNode;
}

// Breadcrumb header used on every detail-level page. Last item is
// treated as the current page (rendered as text, not a link) unless
// it has its own `to`. `actions` sits to the right (e.g. Edit button
// on §6.3 / §6.4 detail/edit pages).
export function Breadcrumb({
  items,
  actions,
}: BreadcrumbProps): ReactElement {
  return (
    <div className="mb-6 flex items-center justify-between gap-4">
      <nav aria-label="Breadcrumb">
        <ol className="flex flex-wrap items-center gap-1 text-sm">
          {items.map((item, idx) => {
            const isLast = idx === items.length - 1;
            return (
              <li key={`${idx}-${item.label}`} className="flex items-center gap-1">
                {idx > 0 ? (
                  <ChevronRight
                    className="h-3 w-3 text-slate-400"
                    aria-hidden="true"
                  />
                ) : null}
                {item.to && !isLast ? (
                  <Link
                    to={item.to}
                    className="text-slate-500 hover:text-slate-900 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                  >
                    {item.label}
                  </Link>
                ) : (
                  <span
                    aria-current={isLast ? "page" : undefined}
                    className={isLast ? "font-medium text-slate-900" : "text-slate-500"}
                  >
                    {item.label}
                  </span>
                )}
              </li>
            );
          })}
        </ol>
      </nav>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  );
}
