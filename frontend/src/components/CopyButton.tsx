import type { ReactElement } from "react";
import { useState } from "react";
import { Check, Copy } from "lucide-react";
import clsx from "clsx";

interface CopyButtonProps {
  value: string;
  label?: string;
  // Optional `successMessage` overrides the default toast copy.
  successMessage?: string;
}

// "Copy full value to clipboard" button. Used in:
//   - §6.2 row actions
//   - §6.3 detail page footer
// On click we write to the clipboard and flash a "Copied" toast. We
// keep the success message local (no global toast spam) — the brief
// checkmark in the button itself is enough visual confirmation.
export function CopyButton({
  value,
  label = "Copy",
  successMessage = "Copied to clipboard",
}: CopyButtonProps): ReactElement {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      // Reset the icon after a short delay so the success state is
      // visible but doesn't persist forever.
      window.setTimeout(() => setCopied(false), 1500);
    } catch (err) {
      // Fall back to a global toast on permission failure so the
      // user knows why nothing happened. We don't try a textarea
      // fallback here because modern browsers all support the
      // clipboard API and the failure mode is unusual.
      // eslint-disable-next-line no-alert
      window.alert(
        `Could not copy to clipboard: ${(err as Error).message}. ${successMessage} requires the Clipboard API.`,
      );
    }
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      aria-label={label}
      title={label}
      className={clsx(
        "inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-2 py-0.5 text-xs font-medium text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400",
        copied && "border-green-300 bg-green-50 text-green-800",
      )}
    >
      {copied ? (
        <Check className="h-3 w-3" aria-hidden="true" />
      ) : (
        <Copy className="h-3 w-3" aria-hidden="true" />
      )}
      <span>{copied ? "Copied" : label}</span>
      {/* The success message is announced via the icon swap; we don't
          double up on a toast. If `successMessage` is overridden by the
          caller we still surface the original text in `title` for SR
          users. */}
      <span className="sr-only">{successMessage}</span>
    </button>
  );
}
