# Implementation Plan: Config Store Admin UI

Companion to `PRD.md`. Each task leaves the app in a runnable state. Tasks are ordered; later tasks depend on earlier ones.

---

## Phase A — Foundation

### Task 1 — Scaffold frontend shell
**Goal:** A runnable Vite + React + Tailwind SPA with a top-bar layout and route placeholders for all 5 routes, packaged for both dev (Vite proxy) and prod (nginx reverse proxy).

**Files to create:**
- `frontend/package.json` — dependencies: `react`, `react-dom`, `react-router-dom`, `@tanstack/react-query`, `axios`, `clsx`, `lucide-react`, `sonner`, `@monaco-editor/react`, `react-hook-form`, `zod`; dev deps: `vite`, `@vitejs/plugin-react`, `typescript`, `tailwindcss`, `postcss`, `autoprefixer`, `@types/*`.
- `frontend/tsconfig.json` — strict mode, `react-jsx`, includes `src/`, types `["vite/client", "node"]`.
- `frontend/vite.config.ts` — `react` plugin, dev server on `:5173`, `/api` proxy → `http://localhost:6002` (override via `VITE_DEV_API_TARGET`).
- `frontend/index.html` — root `#root`, mounts `/src/main.tsx`.
- `frontend/postcss.config.js`, `frontend/tailwind.config.ts` — Tailwind setup.
- `frontend/src/main.tsx` — React Router with placeholder routes for `/`, `/projects/new`, `/projects/:project`, `/projects/:project/new`, `/projects/:project/:key`, `/projects/:project/:key/edit`; QueryClientProvider, Sonner Toaster.
- `frontend/src/components/Layout.tsx` — top bar (logo, "+ New Config" button, Refresh button, cache stats placeholder); `<Outlet/>` for page content.
- `frontend/src/styles/index.css` — Tailwind directives + CSS variables for theming.
- `frontend/src/api/client.ts` — axios instance resolving `VITE_API_URL` with `/api` fallback; `extractErrorMessage` helper. (Mirror of `../logging_system/frontend/src/api/client.ts`.)
- `frontend/src/api/types.ts` — `Config`, `Project`, `HealthResponse`, `CacheStats` types matching §7 backend contract.
- `frontend/src/api/configs.ts` — typed wrappers for each endpoint (stubs returning `Promise.reject("not implemented")` until Phase B lands).
- `frontend/.env.example` — `VITE_API_URL=/api`.
- `frontend/.env.development` — empty.
- `frontend/.dockerignore`, `frontend/.gitignore`.
- `frontend/nginx.conf` — SPA fallback + `/api/` → `http://config_store:6002/`.
- `frontend/Dockerfile` — multi-stage Node 20 build → nginx 1.27-alpine, `VITE_API_URL` build arg.
- `frontend/docker-compose.yml` — external `config-store-net`, host port `:3000` → container `:80`.

**Acceptance:**
- `npm run dev` serves the app on `:5173`.
- `docker compose up -d --build` serves the app on `:3000`.
- Top bar renders; clicking each placeholder route renders an empty page with the correct breadcrumb.

---

### Task 2 — API client + types
**Goal:** Replace stubs in `src/api/configs.ts` with real typed functions; TanStack Query hooks per endpoint.

**Files to modify/create:**
- `frontend/src/api/configs.ts` — typed functions: `listProjects()`, `listConfigs(project)`, `getConfig(project, key)`, `createConfig(...)`, `updateConfig(...)`, `refresh()`.
- `frontend/src/hooks/queries.ts` — TanStack Query hooks wrapping each function with appropriate keys.
- `frontend/src/hooks/mutations.ts` — `useCreateConfig`, `useUpdateConfig`, `useRefreshCache`.

**Acceptance:**
- Functions type-check; calling them with valid args produces correctly typed responses.
- No UI consumes them yet — verification is via temporary throwaway calls in `main.tsx` (then removed).

---

## Phase B — Backend

### Task 3 — Backend list endpoints
**Goal:** Add `GET /projects` and `GET /projects/{project}/configs` to the FastAPI service.

**Files to modify/create:**
- `backend/app/database/repositories/config.py` — add `distinct_projects() -> list[tuple[str, int]]` and `list_for_project(project) -> list[dict]`.
- `backend/app/services/config_service.py` — add `list_projects()` and `list_configs(project)` passthroughs.
- `backend/app/core/models.py` — add `ProjectSummary` (`project: str`, `config_count: int`) and `ConfigListItem` (`config_key: str`, `value: str`).
- `backend/app/api/routes.py` — add the two new GET routes.
- `backend/tests/test_routes.py` (new) — happy path + 404 / empty cases.

**Acceptance:**
- `curl localhost:6002/projects` returns the project list.
- `curl localhost:6002/projects/foo/configs` returns that project's configs.
- Pytest suite green.

---

### Task 4 — Backend write endpoints + cache invalidation
**Goal:** `POST` and `PUT /config/{project}/{key}` with proper status codes and in-memory cache refresh.

**Files to modify/create:**
- `backend/app/database/repositories/config.py` — add `create(project, key, value)` (raises on duplicate) and `update(project, key, value)` (raises on missing).
- `backend/app/services/config_service.py` — add `create_config(...)` and `update_config(...)` that write to MySQL and call `sync_from_remote()` (or a targeted refresh) so the in-memory cache stays consistent.
- `backend/app/api/routes.py` — add `POST` (returns 201, 409 on duplicate via the model's unique constraint) and `PUT` (returns 200, 404 if missing).
- `backend/app/core/models.py` — add `ConfigCreateRequest` / `ConfigUpdateRequest` (just `{ value: str }`).
- `backend/tests/test_routes.py` — POST/PUT happy paths, 409 duplicate, 404 missing.

**Acceptance:**
- Creating a config shows up immediately on `GET /config/{project}/{key}` without `/refresh`.
- Updating an existing config shows the new value immediately.
- Duplicate POST returns 409; PUT on missing returns 404.

---

## Phase C — Browse + Read flows

### Task 5 — §6.1 Project Selection Page
**Goal:** Functional projects list with sort, refresh, and entry to detail/create flows.

**Files to create/modify:**
- `frontend/src/pages/ProjectsPage.tsx` — table with `Project name` (sortable, default ASC) and `Config count` columns; row click → `/projects/:project`; "+ New Config" → `/projects/new`.
- `frontend/src/components/EmptyState.tsx`, `frontend/src/components/ErrorBanner.tsx`, `frontend/src/components/SkeletonRow.tsx`.
- `frontend/src/components/TopBar.tsx` — extracted from Layout; shows live cache stats from `useHealth` hook (30s poll added in Task 10).

**Acceptance:**
- Projects table renders with real data from `GET /projects`.
- Clicking a row navigates to the project page.
- Clicking "+ New Config" navigates to `/projects/new` (stub).
- Empty / loading / error states render as specified in §6.1.

---

### Task 6 — §6.2 Project Config Page
**Goal:** Configs table with truncation, copy, edit buttons; row click → detail page.

**Files to create/modify:**
- `frontend/src/pages/ProjectConfigsPage.tsx` — table of configs, default sort `config_key ASC`, no search (§10 decision).
- `frontend/src/components/ConfigValuePreview.tsx` — implements §8 truncation rule (120 chars OR 3 lines → truncated, `<pre>` element, "Show full value →" hint when truncated, `<empty>` placeholder).
- `frontend/src/components/CopyButton.tsx` — clipboard copy with toast.

**Acceptance:**
- Configs table renders; long values are visually truncated.
- Click anywhere on a row navigates to `/projects/:project/:key`.
- Copy button copies the full value; toast confirms.
- Edit button navigates to `/projects/:project/:key/edit` (stub for now).

---

### Task 7 — §6.3 Config Detail Page
**Goal:** Read-only Monaco editor view.

**Files to create/modify:**
- `frontend/src/components/MonacoEditor.tsx` — lazy wrapper around `@monaco-editor/react` with shared props.
- `frontend/src/utils/detectLanguage.ts` — try JSON.parse → `"json"`; simple heuristic for YAML → `"yaml"`; else `"plaintext"`.
- `frontend/src/pages/ConfigDetailPage.tsx` — read-only Monaco, footer with line/column/char count + Copy, Edit button.

**Acceptance:**
- Detail page renders the value in Monaco.
- Syntax highlighting auto-detected (JSON / YAML / plain).
- Edit button navigates to edit page (stub).
- 404 from backend shows empty-state with "Back to project" link.

---

## Phase D — Edit + Create flows

### Task 8 — §6.4 Edit Page
**Goal:** Editable Monaco with save, spinner, dirty guard.

**Files to create/modify:**
- `frontend/src/pages/ConfigEditPage.tsx` — editable Monaco prefilled from `getConfig`; Save → `useUpdateConfig`; spinner + disabled Save while in-flight; Cancel → back to detail page (with dirty guard confirm).
- `frontend/src/hooks/useDirtyGuard.ts` — `beforeunload` listener + Next.js-style router guard.
- `frontend/src/components/EditorFooter.tsx` — Save / Cancel buttons + dirty-state indicator.

**Acceptance:**
- Editing the value and clicking Save persists and redirects to detail page.
- Save spinner shown during in-flight.
- Browser back, Cancel, and tab close all trigger the dirty guard.
- 4xx / 5xx surfaced inline; remains on page.

---

### Task 9 — §6.5 Create Config Page
**Goal:** Create flow with both entry modes (project prefilled+disabled, or combobox with free-text).

**Files to create/modify:**
- `frontend/src/pages/CreateConfigPage.tsx` — route `/projects/new` (editable project combobox) and `/projects/:project/new` (prefilled + disabled).
- `frontend/src/components/ProjectCombobox.tsx` — autocomplete over existing projects + free-text fallback; client-side regex validation `^[a-z0-9][a-z0-9-_]*$`.
- `frontend/src/components/KeyInput.tsx` — text input with regex `^[a-z0-9][a-z0-9-_.]*$`.

**Acceptance:**
- Both routes work; project field behavior matches entry mode.
- Validation errors render inline before submit.
- Successful POST navigates to `/projects/:project/:key`.
- 409 from backend renders inline error with link to edit page.

---

## Phase E — Polish

### Task 10 — Top-bar stats polling
**Goal:** 30s `GET /health` poll with staleness indicator.

**Files to modify:**
- `frontend/src/hooks/queries.ts` — `useHealth` with `refetchInterval: 30_000`.
- `frontend/src/components/TopBar.tsx` — staleness indicator (e.g., dimmed stats) when last successful fetch > 60s ago.

**Acceptance:**
- Stats update every 30s.
- Backend down → staleness indicator visible within ~60s.
- Refresh button in top bar calls `POST /refresh` and refetches stats.

---

### Task 11 — Responsive + a11y
**Goal:** 768px breakpoint, mobile `<textarea>` fallback for editor, keyboard/ARIA pass.

**Files to modify:**
- `frontend/src/components/ResponsiveTable.tsx` — table → stacked cards below 768px; used by §6.1 and §6.2.
- `frontend/src/components/MonacoEditor.tsx` — accepts `forceTextarea` prop; mobile detection (matchMedia `(max-width: 767px)`) auto-enables.
- All pages — ensure `<label>` associations, ARIA on icon buttons, focus rings, `<th scope="col">`.

**Acceptance:**
- Resize to <768px shows stacked cards on lists; editor goes full-bleed with `<textarea>` toggle visible.
- axe-core run reports 0 critical/serious violations.
- Keyboard-only navigation works end-to-end (Tab order, Enter on buttons, Escape closes modals/toasts).

---

### Task 12 — End-to-end smoke test
**Goal:** All 7 user stories from §4 verified end-to-end against running backend + frontend.

**Steps:**
1. `docker compose up -d --build` for both `backend/` and `frontend/`.
2. Walk through:
   - Story 1: `/` shows the projects list.
   - Story 2: `/projects/:project` shows that project's configs.
   - Story 3: Click truncated preview → Monaco detail view.
   - Story 4: Edit → modify → Save → detail reflects.
   - Story 5: From project page → + New Config → project prefilled+disabled.
   - Story 6: From `/` → + New Config → project combobox.
   - Story 7: Top-bar Refresh → `/refresh` called → stats updated.
3. Capture screenshots or notes; fix any defects.

**Acceptance:** All 7 stories pass; Definition of Done (§9) checklist green.

---

## Suggested Order

1 → 2 → 3 → 5 → 4 → 6 → 7 → 8 → 9 → 10 → 11 → 12

Tasks 3 and 4 can be done before or interleaved with frontend tasks — the frontend just won't have data until they land. Starting with **Task 1** is the only prerequisite for everything else.