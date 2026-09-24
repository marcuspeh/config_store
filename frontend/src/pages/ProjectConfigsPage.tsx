import { useState } from "react";
import type { ReactElement } from "react";
import { Link, useParams } from "react-router-dom";
import { Pencil, Plus } from "lucide-react";
import { useProjectConfigs } from "../hooks/queries";
import type { ConfigListItem } from "../api/types";
import { extractErrorMessage } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { SkeletonRow } from "../components/SkeletonRow";
import { SortableHeader, type SortDir } from "../components/SortableHeader";
import { Breadcrumb } from "../components/Breadcrumb";
import { ConfigValuePreview } from "../components/ConfigValuePreview";
import { CopyButton } from "../components/CopyButton";

function nextDir(
  currentColumn: string | null,
  currentDir: SortDir | null,
  clicked: string,
): { column: string | null; dir: SortDir | null } {
  if (currentColumn !== clicked) return { column: clicked, dir: "asc" };
  if (currentDir === "asc") return { column: clicked, dir: "desc" };
  if (currentDir === "desc") return { column: null, dir: null };
  return { column: clicked, dir: "asc" };
}

function compareConfigs(
  a: ConfigListItem,
  b: ConfigListItem,
  column: string | null,
  dir: SortDir | null,
): number {
  if (!column || !dir) return 0;
  let cmp = a.config_key.localeCompare(b.config_key);
  return dir === "asc" ? cmp : -cmp;
}

// §6.2 Project Config Page. Lists every config in the given project
// with a truncated value preview. Row click navigates to detail.
// Per PRD §10 decision 1 there is no search/filter in v1.
export function ProjectConfigsPage(): ReactElement {
  const { project = "" } = useParams<{ project: string }>();
  const { data, isPending, isError, error, refetch } =
    useProjectConfigs(project);

  // Default sort: config_key ASC per PRD §6.2.
  const [sortColumn, setSortColumn] = useState<string | null>("config_key");
  const [sortDir, setSortDir] = useState<SortDir | null>("asc");

  const sorted = (data ?? [])
    .slice()
    .sort((a, b) => compareConfigs(a, b, sortColumn, sortDir));

  function handleSort(column: string) {
    const next = nextDir(sortColumn, sortDir, column);
    setSortColumn(next.column);
    setSortDir(next.dir);
  }

  return (
    <section aria-labelledby="project-configs-heading">
      <Breadcrumb
        items={[{ label: "Projects", to: "/" }, { label: project }]}
        actions={
          <Link
            to={`/projects/${encodeURIComponent(project)}/new`}
            className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            New Config
          </Link>
        }
      />

      <div className="mb-4 flex items-baseline justify-between">
        <h1
          id="project-configs-heading"
          className="text-2xl font-semibold text-slate-900"
        >
          <span className="font-mono">{project}</span>
        </h1>
        {!isPending && data ? (
          <span className="text-sm text-slate-500">
            {data.length} {data.length === 1 ? "config" : "configs"}
          </span>
        ) : null}
      </div>

      {isError ? (
        <ErrorBanner
          message={`Failed to load configs: ${extractErrorMessage(error)}`}
          onRetry={() => void refetch()}
        />
      ) : null}

      {isPending ? (
        <div
          role="status"
          aria-label="Loading configs"
          className="overflow-hidden rounded-lg border border-slate-200 bg-white"
        >
          {Array.from({ length: 5 }).map((_, i) => (
            <SkeletonRow key={i} columns={3} />
          ))}
        </div>
      ) : sorted.length === 0 ? (
        <EmptyState
          title="No configs in this project yet"
          description='Click "New Config" above to add one.'
        />
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <SortableHeader
                  label="Key"
                  columnKey="config_key"
                  activeColumn={sortColumn}
                  activeDir={sortDir}
                  onSort={handleSort}
                />
                <th
                  scope="col"
                  className="border-b border-slate-200 px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-slate-500"
                >
                  Value
                </th>
                <th
                  scope="col"
                  className="border-b border-slate-200 px-4 py-2 text-right text-xs font-semibold uppercase tracking-wider text-slate-500"
                >
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((row) => (
                <tr
                  key={row.config_key}
                  className="group border-t border-slate-100 align-top hover:bg-slate-50"
                >
                  <td className="px-4 py-3 font-mono text-slate-900">
                    <Link
                      to={`/projects/${encodeURIComponent(project)}/${encodeURIComponent(row.config_key)}`}
                      className="hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                    >
                      {row.config_key}
                    </Link>
                  </td>
                  <td className="max-w-2xl px-4 py-3">
                    <Link
                      to={`/projects/${encodeURIComponent(project)}/${encodeURIComponent(row.config_key)}`}
                      className="block focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                    >
                      <ConfigValuePreview value={row.value} />
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <CopyButton value={row.value} />
                      <Link
                        to={`/projects/${encodeURIComponent(project)}/${encodeURIComponent(row.config_key)}/edit`}
                        className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-2 py-0.5 text-xs font-medium text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                      >
                        <Pencil className="h-3 w-3" aria-hidden="true" />
                        Edit
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
