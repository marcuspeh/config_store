import { useDeferredValue, useEffect, useMemo, useState } from "react";
import type { ReactElement } from "react";
import { useSearchParams } from "react-router-dom";
import {
  AlertTriangle,
  Database,
  Edit2,
  FolderPlus,
  Info,
  Plus,
  RefreshCw,
  Save,
  Search,
  Server,
  Settings2,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import axios from "axios";
import { useProjects, useProjectConfigs } from "../hooks/queries";
import {
  useCreateConfig,
  useDeleteConfig,
  useRefreshCache,
  useUpdateConfig,
} from "../hooks/mutations";
import { useHealthStatus } from "../hooks/useHealthStatus";
import { extractErrorMessage } from "../api/client";
import { validateKey, validateProject, validateValue } from "../utils/validation";
import { detectLanguage } from "../utils/detectLanguage";
import { Button } from "../components/ui/Button";
import { Input, Textarea } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { ErrorBanner } from "../components/ErrorBanner";
import { CopyButton } from "../components/CopyButton";
import { cn } from "../lib/utils";

const PAGE_SIZE = 12;

type ModalKind = "add" | "edit" | "delete" | "new-project" | null;

// TCC Config workspace. Single-screen replacement for the previous
// route-based pages: project sidebar on the left, filtered config list
// on the right, CRUD through modals. All state that should survive a
// refresh or be shareable lives in the query string (project, modal,
// configId, limit); form buffers are local.
export function TccConfigPage(): ReactElement {
  const [searchParams, setSearchParams] = useSearchParams();

  const activeProject = searchParams.get("project") ?? "";
  const modal = searchParams.get("modal") as ModalKind;
  const configId = searchParams.get("configId") ?? "";
  const limit = Number(searchParams.get("limit") ?? PAGE_SIZE);

  const projects = useProjects();
  const configs = useProjectConfigs(activeProject);
  const health = useHealthStatus();
  const refresh = useRefreshCache();

  const create = useCreateConfig();
  const update = useUpdateConfig();
  const remove = useDeleteConfig();

  const [query, setQuery] = useState("");
  // useDeferredValue keeps the filter input snappy on long lists by
  // letting React render the input update immediately and re-running
  // the filter on the next tick. The fallback is non-trivial —
  // toLowerCase() over every config's value on every keystroke.
  const deferredQuery = useDeferredValue(query);
  const [form, setForm] = useState({ key: "", value: "" });
  const [newProject, setNewProject] = useState({
    project: "",
    key: "",
    value: "",
  });
  const [formError, setFormError] = useState<string | null>(null);

  const projectList = useMemo(
    () => projects.data ?? [],
    [projects.data],
  );

  // Land on the first project when the URL doesn't name one.
  useEffect(() => {
    if (activeProject || projectList.length === 0) return;
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set("project", projectList[0].project);
        return next;
      },
      { replace: true },
    );
  }, [activeProject, projectList, setSearchParams]);

  const filtered = useMemo(() => {
    const list = configs.data ?? [];
    const q = deferredQuery.trim().toLowerCase();
    if (!q) return list;
    return list.filter(
      (c) =>
        c.config_key.toLowerCase().includes(q) ||
        c.value.toLowerCase().includes(q),
    );
  }, [configs.data, deferredQuery]);

  const displayed = filtered.slice(0, limit);
  const hasMore = displayed.length < filtered.length;

  function updateParams(updates: Record<string, string | null>) {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        for (const [k, v] of Object.entries(updates)) {
          if (v === null) next.delete(k);
          else next.set(k, v);
        }
        return next;
      },
      { replace: true },
    );
  }

  function closeModal() {
    setForm({ key: "", value: "" });
    setNewProject({ project: "", key: "", value: "" });
    setFormError(null);
    updateParams({ modal: null, configId: null });
  }

  function openAdd() {
    setForm({ key: "", value: "" });
    setFormError(null);
    updateParams({ modal: "add", configId: null });
  }

  function openEdit(key: string) {
    const target = (configs.data ?? []).find((c) => c.config_key === key);
    setForm({ key, value: target?.value ?? "" });
    setFormError(null);
    updateParams({ modal: "edit", configId: key });
  }

  function openDelete(key: string) {
    setFormError(null);
    updateParams({ modal: "delete", configId: key });
  }

  function handleRefresh() {
    refresh.mutate(undefined, {
      onSuccess: () => toast.success("Cache refreshed"),
      onError: (err) =>
        toast.error(`Refresh failed: ${extractErrorMessage(err)}`),
    });
  }

  // 409 means the key already exists — point the user at Edit instead.
  function conflictMessage(err: unknown): string | null {
    return axios.isAxiosError(err) && err.response?.status === 409
      ? `A config named "${form.key}" already exists in this project.`
      : null;
  }

  // 404 means the row vanished between the user opening the modal and
  // submitting (e.g. deleted in another tab). Surface a friendlier
  // message than the default "Request failed with status code 404".
  function notFoundMessage(err: unknown): string | null {
    return axios.isAxiosError(err) && err.response?.status === 404
      ? "This config no longer exists. Refresh the list and try again."
      : null;
  }

  function handleSaveConfig() {
    const keyError = validateKey(form.key);
    const valueError = validateValue(form.value);
    if (keyError || valueError) {
      setFormError(keyError ?? valueError);
      return;
    }

    if (modal === "edit") {
      if (!activeProject || !configId) {
        setFormError("Missing project or config key. Refresh and retry.");
        return;
      }
      update.mutate(
        { project: activeProject, key: configId, body: { value: form.value } },
        {
          onSuccess: () => {
            toast.success("Saved");
            closeModal();
          },
          onError: (err) =>
            setFormError(
              notFoundMessage(err) ?? `Save failed: ${extractErrorMessage(err)}`,
            ),
        },
      );
      return;
    }

    if (!activeProject) {
      setFormError("Select a project before creating a config.");
      return;
    }
    create.mutate(
      { project: activeProject, key: form.key, body: { value: form.value } },
      {
        onSuccess: () => {
          toast.success(`Created ${form.key}`);
          closeModal();
        },
        onError: (err) =>
          setFormError(
            conflictMessage(err) ?? `Create failed: ${extractErrorMessage(err)}`,
          ),
      },
    );
  }

  function handleCreateProject() {
    const projectError = validateProject(newProject.project);
    const keyError = validateKey(newProject.key);
    const valueError = validateValue(newProject.value);
    if (projectError || keyError || valueError) {
      setFormError(projectError ?? keyError ?? valueError);
      return;
    }

    create.mutate(
      {
        project: newProject.project,
        key: newProject.key,
        body: { value: newProject.value },
      },
      {
        onSuccess: () => {
          toast.success(`Project ${newProject.project} initialized`);
          closeModal();
          updateParams({ project: newProject.project });
        },
        onError: (err) =>
          setFormError(
            conflictMessage(err) ??
              `Create failed: ${extractErrorMessage(err)}`,
          ),
      },
    );
  }

  function handleDelete() {
    if (!activeProject || !configId) {
      setFormError("Missing project or config key. Refresh and retry.");
      return;
    }
    remove.mutate(
      { project: activeProject, key: configId },
      {
        onSuccess: () => {
          toast.success(`Deleted ${configId}`);
          closeModal();
        },
        onError: (err) =>
          setFormError(
            notFoundMessage(err) ?? `Delete failed: ${extractErrorMessage(err)}`,
          ),
      },
    );
  }

  const isEditing = modal === "edit";

  return (
    <div className="relative flex h-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm md:flex-row">
      <div className="absolute left-0 top-0 z-10 hidden h-full w-1 bg-gradient-to-b from-blue-500 to-indigo-500 md:block" />

      {/* Sidebar — projects */}
      <aside className="flex w-full shrink-0 flex-col border-b border-slate-200 bg-slate-50 md:w-64 md:border-b-0 md:border-r">
        <div className="flex items-center gap-2 p-5 text-slate-800">
          <Settings2 className="h-5 w-5 text-indigo-600" aria-hidden="true" />
          <h1 className="font-mono text-base font-semibold tracking-wider">
            TCC CONFIG
          </h1>
        </div>

        <div className="flex-1 space-y-1 overflow-y-auto p-3">
          <div className="mb-3 flex items-center justify-between pl-2 pr-1">
            <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">
              Projects
            </span>
            <button
              type="button"
              onClick={() => updateParams({ modal: "new-project" })}
              className="rounded p-1 text-slate-400 transition-colors hover:bg-indigo-50 hover:text-indigo-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              title="Add new project"
              aria-label="Add new project"
            >
              <FolderPlus className="h-4 w-4" />
            </button>
          </div>

          {projects.isPending ? (
            <p className="px-3 py-2 text-sm text-slate-400">Loading…</p>
          ) : projects.isError ? (
            <ErrorBanner
              message={`Failed to load projects: ${extractErrorMessage(projects.error)}`}
              onRetry={() => void projects.refetch()}
            />
          ) : projectList.length === 0 ? (
            <p className="px-3 py-2 text-sm text-slate-400">
              No projects yet.
            </p>
          ) : (
            projectList.map((p) => (
              <button
                key={p.project}
                type="button"
                onClick={() => updateParams({ project: p.project })}
                aria-current={activeProject === p.project}
                className={cn(
                  "flex w-full items-center gap-3 rounded-md border px-3 py-2.5 text-left transition-all",
                  activeProject === p.project
                    ? "border-blue-200 bg-blue-50 text-blue-700 shadow-sm"
                    : "border-transparent text-slate-600 hover:bg-slate-200/50 hover:text-slate-900",
                )}
              >
                <Database className="h-4 w-4 opacity-70" aria-hidden="true" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">
                    {p.project}
                  </span>
                  <span className="mt-0.5 block font-mono text-[10px] uppercase tracking-wide opacity-70">
                    {p.config_count} {p.config_count === 1 ? "config" : "configs"}
                  </span>
                </span>
              </button>
            ))
          )}
        </div>

        <div className="border-t border-slate-200 p-3">
          <div className="flex items-center justify-between gap-2">
            <span
              className={cn(
                "flex items-center gap-1.5 text-xs",
                health.isError ? "text-slate-400" : "text-slate-500",
              )}
              title={
                health.lastUpdatedAt
                  ? `Last updated ${new Date(health.lastUpdatedAt).toLocaleTimeString()}`
                  : "Never updated"
              }
            >
              {health.isError || health.isStale ? (
                <AlertTriangle className="h-3 w-3" aria-hidden="true" />
              ) : null}
              {health.isError
                ? "Offline"
                : health.isStale
                  ? "Stale"
                  : `${health.data?.stats.projects_loaded ?? "—"} projects · ${health.data?.stats.cache_keys_total ?? "—"} keys`}
            </span>
            <Button
              size="sm"
              variant="secondary"
              onClick={handleRefresh}
              disabled={refresh.isPending}
              aria-label="Refresh cache"
            >
              <RefreshCw
                className={cn("h-3 w-3", refresh.isPending && "animate-spin")}
                aria-hidden="true"
              />
              Refresh
            </Button>
          </div>
        </div>
      </aside>

      {/* Main content — config list */}
      <section className="flex min-h-0 flex-1 flex-col bg-white">
        <div className="flex items-center justify-between gap-4 border-b border-slate-200 px-6 py-4">
          <div className="max-w-md flex-1">
            <Input
              icon={<Search className="h-4 w-4" aria-hidden="true" />}
              placeholder="Filter configs by key or value..."
              aria-label={
                activeProject
                  ? `Filter configs in ${activeProject} by key or value`
                  : "Filter configs by key or value"
              }
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                // Reset pagination when the filter changes — the
                // current `limit` in the URL was set against the
                // pre-filter list and "View More" would otherwise
                // never appear for a search that shrinks the list.
                if (limit !== PAGE_SIZE) updateParams({ limit: null });
              }}
            />
          </div>
          <Button
            onClick={openAdd}
            disabled={!activeProject}
            className="flex-shrink-0 gap-2 shadow-sm"
          >
            <Plus className="h-4 w-4" aria-hidden="true" /> Add Config
          </Button>
        </div>

        <div className="flex-1 overflow-auto bg-slate-50/50 p-6">
          {configs.isError ? (
            <ErrorBanner
              message={`Failed to load configs: ${extractErrorMessage(configs.error)}`}
              onRetry={() => void configs.refetch()}
            />
          ) : null}

          {configs.isPending ? (
            <ul className="space-y-3" role="status" aria-label="Loading configs">
              {Array.from({ length: 6 }).map((_, i) => (
                <li
                  key={i}
                  className="h-[86px] animate-pulse rounded-lg border border-slate-200 bg-white"
                />
              ))}
            </ul>
          ) : displayed.length === 0 ? (
            <div className="mx-auto mt-10 max-w-lg rounded-xl border-2 border-dashed border-slate-200 bg-white px-6 py-20 text-center text-slate-500">
              <Server className="mx-auto mb-4 h-12 w-12 text-slate-300" aria-hidden="true" />
              <p className="text-lg font-medium text-slate-700">
                {query ? "No matching configs" : "No configurations found"}
              </p>
              <p className="mb-6 mt-1 text-sm">
                {query
                  ? "Try a different key or value."
                  : "Add the first config to this project to get started."}
              </p>
              <Button onClick={openAdd} className="gap-2 shadow-sm">
                <Plus className="h-4 w-4" aria-hidden="true" /> Add Config
              </Button>
            </div>
          ) : (
            <div className="space-y-6 pb-8">
              <ul className="flex flex-col gap-3">
                {displayed.map((config) => (
                  <li
                    key={config.config_key}
                    className="group relative flex flex-col gap-4 overflow-hidden rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition-colors hover:border-indigo-300 md:flex-row md:items-start"
                  >
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-transparent transition-colors group-hover:bg-indigo-500" />

                    <div className="flex min-w-0 flex-1 items-start justify-between md:w-1/3 md:flex-none md:min-w-[200px] md:justify-start">
                      <button
                        type="button"
                        onClick={() => openEdit(config.config_key)}
                        className="break-all pr-2 text-left font-mono text-sm font-bold text-slate-800 hover:text-indigo-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                      >
                        {config.config_key}
                      </button>
                      <RowActions
                        configKey={config.config_key}
                        onEdit={openEdit}
                        onDelete={openDelete}
                      />
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 shadow-inner">
                        <div className="max-h-32 overflow-y-auto break-all font-mono text-xs leading-relaxed text-slate-700">
                          {config.value}
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>

              {hasMore ? (
                <div className="flex justify-center pt-2">
                  <Button
                    variant="secondary"
                    className="rounded-full shadow-sm"
                    onClick={() =>
                      updateParams({ limit: String(limit + PAGE_SIZE) })
                    }
                  >
                    View More Configs
                  </Button>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </section>

      {/* Add / Edit config */}
      <Modal
        isOpen={modal === "add" || modal === "edit"}
        onClose={closeModal}
        title={isEditing ? "Edit Configuration" : "Add Configuration"}
      >
        <div className="space-y-4 py-4">
          {formError ? (
            <p
              role="alert"
              className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
            >
              {formError}
            </p>
          ) : null}
          <div className="space-y-2">
            <label
              htmlFor="config-key"
              className="text-xs font-semibold uppercase tracking-wider text-slate-500"
            >
              Key
            </label>
            <Input
              id="config-key"
              className="font-mono"
              value={form.key}
              readOnly={isEditing}
              aria-readonly={isEditing}
              onChange={(e) => setForm({ ...form, key: e.target.value })}
              placeholder="e.g. max_connections"
            />
          </div>
          <div className="space-y-2">
            <label
              htmlFor="config-value"
              className="text-xs font-semibold uppercase tracking-wider text-slate-500"
            >
              Value
            </label>
            <Textarea
              id="config-value"
              className="min-h-[140px] font-mono"
              value={form.value}
              onChange={(e) => setForm({ ...form, value: e.target.value })}
              placeholder={`Value (${detectLanguage(form.value)})`}
              spellCheck={false}
            />
          </div>
        </div>
        <div className="mt-4 flex justify-end gap-3 border-t border-slate-100 pt-4">
          <Button variant="ghost" onClick={closeModal}>
            Cancel
          </Button>
          <Button
            onClick={handleSaveConfig}
            disabled={
              !form.key ||
              create.isPending ||
              update.isPending
            }
          >
            <Save className="mr-2 h-4 w-4" aria-hidden="true" />
            {isEditing ? "Save Changes" : "Create Config"}
          </Button>
        </div>
      </Modal>

      {/* New project — a project is implicit, created by its first config */}
      <Modal
        isOpen={modal === "new-project"}
        onClose={closeModal}
        title="New Project Namespace"
      >
        <div className="space-y-4 py-4">
          {formError ? (
            <p
              role="alert"
              className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
            >
              {formError}
            </p>
          ) : null}
          <div className="flex gap-3 rounded-lg border border-indigo-100 bg-indigo-50 p-3 text-sm text-indigo-800">
            <Info className="mt-0.5 h-5 w-5 flex-shrink-0 text-indigo-600" aria-hidden="true" />
            <div>
              <p className="mb-1 font-medium">Projects are implicit namespaces.</p>
              <p className="leading-relaxed opacity-90">
                Configs are stored as{" "}
                <code className="rounded bg-white/60 px-1 py-0.5 font-mono text-xs">
                  project-key = value
                </code>
                , so a project exists once it has at least one config. Define
                the first key to create it.
              </p>
            </div>
          </div>

          <div className="space-y-2 pt-2">
            <label
              htmlFor="project-name"
              className="text-xs font-semibold uppercase tracking-wider text-slate-500"
            >
              Project Name
            </label>
            <Input
              id="project-name"
              value={newProject.project}
              onChange={(e) =>
                setNewProject({ ...newProject, project: e.target.value })
              }
              placeholder="e.g. auth-service"
            />
          </div>

          <div className="mt-2 grid grid-cols-2 gap-4 border-t border-slate-100 pt-4">
            <div className="col-span-2 space-y-2">
              <label
                htmlFor="project-first-key"
                className="text-xs font-semibold uppercase tracking-wider text-slate-500"
              >
                First Config Key
              </label>
              <Input
                id="project-first-key"
                className="font-mono"
                value={newProject.key}
                onChange={(e) =>
                  setNewProject({ ...newProject, key: e.target.value })
                }
                placeholder="e.g. port"
              />
            </div>
            <div className="col-span-2 space-y-2">
              <label
                htmlFor="project-first-value"
                className="text-xs font-semibold uppercase tracking-wider text-slate-500"
              >
                Value
              </label>
              <Textarea
                id="project-first-value"
                className="min-h-[90px] font-mono"
                value={newProject.value}
                onChange={(e) =>
                  setNewProject({ ...newProject, value: e.target.value })
                }
                placeholder="Value"
                spellCheck={false}
              />
            </div>
          </div>
        </div>
        <div className="mt-4 flex justify-end gap-3 border-t border-slate-100 pt-4">
          <Button variant="ghost" onClick={closeModal}>
            Cancel
          </Button>
          <Button
            onClick={handleCreateProject}
            disabled={!newProject.project || !newProject.key || create.isPending}
          >
            <FolderPlus className="mr-2 h-4 w-4" aria-hidden="true" />
            Initialize Project
          </Button>
        </div>
      </Modal>

      {/* Delete confirmation */}
      <Modal
        isOpen={modal === "delete"}
        onClose={closeModal}
        title="Delete Configuration"
      >
        <div className="space-y-4 py-6">
          {formError ? (
            <p
              role="alert"
              className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
            >
              {formError}
            </p>
          ) : null}
          <p className="text-slate-600">
            Delete{" "}
            <span className="font-mono font-medium text-slate-900">
              {configId}
            </span>{" "}
            from{" "}
            <span className="font-mono">{activeProject}</span>? This cannot be
            undone and might affect the running application.
          </p>
        </div>
        <div className="mt-4 flex justify-end gap-3 border-t border-slate-100 pt-4">
          <Button variant="secondary" onClick={closeModal}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleDelete} disabled={remove.isPending}>
            <Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
            Delete Config
          </Button>
        </div>
      </Modal>
    </div>
  );
}

interface RowActionsProps {
  configKey: string;
  onEdit: (key: string) => void;
  onDelete: (key: string) => void;
}

// Always visible on touch, hover-revealed from md up — hover-only
// actions are unreachable on a phone.
function RowActions({
  configKey,
  onEdit,
  onDelete,
}: RowActionsProps): ReactElement {
  return (
    <div className="flex shrink-0 items-center gap-1 md:opacity-0 md:transition-opacity md:group-hover:opacity-100 md:group-focus-within:opacity-100">
      <Button
        size="sm"
        variant="ghost"
        onClick={() => onEdit(configKey)}
        aria-label={`Edit ${configKey}`}
        className="h-8 w-8 rounded-md border border-slate-200 bg-white p-0 text-slate-500 hover:border-indigo-200 hover:text-indigo-600 md:border-transparent md:bg-transparent"
      >
        <Edit2 className="h-4 w-4" aria-hidden="true" />
      </Button>
      <CopyButton value={configKey} label="Copy key" />
      <Button
        size="sm"
        variant="ghost"
        onClick={() => onDelete(configKey)}
        aria-label={`Delete ${configKey}`}
        className="h-8 w-8 rounded-md border border-slate-200 bg-white p-0 text-slate-500 hover:border-red-200 hover:text-red-600 md:border-transparent md:bg-transparent"
      >
        <Trash2 className="h-4 w-4" aria-hidden="true" />
      </Button>
    </div>
  );
}