import { lazy, Suspense } from "react";
import type { ReactElement } from "react";
import clsx from "clsx";

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
  // Hidden label for screen readers. Monaco's textarea is announced as
  // "code editor" without context; this gives it a meaningful name.
  ariaLabel: string;
}

// Wrapper around @monaco-editor/react's Editor with:
//   - Lazy load (the whole bundle is several MB).
//   - A small loading fallback so the page doesn't flash empty.
//   - A shared aria-label and an outline matching the rest of the UI.
//
// We use the editor's built-in word-wrap so users can toggle it; the
// PRD allows for it being a toggle on the detail page (we surface it
// via the editor's default context menu).
export function MonacoEditor({
  value,
  language,
  readOnly = true,
  onChange,
  className,
  height = "60vh",
  ariaLabel,
}: MonacoEditorProps): ReactElement {
  return (
    <div
      className={clsx(
        "overflow-hidden rounded-lg border border-slate-200 bg-white",
        className,
      )}
    >
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
          // read-only view on §6.3; edit page passes `false`.
          options={{
            readOnly,
            // Word-wrap on by default so long single-line JSON values
            // don't require horizontal scrolling.
            wordWrap: "on",
            // Hide Monaco's default minimap; not useful for short configs.
            minimap: { enabled: false },
            // Strip the read-only banner; the editor chrome is already
            // clear about the page context.
            renderWhitespace: "selection",
            fontSize: 13,
            // Light theme by default; the editor's auto-detection
            // matches OS preference too.
            automaticLayout: true,
            scrollBeyondLastLine: false,
          }}
          onChange={(next) => onChange?.(next ?? "")}
          // The editor needs an aria-label since the inner textarea
          // doesn't get one from Monaco by default.
          // @ts-expect-error -- Monaco's typings don't include `ariaLabel`.
          ariaLabel={ariaLabel}
        />
      </Suspense>
    </div>
  );
}
