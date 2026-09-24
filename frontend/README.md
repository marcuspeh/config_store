# Frontend (config_store admin UI)

Web admin for managing config_store entries. Built as a Vite + React SPA.
In production the static bundle is served by **nginx**, which also
**reverse-proxies `/api/*` to the FastAPI backend** so the browser only
talks to a single origin (no CORS).

The setup mirrors the sibling `../logging_system/frontend` project.

## Dev

```bash
npm install
npm run dev
```

Vite serves the SPA on `:5173` and proxies `/api/*` to the backend on
`http://localhost:6002` (override with `VITE_DEV_API_TARGET`).

`.env.development` defaults `VITE_API_URL=/api`. Copy `.env.example` to
`.env.local` to override per-developer.

## Build

Multi-stage Dockerfile (`Dockerfile`) builds the Vite bundle, then ships
it in a minimal `nginx:1.27-alpine` image with `nginx.conf` that proxies
`/api/*` to `http://config_store:6002/` over the external
`config-store-net` docker network.

```bash
docker compose up -d --build   # serves on :3000
```

The container expects the backend to be reachable as `config_store:6002`
on the same docker network (see `backend/docker-compose.yml`).

## Project Layout

```
src/
├── api/          axios client + typed endpoints + shared types
├── components/   Layout, TopBar, PageStub, ...
├── pages/        One file per PRD page (projects, project configs, detail, edit, create)
├── styles/       Tailwind entry
├── App.tsx       Router
└── main.tsx      QueryClientProvider + Sonner Toaster + mount
```

See `PRD.md` for the product spec and `TASKS.md` for the implementation
plan.
