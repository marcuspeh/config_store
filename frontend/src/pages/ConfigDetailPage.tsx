import { useMemo } from "react";
import type { ReactElement } from "react";
import { Link, useParams } from "react-router-dom";
import { Pencil } from "lucide-react";
import { useConfig } from "../hooks/queries";
import { extractErrorMessage } from "../api/client";
import { Breadcrumb } from "../components/Breadcrumb";
import { MonacoEditor } from "../components/MonacoEditor";
import { CopyButton } from "../components/CopyButton";
import { ErrorBanner } from "../components/ErrorBanner";
import { detectLanguage } from "../utils/detectLanguage";

// §6.3 Config Detail Page. Read-only Monaco view + Edit button + Copy
// in the footer. Language is auto-detected from the value for syntax
// highlighting only (not persisted — PRD §10 decision 2).
export function ConfigDetailPage(): ReactElement {
  const { project = "", key = "" } = useParams<{
    project: string;
    key: string;
  }>();
  const { data, isPending, isError, error, refetch } = useConfig(
    project,
    key,
  );

  const language = useMemo(
    () => (data ? detectLanguage(data.value) : "plaintext"),
    [data],
  );

  return (
    <section aria-labelledby="config-detail-heading">
      <Breadcrumb
        items={[
          { label: "Projects", to: "/" },
          { label: project, to: `/projects/${encodeURIComponent(project)}` },
          { label: key },
        ]}
        actions={
          data ? (
            <Link
              to={`/projects/${encodeURIComponent(project)}/${encodeURIComponent(key)}/edit`}
              className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800"
            >
              <Pencil className="h-4 w-4" aria-hidden="true" />
              Edit
            </Link>
          ) : null
        }
      />

      <div className="mb-4">
        <h1
          id="config-detail-heading"
          className="font-mono text-2xl font-semibold text-slate-900"
        >
          {key || "(no key)"}
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          in <span className="font-mono">{project || "(no project)"}</span>
          {data ? (
            <>
              {" · "}
              <span className="uppercase tracking-wide text-xs text-slate-400">
                {language}
              </span>
            </>
          ) : null}
        </p>
      </div>

      {isError ? (
        <ErrorBanner
          message={`Failed to load config: ${extractErrorMessage(error)}`}
          onRetry={() => void refetch()}
        />
      ) : null}

      {!isPending && isError && (error as { response?: { status?: number } })?.response?.status === 404 ? (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
          <h2 className="text-base font-medium text-slate-900">
            Config not found
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            <span className="font-mono">{project}</span> /{" "}
            <span className="font-mono">{key}</span> doesn't exist.
          </p>
          <Link
            to={`/projects/${encodeURIComponent(project)}`}
            className="mt-4 inline-block text-sm font-medium text-slate-900 hover:underline"
          >
            ← Back to project
          </Link>
        </div>
      ) : data ? (
        <>
          <MonacoEditor
            value={data.value}
            language={language}
            readOnly
            ariaLabel={`Config value for ${project}/${key}`}
          />
          <Footer value={data.value} />
        </>
      ) : null}
    </section>
  );
}

interface FooterProps {
  value: string;
}

function Footer({ value }: FooterProps): ReactElement {
  const lines = value.length === 0 ? 0 : value.split("\n").length;
  const chars = value.length;
  return (
    <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
      <span>
        <span className="font-mono">{lines}</span> line{lines === 1 ? "" : "s"}
        {" · "}
        <span className="font-mono">{chars}</span> char{chars === 1 ? "" : "s"}
      </span>
      <CopyButton value={value} label="Copy value" />
    </div>
  );
}
