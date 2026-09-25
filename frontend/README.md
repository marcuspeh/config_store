# Frontend (config_store admin UI)

Web admin for managing `config_store` entries. Browse, inspect, edit,
and create configs across multiple projects. Built as a Vite + React
SPA. In production the static bundle is served by **nginx**, which
also **reverse-proxies `/api/*` to the FastAPI backend** so the
browser only talks to a single origin (no CORS).

The setup mirrors the sibling `../logging_system/frontend` project.

## Stack

- **React 18** + **TypeScript** + **Vite 5**.
- **Tailwind CSS 3** for styling (hand-rolled components; no opinionated UI kit).
- **TanStack Query 5** for data fetching, caching, and invalidation.
- **React Router 6** for the SPA router.
- **@monaco-editor/react** for the read/edit value editor (lazy-loaded).
- **sonner** for toasts.
- **lucide-react** for icons.
- **zod** + **react-hook-form** available for forms (validation is currently inline).
- **axios** for the HTTP client.

## Dev (backend running directly on host)

The backend binds to `CONFIG_STORE_PORT` (default `6002`, see
`backend/app/main.py`). When you run the backend directly — e.g.
`cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 6002` —
the frontend dev server connects to it automatically.

```bash
cd frontend
npm install
npm run dev            # serves on :5173
```

Vite's dev proxy forwards `/api/*` to `http://localhost:6002`. Override
with `VITE_DEV_API_TARGET` if your backend is on a different host/port.

`.env.development` defaults `VITE_API_URL=/api`. Copy `.env.example` to
`.env.local` to override per-developer.

## Build (frontend as a docker container)

Multi-stage `Dockerfile` builds the Vite bundle, then ships it in a
minimal `nginx:1.27-alpine` image. `nginx.conf` reverse-proxies `/api/*`
to a backend address supplied at container start via the
`BACKEND_UPSTREAM` env var (default `http://config_store:6002/`,
substituted by `envsubst`).

**Option A — full stack in docker** (backend also running in a
container with hostname `config_store` on the shared `config-store-net`
network):

```bash
docker compose up -d --build   # serves on :3000
```

**Option B — backend running directly on the host.** The in-container
nginx needs a way to reach the host-side uvicorn; `host.docker.internal`
resolves to the host from inside any container.

```bash
BACKEND_UPSTREAM=http://host.docker.internal:6002/ \
  docker compose up -d --build
```

`host.docker.internal` works out of the box on Docker Desktop and on
Linux hosts started with `--add-host=host.docker.internal:host-gateway`.

The container always exposes port `3000` on the host (mapped to
container port `80`).

## Project Layout

```
src/
├── api/          axios client + typed endpoints + shared types
│   ├── client.ts     baseURL resolution (VITE_API_URL), error helper
│   ├── configs.ts    typed wrappers for every backend endpoint
│   └── types.ts      ProjectSummary, ConfigListItem, ConfigResponse, ...
├── components/   shared UI building blocks
│   ├── Layout.tsx              top bar + skip-link + main outlet
│   ├── TopBar.tsx              logo, cache stats, Refresh, New Config
│   ├── Breadcrumb.tsx          shared header used by detail/edit/create
│   ├── MonacoEditor.tsx        lazy Monaco with mobile <textarea> fallback
│   ├── ConfigValuePreview.tsx  truncated <pre> render for §6.2 rows
│   ├── CopyButton.tsx          clipboard copy with success state
│   ├── SortableHeader.tsx      table header with asc/desc/none cycle
│   ├── EmptyState.tsx          centred empty placeholder
│   ├── ErrorBanner.tsx         red error with optional retry
│   ├── SkeletonRow.tsx         animated grey bar for loading lists
│   └── ResponsiveTable.tsx     CSS-driven table↔cards switch at 768px
├── hooks/
│   ├── queries.ts              useProjects / useConfig / useHealth / ...
│   ├── mutations.ts            useCreateConfig / useUpdateConfig / useRefreshCache
│   ├── queryKeys.ts            cache-key factory
│   ├── useDirtyGuard.ts        in-app + tab-close guard
│   ├── useHealthStatus.ts      wraps useHealth with staleness detection
│   └── useMediaQuery.ts        SSR-safe matchMedia subscription
├── pages/        one file per PRD page
│   ├── ProjectsPage.tsx        /                          (§6.1)
│   ├── ProjectConfigsPage.tsx  /projects/:project         (§6.2)
│   ├── ConfigDetailPage.tsx    /projects/:project/:key    (§6.3)
│   ├── ConfigEditPage.tsx      /projects/:project/:key/edit (§6.4)
│   └── CreateConfigPage.tsx    /projects/new, /projects/:project/new (§6.5)
├── utils/
│   ├── detectLanguage.ts       "json" | "yaml" | "plaintext" hint for Monaco
│   ├── truncate.ts             §6.2 truncation rule (120 chars OR 3 lines)
│   └── validation.ts           project/key regex + length checks
├── App.tsx       router
└── main.tsx      QueryClientProvider + Sonner Toaster + mount
```

## Routes

| Path | Page | Notes |
|------|------|-------|
| `/` | ProjectsPage | Project list with config counts, sortable. |
| `/projects/new` | CreateConfigPage | Project field editable + autocomplete. |
| `/projects/:project` | ProjectConfigsPage | Configs table with truncated previews + Copy + Edit. |
| `/projects/:project/new` | CreateConfigPage | Project field prefilled and disabled. |
| `/projects/:project/:key` | ConfigDetailPage | Read-only Monaco with language auto-detect. |
| `/projects/:project/:key/edit` | ConfigEditPage | Editable Monaco + Save + dirty guard. |

## Conventions

- **Language:** English only; no i18n.
- **Search/filter:** none on the configs list in v1.
- **Concurrency:** last-write-wins. No optimistic locking.
- **Timestamps:** the backend has no `created_at` / `updated_at` columns, so the UI doesn't show "last activity" or similar metadata.
- **Delete:** out of v1 (use the backend repo / MongoDB directly).
- **Auth:** out of v1 (handled by upstream proxy).

## Backend

The frontend expects these endpoints (defined in
`backend/app/api/routes.py`):

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Cache stats for the top bar. |
| GET | `/projects` | List distinct projects with config counts. |
| GET | `/projects/{project}/configs` | List every config in a project. |
| GET | `/config/{project}/{key}` | Read one config. |
| POST | `/config/{project}/{key}` | Create (409 on duplicate). |
| PUT | `/config/{project}/{key}` | Update (404 if missing). |
| POST | `/refresh` | Manually trigger Mongo → MySQL sync. |

All writes propagate to MongoDB first (the source of truth), then to
MySQL. Subsequent reads see the new value immediately without manual
refresh because every read goes through the MySQL repo.
