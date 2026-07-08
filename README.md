# Config Store

A FastAPI-based configuration store that syncs configs from MongoDB to MySQL for fast, local access.

## Architecture

```
MongoDB (Remote) ──sync──> MySQL (Local Cache) ──read──> API
```

- **MongoDB**: Source of truth for all configs (remote)
- **MySQL**: Local cache for fast reads
- **FastAPI**: REST API for retrieving configs

## Features

- REST API for retrieving config values
- Automatic periodic sync from MongoDB to MySQL
- Manual cache refresh endpoint
- Health check endpoint with cache statistics

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check with cache stats |
| GET | `/config/{project}/{key}` | Get a config value |
| POST | `/refresh` | Manually trigger a cache sync |

## Quick Start

### Prerequisites

- Python 3.12+
- uv
- MongoDB instance
- MySQL instance

### Local Development

```bash
# Install dependencies
uv sync

# Run the server
uv run uvicorn main:app --reload
```

### Docker

```bash
# Start all services (config_store + MySQL)
docker compose up --build
```

## Configuration

Copy `.env.example` to `.env` and configure:

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

Configs in MongoDB should have this structure:

```json
{
  "project": "my-project",
  "key": "database_url",
  "value": "postgres://localhost:5432/mydb"
}
```

## Testing

```bash
# Install test dependencies
uv pip install -e ".[test]"

# Run tests
uv run pytest tests/ -v
```

## License

MIT
