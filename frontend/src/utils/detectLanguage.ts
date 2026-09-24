// Cheap language detection for the Monaco editor. The PRD says language
// is "client-only metadata" (no backend persistence) — it's only used
// for syntax highlighting, never for parsing.
//
// Order of attempts matters:
//   1. JSON — strict parse; if it works, it's almost certainly JSON.
//   2. YAML — heuristic: must contain a `:` line, no `{` or `[` to
//      avoid false positives from prose.
//   3. Plaintext — fallback.

export type DetectedLanguage = "json" | "yaml" | "plaintext";

export function detectLanguage(value: string): DetectedLanguage {
  const trimmed = value.trim();
  if (trimmed.length === 0) return "plaintext";

  if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
    try {
      JSON.parse(trimmed);
      return "json";
    } catch {
      // Falls through to the YAML check below.
    }
  }

  // YAML heuristic: a top-level "key: value" line with no JSON braces.
  // We don't run a full YAML parser because the editor handles
  // syntax-highlight fine on a hint and we don't want to pull in
  // another dependency.
  const hasColonLine = /^[^\s#].*:\s*\S/m.test(trimmed);
  if (
    hasColonLine &&
    !trimmed.includes("{") &&
    !trimmed.includes("[")
  ) {
    return "yaml";
  }

  return "plaintext";
}
