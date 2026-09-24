import { useMemo, useState } from "react";
import type { ReactElement } from "react";
import { Link } from "react-router-dom";
import { useProjects } from "../hooks/queries";
import type { ProjectSummary } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { SkeletonRow } from "../components/SkeletonRow";
import { SortableHeader, type SortDir } from "../components/SortableHeader";
import { extractErrorMessage } from "../api/client";

// Sort cycle for a column: none -> asc -> desc -> none. Matches the
// behaviour of most admin tables; PRD §6.1 leaves the exact cycle
// unspecified.
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

function compareProjects(
  a: ProjectSummary,
  b: ProjectSummary,
  column: string | null,
  dir: SortDir | null,
): number {
  if (!column || !dir) return 0;
  let cmp = 0;
  if (column === "project") {
    cmp = a.project.localeCompare(b.project);
  } else if (column === "config_count") {
    cmp = a.config_count - b.config_count;
  }
  return dir === "asc" ? cmp : -cmp;
}

// §6.1 Project Selection Page. Lists every distinct project with its
// config count, sortable by name (default ASC) and config count. Row
// click navigates to /projects/[project]. The top-bar "+ New Config"
// already routes to /projects/new.
export function ProjectsPage(): ReactElement {
  const { data, isPending, isError, error, refetch } = useProjects();

  const [sortColumn, setSortColumn] = useState<string | null>("project");
  const [sortDir, setSortDir] = useState<SortDir | null>("asc");

  const sorted = useMemo(() => {
    if (!data) return [];
    return [...data].sort((a, b) =>
      compareProjects(a, b, sortColumn, sortDir),
    );
  }, [data, sortColumn, sortDir]);

  function handleSort(column: string) {
    const next = nextDir(sortColumn, sortDir, column);
    setSortColumn(next.column);
    setSortDir(next.dir);
  }

  return (
    <section aria-labelledby="projects-heading">
      <div className="mb-6 flex items-center justify-between">
        <h1
          id="projects-heading"
          className="text-2xl font-semibold text-slate-900"
        >
          Projects
        </h1>
      </div>

      {isError ? (
        <ErrorBanner
          message={`Failed to load projects: ${extractErrorMessage(error)}`}
          onRetry={() => void refetch()}
        />
      ) : null}

      {isPending ? (
        <div
          role="status"
          aria-label="Loading projects"
          className="overflow-hidden rounded-lg border border-slate-200 bg-white"
        >
          {Array.from({ length: 5 }).map((_, i) => (
            <SkeletonRow key={i} columns={2} />
          ))}
        </div>
      ) : sorted.length === 0 ? (
        <EmptyState
          title="No projects yet"
          description='Click "New Config" in the top bar to add the first one.'
        />
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <SortableHeader
                  label="Project name"
                  columnKey="project"
                  activeColumn={sortColumn}
                  activeDir={sortDir}
                  onSort={handleSort}
                />
                <SortableHeader
                  label="Config count"
                  columnKey="config_count"
                  activeColumn={sortColumn}
                  activeDir={sortDir}
                  onSort={handleSort}
                />
              </tr>
            </thead>
            <tbody>
              {sorted.map((row) => (
                <tr
                  key={row.project}
                  className="border-t border-slate-100 hover:bg-slate-50"
                >
                  <td className="px-4 py-2">
                    <Link
                      to={`/projects/${encodeURIComponent(row.project)}`}
                      className="font-mono text-slate-900 hover:text-slate-700 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                    >
                      {row.project}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-slate-600">
                    <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                      {row.config_count}
                    </span>
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
