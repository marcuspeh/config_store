import { useEffect, useMemo, useState } from "react";
import type { ReactElement } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Loader2, Save, X } from "lucide-react";
import { toast } from "sonner";
import { useConfig } from "../hooks/queries";
import { useUpdateConfig } from "../hooks/mutations";
import { extractErrorMessage } from "../api/client";
import { Breadcrumb } from "../components/Breadcrumb";
import { MonacoEditor } from "../components/MonacoEditor";
import { ErrorBanner } from "../components/ErrorBanner";
import { detectLanguage } from "../utils/detectLanguage";
import { useDirtyGuard } from "../hooks/useDirtyGuard";

// §6.4 Edit Page. Editable Monaco prefilled with the current value,
// Save (PUT) with spinner + dirty guard, Cancel with confirm.
//
// `language` is auto-detected but the user can't override it in v1
// (PRD §10 decision 2).
export function ConfigEditPage(): ReactElement {
  const { project = "", key = "" } = useParams<{
    project: string;
    key: string;
  }>();
  const navigate = useNavigate();

  const detail = useConfig(project, key);
  const update = useUpdateConfig();

  // Local edit buffer. Initialised from the loaded value; subsequent
  // edits do NOT re-sync from the server (we don't want to overwrite
  // the user's in-progress changes on background refetches).
  const [draft, setDraft] = useState<string>("");
  const [initialised, setInitialised] = useState(false);

  useEffect(() => {
    if (detail.data && !initialised) {
      setDraft(detail.data.value);
      setInitialised(true);
    }
  }, [detail.data, initialised]);

  const dirty = initialised && detail.data ? draft !== detail.data.value : false;
  const language = useMemo(
    () => (detail.data ? detectLanguage(detail.data.value) : "plaintext"),
    [detail.data],
  );

  // Dirty guard covers: breadcrumbs, browser back/forward, tab close.
  // Cancel is handled explicitly below with a window.confirm.
  useDirtyGuard({ when: dirty && !update.isPending });

  function handleCancel() {
    if (!dirty || window.confirm("Discard unsaved changes?")) {
      navigate(
        `/projects/${encodeURIComponent(project)}/${encodeURIComponent(key)}`,
      );
    }
  }

  function handleSave() {
    update.mutate(
      { project, key, body: { value: draft } },
      {
        onSuccess: () => {
          toast.success("Saved");
          navigate(
            `/projects/${encodeURIComponent(project)}/${encodeURIComponent(key)}`,
          );
        },
        onError: (err) => {
          // The dirty guard stays off while the mutation is in flight
          // so the user can retry without being prompted. Surface the
          // message inline below the editor instead of as a toast so
          // they can see it while editing.
          toast.error(`Save failed: ${extractErrorMessage(err)}`);
        },
      },
    );
  }

  return (
    <section aria-labelledby="config-edit-heading">
      <Breadcrumb
        items={[
          { label: "Projects", to: "/" },
          { label: project, to: `/projects/${encodeURIComponent(project)}` },
          { label: key, to: `/projects/${encodeURIComponent(project)}/${encodeURIComponent(key)}` },
          { label: "Edit" },
        ]}
        actions={
          <>
            <button
              type="button"
              onClick={handleCancel}
              disabled={update.isPending}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <X className="h-4 w-4" aria-hidden="true" />
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={update.isPending || !dirty || detail.isPending}
              className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {update.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Save className="h-4 w-4" aria-hidden="true" />
              )}
              Save
            </button>
          </>
        }
      />

      <div className="mb-4">
        <h1
          id="config-edit-heading"
          className="font-mono text-2xl font-semibold text-slate-900"
        >
          {key || "(no key)"}
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          in <span className="font-mono">{project || "(no project)"}</span>
          {" · "}
          <span className="uppercase tracking-wide text-xs text-slate-400">
            {language}
          </span>
          {dirty ? (
            <span
              className="ml-2 inline-flex items-center rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-800"
              aria-live="polite"
            >
              Unsaved changes
            </span>
          ) : null}
        </p>
      </div>

      {detail.isError ? (
        <ErrorBanner
          message={`Failed to load config: ${extractErrorMessage(detail.error)}`}
          onRetry={() => void detail.refetch()}
        />
      ) : null}

      {update.isError ? (
        <ErrorBanner
          message={`Save failed: ${extractErrorMessage(update.error)}`}
        />
      ) : null}

      {!detail.isPending && detail.isError ? null : detail.data ? (
        <MonacoEditor
          value={draft}
          language={language}
          readOnly={update.isPending}
          onChange={setDraft}
          height="65vh"
          ariaLabel={`Editing ${project}/${key}`}
        />
      ) : (
        <div
          className="flex h-[65vh] items-center justify-center rounded-lg border border-slate-200 bg-white text-sm text-slate-500"
          role="status"
        >
          Loading…
        </div>
      )}

      <div className="mt-2 text-xs text-slate-500">
        <Link
          to={`/projects/${encodeURIComponent(project)}/${encodeURIComponent(key)}`}
          className="hover:underline"
        >
          ← Back to detail
        </Link>
      </div>
    </section>
  );
}
