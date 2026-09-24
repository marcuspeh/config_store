// Centralized query-key factory so caches stay consistent across the
// app. Always go through these helpers instead of inlining string keys
// at call sites — otherwise an invalidate-on-mutation elsewhere will
// silently miss a key typo here.

export const queryKeys = {
  projects: () => ["projects"] as const,
  configs: (project: string) => ["configs", project] as const,
  config: (project: string, key: string) =>
    ["config", project, key] as const,
  health: () => ["health"] as const,
} as const;
