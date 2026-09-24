# PRD: Config Store Admin UI

**Status:** Draft v2
**Owner:** TBD
**Last updated:** 2026-09-23

## 1. Overview

A web-based admin interface for the `config_store` service that allows operators to browse, inspect, and modify configuration values stored across multiple projects. The UI consumes the FastAPI backend in `backend/app/api/routes.py` and is built as a Vite + React SPA living under `frontend/`. In production, nginx serves the static bundle and reverse-proxies `/api/*` to the backend over a docker network — modeled on the sibling `../logging_system/frontend` setup.

## 2. Goals

- Provide a clear, navigable view of all projects and their configuration keys.
- Enable read-only inspection of config values with a code-editor view suitable for structured data (JSON, YAML, etc.).
- Allow authorized users to create and update configs.
- Surface the cache sync state (`/health`) so operators know how fresh the data is.

## 3. Non-Goals (v1)

- Authentication / RBAC (assumed to be handled by an upstream proxy; any user with network access can perform any action in v1).
- Writing to MongoDB directly from the UI (writes go through the backend, which then propagates via the existing sync pipeline).
- Version history / audit log of config changes.
- Bulk import / export.
- Concurrent-edit conflict resolution beyond **last-write-wins**.
- Delete operations (deferred to v1.1).
- Telemetry / error reporting integration.

## 4. User Stories

| # | As a… | I want to… | So that… |
|---|-------|------------|----------|
| 1 | Operator | See a list of projects that have configs | I can pick one to inspect |
| 2 | Operator | See all config keys in a project | I can find the value I need |
| 3 | Operator | Preview a long config value in a code editor | I can read JSON/YAML cleanly |
| 4 | Operator | Edit a config value and save | I can update settings without touching MongoDB |
| 5 | Operator | Create a new config in a known project | I can onboard a new key quickly |
| 6 | Operator | Create a new config from the project list | I can add to a brand-new project |
| 7 | Operator | Manually trigger a cache refresh | I can verify a recent change is reflected in another tab |

## 5. Information Architecture & Navigation

Four primary routes plus one shared layout. All app routes live under `/projects` for a single hierarchy:

```
/                                        → Projects list (Project Selection Page)
/projects/new                            → Create config (project field empty + editable)
/projects/[project]                      → Project configs list (Project Config Page)
/projects/[project]/new                  → Create config (project field prefilled + disabled)
/projects/[project]/[key]                → Config detail (read-only code editor view)
/projects/[project]/[key]/edit           → Edit config page
```

- A persistent top bar shows app name, current cache stats (`projects_loaded`, `cache_keys_total` from `GET /health`), a "Refresh cache" button, and a global "+ New Config" button.
- Breadcrumb navigation: `Projects / {project} / {key}`.

### Requirement → Section Mapping

| User Requirement | Section |
|------------------|---------|
| Req 1 — Projects selection page | §6.1 |
| Req 2 — Configs list per project | §6.2 |
| Req 3 — Truncation + click to open in code editor | §6.2, §6.3, §8 (truncation rule) |
| Req 4 — Edit button → separate edit page | §6.4 |
| Req 5 — Add new from either page, project prefilled+disabled on project page | §6.5 |

## 6. Page Designs

### 6.1 Project Selection Page (`/`)

**Purpose:** Entry point. Lets the user choose which project's configs to manage.

**Layout:**
- Header: title "Projects" + a primary "+ New Config" button (top right) linking to `/projects/new`.
- Body: table of project rows, sortable by `Project name` (default ASC) and `Config count`.

**Columns per row:**
| Field | Source | Notes |
|-------|--------|-------|
| Project name | distinct `project` from `GET /projects` | Clickable, links to `/projects/[project]` |
| Config count | count of keys per project | Badge, refreshed on mount and after writes |
| Last updated | *(out of scope v1 — see §3)* | Hidden; will surface when backend adds timestamps |

**Behaviors:**
- Click row → navigate to `/projects/[project]`.
- Click "+ New Config" → navigate to `/projects/new` (project field empty).
- Empty state: "No projects yet. Click 'New Config' to add the first one."
- Loading: skeleton rows (5 placeholders).
- Error: inline error banner with retry.

### 6.2 Project Config Page (`/projects/[project]`)

**Purpose:** List all configs belonging to one project.

**Layout:**
- Breadcrumb: `Projects / {project}`.
- Header: project name, config count, "+ New Config" button linking to `/projects/[project]/new`.
- Body: table of configs, default sort by `config_key ASC`. No search/filter in v1 (deferred to v1.1).

**Columns per row:**
| Field | Source | Behavior |
|-------|--------|----------|
| Key | `config_key` | Plain text, monospace |
| Value (preview) | `value` | Truncated per §8 truncation rule; row is a link to detail page |
| Actions | — | "Copy" button (copies full value to clipboard); "Edit" button → edit page |

**Empty state:** "No configs in this project yet. Click 'New Config' to add one."

### 6.3 Config Detail Page (`/projects/[project]/[key]`)

**Purpose:** Read a config value in a proper code editor.

**Layout:**
- Breadcrumb: `Projects / {project} / {key}`.
- Header: project + key, "Edit" button (top right) linking to the edit page.
- Body: read-only code editor pane filling available height.
- Footer: line/column count, character count, "Copy" button.

**Behaviors:**
- "Edit" is the **only** mutation path from this page.
- If the project/key pair 404s, show an empty-state with "Back to project" link.

### 6.4 Edit Page (`/projects/[project]/[key]/edit`)

**Purpose:** Modify a config value and persist it.

**Layout:**
- Breadcrumb: `Projects / {project} / {key} / Edit`.
- Header: project + key, "Cancel" + "Save" buttons.
- Body: editable code editor prefilled with current value. The UI is English-only — no language picker.

**Save behavior:**
- "Save" calls `PUT /config/{project}/{key}` with `{ "value": "..." }`.
- During save: Save button disables + shows spinner; Cancel stays enabled.
- On success: toast "Saved", redirect to the detail page.
- On 4xx: inline error under the editor; remain on page.
- On 5xx: toast with retry button.

**Dirty guard:**
- Triggered by: clicking a breadcrumb, the top-bar refresh, the Cancel button (with confirm), the browser back/forward buttons, or closing the tab.
- Implementation: `beforeunload` listener + Next.js router event guard.
- Confirmation dialog is focus-trapped and announces via `aria-live=polite`.

**Concurrency:** last-write-wins. No optimistic locking in v1 (per Non-Goals).

### 6.5 Create Config Page (`/projects/new` and `/projects/[project]/new`)

**Purpose:** Create a new config.

**Two entry modes:**
- **From project page** (`/projects/[project]/new`):
  - Project field is **prefilled and disabled** (read-only input).
- **From projects list** (`/projects/new`):
  - Project field is **empty and editable** — rendered as a combobox with autocomplete over existing project names plus free-text fallback for new projects.

**Form fields:**
| Field | Type | Required | Validation |
|-------|------|----------|------------|
| Project | text / combobox | yes | non-empty, ≤255 chars, regex `^[a-z0-9][a-z0-9-_]*$` |
| Key | text | yes | non-empty, ≤255 chars, regex `^[a-z0-9][a-z0-9-_.]*$` |
| Value | code editor | yes | non-empty |

**Submit:**
- `POST /config/{project}/{key}` with `{ "value": "..." }`.
- On 201: navigate to `/projects/[project]/[key]`.
- On 409 (duplicate key): inline error "A config with this key already exists. Use Edit instead." with a link to the edit page.

## 7. Backend API Surface (Frontend-facing)

### 7.1 Current endpoints (already exist)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/health` | Returns `{ status, stats: { projects_loaded, cache_keys_total } }`. Used for top-bar stats. |
| GET | `/config/{project}/{key}` | Returns `{ project, key, value }`. Used by detail + edit pages (edit prefills from this). |
| POST | `/refresh` | Triggers cache sync. Used by the "Refresh cache" button. |

### 7.2 New endpoints required

| Method | Path | Request body | Response | Notes |
|--------|------|--------------|----------|-------|
| GET | `/projects` | — | `[{ project, config_count }]` | Used by §6.1 |
| GET | `/projects/{project}/configs` | — | `[{ config_key, value }]` | Used by §6.2. No `?search=` query param in v1. |
| POST | `/config/{project}/{key}` | `{ value }` | `ConfigResponse` (201) | Returns 409 on duplicate key+project. |
| PUT | `/config/{project}/{key}` | `{ value }` | `ConfigResponse` (200) | Returns 404 if not found (does not upsert). |

### 7.3 Backend prerequisites

- All new write endpoints (POST, PUT) must invalidate or refresh the in-memory cache held by `ConfigService` so another browser tab sees the change without manual `/refresh`.
- The backend treats `value` as opaque text. No `language` column, no language-aware parsing.
- `GET /health` polling in the top bar refreshes every 30 seconds; on error, fall back to last known good values and show a subtle staleness indicator.

## 8. UI/UX Spec

**Framework:** Vite + React + TypeScript (SPA). Static assets are served by **nginx** in production, which also **reverse-proxies `/api/*` to the FastAPI backend** so the browser only talks to a single origin (no CORS).
**Component library:** Tailwind CSS for styling. Components are hand-rolled or sourced from Radix primitives — no opinionated UI kit dependency.
**Code editor:** Monaco Editor via `@monaco-editor/react`. Loaded **lazily via `React.lazy` + `Suspense`**, scoped to detail/edit/create routes only — never loaded on the projects list or project configs list.
**Data fetching:** TanStack Query (`@tanstack/react-query`) for caching, retries, and optimistic updates.
**Forms:** `react-hook-form` + `zod` for validation (shared schemas with backend regexes).
**Theming:** light/dark via a small CSS-variable theme toggle, follows OS preference.
**Toasts:** `sonner` for save/refresh confirmations.

### Build, Serve, and Proxy

Mirrors the layout used by the sibling `../logging_system/frontend` project.

- **Dev (`npm run dev`):** Vite dev server on `:5173`. `vite.config.ts` proxies `/api/*` to the backend (default `http://localhost:6002`, override via `VITE_DEV_API_TARGET`).
- **Prod (`docker compose up -d --build` from `frontend/`):** multi-stage Dockerfile builds the Vite bundle, then a minimal `nginx:1.27-alpine` image serves `dist/` and reverse-proxies `/api/*` to `http://config_store:6002/` over the external `config-store-net` docker network (the same network the backend compose attaches to).
- **Single origin:** the browser always talks to `http://localhost:3000` (nginx on the host). `/api/health`, `/api/config/...`, etc., are forwarded to the backend container, so no CORS headers are needed.
- **`VITE_API_URL` build arg:** default `/api` (relative — goes through the nginx proxy). Override to an absolute URL if the SPA is served from a different origin than the backend.

### Truncation rule (§6.2 preview)

- **Policy:** "Best-effort preview; the detail page is authoritative."
- **Threshold:** if `value` is longer than 120 characters **or** contains more than 3 lines, truncate.
- **Render:** `<pre>` element preserving newlines, `max-height: 3em`, `overflow: hidden`, `text-overflow: ellipsis`. This works for both single-line and multi-line (JSON/YAML) values.
- **Affordance:** when truncated, append a small "Show full value →" hint at the bottom-right of the preview cell.
- **Empty value:** render `<empty>` placeholder so the row remains visible.
- **Click target:** the entire preview cell is a link to the detail page.

### Accessibility

- All form fields have associated `<label>`s.
- The code editor provides a hidden `<textarea>` fallback for screen readers (Monaco's `ariaLabel` + read-only mode).
- Toast region has `aria-live=polite`.
- All icon-only buttons (Copy, Refresh) have `aria-label`.
- Visible focus ring on every interactive element.
- Tables use proper `<th scope="col">` markup.

### Responsive behavior

- Breakpoint: **768px**. Below it, the projects list (§6.1) and project configs list (§6.2) switch from tables to stacked cards (one card per row).
- On mobile, the editor (§6.3 / §6.4) goes full-bleed and offers a fallback `<textarea>` toggle if Monaco becomes unusable on narrow screens.

## 9. Definition of Done

The frontend is considered v1-complete when:

1. **Browse:** A user can navigate `/` → `/projects/[project]` and see all configs in that project with truncated previews.
2. **Read:** Clicking a truncated preview opens `/projects/[project]/[key]` with the full value in a read-only Monaco editor.
3. **Edit:** From the detail page, the user clicks Edit, modifies the value, and saves; the new value is reflected on the detail page.
4. **Create (from project):** From `/projects/[project]`, clicking "+ New Config" lands on `/projects/[project]/new` with the project field prefilled and disabled.
5. **Create (from list):** From `/`, clicking "+ New Config" lands on `/projects/new` with an editable project field.
6. **Refresh:** The top-bar "Refresh cache" button calls `POST /refresh` and updates the stats display.
7. **Error states:** All pages render meaningful empty / loading / error states.
8. **Accessibility & responsive:** Passes keyboard navigation, axe-core a11y checks, and the 768px responsive behavior described in §8.

## 10. Resolved Decisions

1. **Search/filter on §6.2:** **out of v1.** Defer to v1.1. No search input is rendered.
2. **UI language:** **English only.** No language picker on the edit page; no `language` field on the create form; no `language` column in the backend.
3. **Sortable columns on §6.1:** **name + config count only.** No "Last activity" / timestamp column in v1.
4. **Top-bar stats polling cadence:** **30s polling with a manual "Refresh cache" button.** (Adopted recommendation.)
5. **Mobile editor fallback:** **provide a `<textarea>` toggle** so the user can switch out of Monaco when narrow screens make it unusable.