import { useMemo, useState } from "react";
import type { ReactElement } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Loader2, Save } from "lucide-react";
import { toast } from "sonner";
import axios from "axios";
import { useProjects } from "../hooks/queries";
import { useCreateConfig } from "../hooks/mutations";
import { extractErrorMessage } from "../api/client";
import { Breadcrumb } from "../components/Breadcrumb";
import { MonacoEditor } from "../components/MonacoEditor";
import { ErrorBanner } from "../components/ErrorBanner";
import { detectLanguage } from "../utils/detectLanguage";
import {
  validateKey,
  validateProject,
  validateValue,
} from "../utils/validation";
import { useDirtyGuard } from "../hooks/useDirtyGuard";

// §6.5 Create Config Page. Two routes drive the same component:
//   - /projects/new            → project field is editable + autocomplete.
//   - /projects/:project/new   → project field is prefilled and disabled.
//
// Validation runs on submit AND on blur; the create mutation handles
// the 409 case from the backend (duplicate key) by surfacing it as an
// inline error with a "use Edit instead" link.

export function CreateConfigPage(): ReactElement {
  const { project: projectParam } = useParams<{ project?: string }>();
  const prefilled = Boolean(projectParam);
  const navigate = useNavigate();

  // Pull the existing project list for the datalist on the editable
  // route. We still call it on the prefilled route so the autocomplete
  // doesn't pop in/out as the user toggles routes — the cost is just
  // one tiny list query.
  const projects = useProjects();

  const [project, setProject] = useState<string>(projectParam ?? "");
  const [key, setKey] = useState<string>("");
  const [value, setValue] = useState<string>("");
  const [touched, setTouched] = useState({
    project: prefilled,
    key: false,
    value: false,
  });

  const create = useCreateConfig();

  const language = useMemo(() => detectLanguage(value), [value]);
  const dirty = project.length > 0 || key.length > 0 || value.length > 0;

  // Same dirty-guard semantics as the edit page. Save in flight turns
  // it off so the user isn't prompted while the request is happening.
  useDirtyGuard({ when: dirty && !create.isPending });

  const projectError = touched.project ? validateProject(project) : null;
  const keyError = touched.key ? validateKey(key) : null;
  const valueError = touched.value ? validateValue(value) : null;
  const hasInlineErrors = Boolean(projectError || keyError || valueError);

  // 409 detection: axios surfaces the status on `error.response.status`.
  const isConflict =
    create.isError &&
    axios.isAxiosError(create.error) &&
    create.error.response?.status === 409;

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setTouched({ project: true, key: true, value: true });

    // Block submit if any field fails client-side validation. We
    // don't bother disabling the button — showing the inline errors
    // after a click is the clearer UX.
    if (validateProject(project) || validateKey(key) || validateValue(value)) {
      return;
    }

    create.mutate(
      { project, key, body: { value } },
      {
        onSuccess: () => {
          toast.success("Created");
          navigate(
            `/projects/${encodeURIComponent(project)}/${encodeURIComponent(key)}`,
          );
        },
        // 4xx/5xx errors are surfaced inline by the page itself, so
        // we don't double up with a toast.
      },
    );
  }

  return (
    <section aria-labelledby="create-heading">
      <Breadcrumb
        items={
          prefilled
            ? [
                { label: "Projects", to: "/" },
                { label: projectParam!, to: `/projects/${encodeURIComponent(projectParam!)}` },
                { label: "New config" },
              ]
            : [
                { label: "Projects", to: "/" },
                { label: "New config" },
              ]
        }
        actions={
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back
          </button>
        }
      />

      <h1
        id="create-heading"
        className="mb-6 text-2xl font-semibold text-slate-900"
      >
        {prefilled ? (
          <>
            New config in{" "}
            <span className="font-mono">{projectParam}</span>
          </>
        ) : (
          "New config"
        )}
      </h1>

      {create.isError && !isConflict ? (
        <ErrorBanner
          message={`Create failed: ${extractErrorMessage(create.error)}`}
        />
      ) : null}

      {isConflict ? (
        <div
          role="alert"
          className="mb-4 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          <p>
            A config with this key already exists. Use{" "}
            <button
              type="button"
              onClick={() =>
                navigate(
                  `/projects/${encodeURIComponent(project)}/${encodeURIComponent(key)}/edit`,
                )
              }
              className="font-medium underline hover:text-amber-700"
            >
              Edit
            </button>{" "}
            to modify it instead.
          </p>
        </div>
      ) : null}

      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        <Field
          id="project"
          label="Project"
          error={projectError}
          helpText={
            prefilled
              ? undefined
              : "Lowercase letters, digits, hyphens, or underscores. Must start with a letter or digit."
          }
        >
          {prefilled ? (
            <input
              id="project"
              type="text"
              value={project}
              disabled
              readOnly
              aria-readonly="true"
              className="w-full rounded-md border border-slate-200 bg-slate-100 px-3 py-1.5 font-mono text-sm text-slate-700 focus:outline-none"
            />
          ) : (
            <>
              <input
                id="project"
                type="text"
                value={project}
                onChange={(e) => setProject(e.target.value)}
                onBlur={() => setTouched((t) => ({ ...t, project: true }))}
                list="existing-projects"
                autoComplete="off"
                spellCheck={false}
                placeholder="my-project"
                className="w-full rounded-md border border-slate-200 bg-white px-3 py-1.5 font-mono text-sm focus:border-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
              />
              <datalist id="existing-projects">
                {(projects.data ?? []).map((p) => (
                  <option key={p.project} value={p.project} />
                ))}
              </datalist>
            </>
          )}
        </Field>

        <Field
          id="key"
          label="Key"
          error={keyError}
          helpText="Lowercase letters, digits, hyphens, underscores, or dots. Must start with a letter or digit."
        >
          <input
            id="key"
            type="text"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            onBlur={() => setTouched((t) => ({ ...t, key: true }))}
            autoComplete="off"
            spellCheck={false}
            placeholder="database_url"
            className="w-full rounded-md border border-slate-200 bg-white px-3 py-1.5 font-mono text-sm focus:border-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
          />
        </Field>

        <Field
          id="value"
          label="Value"
          error={valueError}
          helpText={`Detected language: ${language}`}
        >
          <MonacoEditor
            value={value}
            language={language}
            readOnly={create.isPending}
            onChange={setValue}
            height="40vh"
            ariaLabel="New config value"
          />
        </Field>

        <div className="flex items-center justify-end gap-2 border-t border-slate-200 pt-4">
          <button
            type="submit"
            disabled={create.isPending || hasInlineErrors}
            className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {create.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <Save className="h-4 w-4" aria-hidden="true" />
            )}
            Create
          </button>
        </div>
      </form>
    </section>
  );
}

interface FieldProps {
  id: string;
  label: string;
  error: string | null;
  helpText?: string;
  children: ReactElement;
}

// Simple label + control + (optional error/help) wrapper. Avoids
// re-implementing the same `<label>`/`<input>` association in three
// places below.
function Field({
  id,
  label,
  error,
  helpText,
  children,
}: FieldProps): ReactElement {
  const helpId = helpText ? `${id}-help` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [helpId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div>
      <label
        htmlFor={id}
        className="mb-1 block text-sm font-medium text-slate-700"
      >
        {label}
      </label>
      {/* Children must wire `id={id}` and `aria-describedby={describedBy}` themselves
          because we render non-input controls (Monaco) which can't be wrapped. */}
      <div aria-describedby={describedBy}>{children}</div>
      {helpText ? (
        <p id={helpId} className="mt-1 text-xs text-slate-500">
          {helpText}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} role="alert" className="mt-1 text-xs text-red-700">
          {error}
        </p>
      ) : null}
    </div>
  );
}
