# Multi-stage build: Vite -> nginx static host + reverse proxy.
#
# Build-time args:
#   VITE_API_URL  Base URL the browser hits for API requests. The default
#                 ("/api") is a relative path that nginx proxies to the
#                 backend over the docker network (or host via
#                 `host.docker.internal` — see docker-compose.yml).
#
# Runtime:
#   - nginx serves the built SPA on container port 80.
#   - /api/* is reverse-proxied to ${BACKEND_UPSTREAM} (envsubst'd into
#     nginx.conf at container start) so the browser only ever talks to
#     a single origin and no CORS configuration is needed.
#
# Default runtime env (set in docker-compose.yml):
#   BACKEND_UPSTREAM=http://config_store:6002/
# Override at `docker run` time with `-e BACKEND_UPSTREAM=...` to point
# at a backend running on the host (e.g.
# `http://host.docker.internal:6002/`).

ARG VITE_API_URL=/api

FROM node:20-alpine AS build
WORKDIR /app

ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}

COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund

COPY tsconfig.json vite.config.ts tailwind.config.ts postcss.config.js index.html ./
COPY src ./src

RUN npm run build

FROM nginx:1.27-alpine

# Substitute ${BACKEND_UPSTREAM} in nginx.conf at container start.
# The default.conf in /etc/nginx/conf.d/ uses `${BACKEND_UPSTREAM}`
# literally; we sed-substitute to a temp file then move it into place
# in the entrypoint so it picks up whatever env var is set at run time.

# Install envsubst (provided by gettext) and curl (for healthcheck).
RUN apk add --no-cache gettext curl

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Defaults baked into the runtime image. Override via `-e BACKEND_UPSTREAM=...`.
ENV BACKEND_UPSTREAM=http://config_store:6002/

# Healthcheck hits /healthz on the SPA (we don't have one, but /
# returning 200 is enough). Use the index.html fallback.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://127.0.0.1/ || exit 1

EXPOSE 80
CMD ["sh", "-c", "envsubst '$$BACKEND_UPSTREAM' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
