import { lazy, Suspense, useState } from "react";
import type { ReactElement } from "react";
import clsx from "clsx";
import { Code, Maximize2 } from "lucide-react";
import { useMediaQuery } from "../hooks/useMediaQuery";

// Lazy-load the Monaco editor so it never lands in the bundle for the
// projects list / project configs pages. PRD §8: "loaded via
// React.lazy + Suspense, scoped to detail/edit/create routes only".
const MonacoEditorLazy = lazy(async () => {
  const mod = await import("@monaco-editor/react");
  return { default: mod.Editor };
});

interface MonacoEditorProps {
  value: string;
  language: "json" | "yaml" | "plaintext";
  readOnly?: boolean;
  onChange?: (next: string) => void;
  className?: string;
  height?: string;
  ariaLabel: string;
}

// Breakpoint at which we automatically fall back to the plain
// `<textarea>`. PRD §11: "On mobile, the editor goes full-bleed and
// offers a fallback <textarea> toggle if Monaco becomes unusable on
// narrow screens."
const MOBILE_BREAKPOINT = "(max-width: 767px)";

// Wrapper around @monaco-editor/react's Editor with:
//   - Lazy load (the whole bundle is several MB).
//   - Mobile `<textarea>` fallback (auto + manual toggle).
//   - A small loading fallback so the page doesn't flash empty.
//   - A shared aria-label and an outline matching the rest of the UI.
export function MonacoEditor({
  value,
  language,
  readOnly = true,
  onChange,
  className,
  height = "60vh",
  ariaLabel,
}: MonacoEditorProps): ReactElement {
  const isNarrow = useMediaQuery(MOBILE_BREAKPOINT);
  // `userOverrodeTextarea` lets the user opt back into Monaco even on
  // a narrow viewport, or force-textarea on a wide one. The auto
  // fallback only kicks in until the user makes an explicit choice.
  const [userOverrodeTextarea, setUserOverrodeTextarea] =
    useState<boolean | null>(null);

  const useTextarea = userOverrodeTextarea ?? isNarrow;

  return (
    <div
      className={clsx(
        "overflow-hidden rounded-lg border border-slate-200 bg-white",
        className,
      )}
    >
      <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50 px-3 py-1.5 text-xs text-slate-500">
        <span className="font-mono uppercase tracking-wide">{language}</span>
        <button
          type="button"
          onClick={() =>
            setUserOverrodeTextarea((prev) => !(prev ?? isNarrow))
          }
          aria-pressed={useTextarea}
          title={
            useTextarea
              ? "Switch to Monaco editor (syntax highlighting)"
              : "Switch to plain text editor (works better on small screens)"
          }
          className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-2 py-0.5 font-medium text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
        >
          {useTextarea ? (
            <>
              <Maximize2 className="h-3 w-3" aria-hidden="true" />
              Use rich editor
            </>
          ) : (
            <>
              <Code className="h-3 w-3" aria-hidden="true" />
              Use plain text
            </>
          )}
        </button>
      </div>

      {useTextarea ? (
        <textarea
          value={value}
          readOnly={readOnly}
          onChange={(e) => onChange?.(e.target.value)}
          aria-label={ariaLabel}
          spellCheck={false}
          className={clsx(
            "block w-full resize-none border-0 p-3 font-mono text-xs text-slate-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400",
            readOnly && "bg-slate-50",
          )}
          style={{ height }}
        />
      ) : (
        <Suspense
          fallback={
            <div
              className="flex items-center justify-center text-sm text-slate-500"
              style={{ height }}
            >
              Loading editor…
            </div>
          }
        >
          <MonacoEditorLazy
            height={height}
            defaultLanguage={language}
            language={language}
            value={value}
            options={{
              readOnly,
              wordWrap: "on",
              minimap: { enabled: false },
              renderWhitespace: "selection",
              fontSize: 13,
              automaticLayout: true,
              scrollBeyondLastLine: false,
            }}
            onChange={(next) => onChange?.(next ?? "")}
            // @ts-expect-error -- Monaco's typings don't include `ariaLabel`.
            ariaLabel={ariaLabel}
          />
        </Suspense>
      )}
    </div>
  );
}
