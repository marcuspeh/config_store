import type { ReactElement } from "react";
import clsx from "clsx";
import { isTruncated } from "../utils/truncate";

interface ConfigValuePreviewProps {
  value: string;
  className?: string;
}

// Renders a single config value in the §6.2 row preview column.
//
// Rules (PRD §8):
//   - Empty value: `<empty>` placeholder.
//   - Otherwise render in a `<pre>` element preserving newlines.
//   - Truncation is purely visual via CSS (max-height: 3em,
//     overflow:hidden). We do NOT slice the string — multi-line JSON
//     and YAML stay readable.
//   - When `isTruncated(value)` is true, append a "Show full value →"
//     hint that inherits the link behaviour of the surrounding row.
export function ConfigValuePreview({
  value,
  className,
}: ConfigValuePreviewProps): ReactElement {
  if (value.length === 0) {
    return (
      <span
        className={clsx(
          "inline-block rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-slate-400",
          className,
        )}
      >
        {"<empty>"}
      </span>
    );
  }

  const truncated = isTruncated(value);

  return (
    <div className={clsx("relative", className)}>
      <pre
        className={clsx(
          "whitespace-pre-wrap break-words font-mono text-xs text-slate-700",
          // Only apply the clamp when we know the value exceeds the
          // threshold — avoids an unnecessary scrollbar on short values.
          truncated && "max-h-[3em] overflow-hidden",
        )}
      >
        {value}
      </pre>
      {truncated ? (
        <span className="mt-1 inline-block text-[10px] font-medium text-slate-500 group-hover:underline">
          Show full value →
        </span>
      ) : null}
    </div>
  );
}
