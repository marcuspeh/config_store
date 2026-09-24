// Truncation rule for §6.2 config-value previews. PRD §8 spec:
//
//   - Threshold: if `value` is longer than 120 characters OR contains
//     more than 3 lines, truncate.
//   - Empty value: render `<empty>` placeholder (handled in the
//     component, not here).
//
// We intentionally do NOT try to slice the string at a "nice" position
// — previews are best-effort and the detail page is authoritative. The
// renderer uses CSS (max-height + overflow) to do the actual visual
// truncation so multi-line values stay readable.
export const TRUNCATE_MAX_CHARS = 120;
export const TRUNCATE_MAX_LINES = 3;

export function isTruncated(value: string): boolean {
  if (value.length > TRUNCATE_MAX_CHARS) return true;
  // `split("\n")` gives at least one element for any string.
  if (value.split("\n").length > TRUNCATE_MAX_LINES) return true;
  return false;
}
