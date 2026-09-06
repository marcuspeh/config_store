# Config Store

A FastAPI-based configuration store that syncs configs from MongoDB to MySQL for fast, local access, with a web admin UI and SDKs for consumers.

## Architecture

```
MongoDB (Remote) ──sync──> MySQL (Local Cache) ──read──> API ──< Web UI
                                                          └─< SDKs (Python, Go)
```

- **MongoDB**: Source of truth for all configs (remote)
- **MySQL**: Local cache for fast reads
- **FastAPI** (`backend/`): REST API for retrieving and managing configs
- **Next.js** (`frontend/`, planned): Web admin UI
- **SDKs** (`sdk/`): Client libraries for consumers

## Repo Layout

```
config_store/
├── backend/        # FastAPI service (its own Dockerfile + docker-compose.yml)
├── frontend/       # Next.js admin UI (placeholder)
├── sdk/            # Python + Go client SDKs
├── docs/           # Architecture & API docs
├── Makefile        # Convenience commands
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check with cache stats |
| GET | `/config/{project}/{key}` | Get a config value |
| POST | `/refresh` | Manually trigger a cache sync |

## Quick Start

### Backend

```bash
cd backend
cp .env.example .env       # then edit
docker compose up --build  # starts backend on :6002
```

Or without Docker:

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

### Frontend (planned)

```bash
cd frontend
pnpm install
pnpm dev                   # serves on :3000, points at backend
```

### SDKs

See [`sdk/python/README.md`](sdk/python/README.md) and [`sdk/go/README.md`](sdk/go/README.md).

## Configuration

Copy `backend/.env.example` to `backend/.env` and configure:

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URI` | MongoDB connection string | - |
| `MONGO_DB` | MongoDB database name | `config_store` |
| `MONGO_COLLECTION` | MongoDB collection name | `configs` |
| `MYSQL_HOST` | MySQL host | `mysql` |
| `MYSQL_PORT` | MySQL port | `3306` |
| `MYSQL_USER` | MySQL user | `config_store` |
| `MYSQL_PASSWORD` | MySQL password | `config_store_password` |
| `MYSQL_DATABASE` | MySQL database name | `config_store` |
| `SYNC_INTERVAL` | Sync interval in seconds | `60` |

## MongoDB Config Format

```json
{
  "project": "my-project",
  "key": "database_url",
  "value": "postgres://localhost:5432/mydb"
}
```

## Testing

```bash
make test                   # runs backend pytest suite
```

## Linting

```bash
make lint                   # runs ruff against backend/
```

## License

MIT
