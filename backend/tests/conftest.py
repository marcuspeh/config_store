"""Pytest configuration and fixtures."""
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent))


# Pre-create mock classes
class MockMongoClient:
    def __init__(self, *args, **kwargs):
        pass

    async def fetch_all_configs(self):
        return []

    async def close(self):
        pass


class MockConfigRepository:
    def __init__(self, *args, **kwargs):
        pass

    async def upsert(self, configs):
        pass

    async def delete_stale(self, keys):
        pass

    async def get_value(self, project, key):
        return None

    async def stats(self):
        return {"projects_loaded": 0, "cache_keys_total": 0}


# Stub the new client + repository modules so tests can construct
# ConfigService without instantiating real Mongo / Tortoise.
mock_clients_module = MagicMock()
mock_clients_module.MongoClient = MockMongoClient

mock_repositories_module = MagicMock()
mock_repositories_module.ConfigRepository = MockConfigRepository

mock_db_module = MagicMock()
mock_db_module.models = MagicMock()

# Legacy module paths (kept for any stragglers).
sys.modules['db'] = mock_db_module
sys.modules['db.models'] = mock_db_module.models
sys.modules['db.mongodb_manager'] = mock_db_module
sys.modules['db.mysql_manager'] = mock_db_module

# Current module paths used by app.services.config_service.
# NOTE: We stub the *attributes* of app.clients and app.database.repositories
# but leave the parent packages themselves untouched so the real
# app.database.session module can still be imported.
import app.clients as _app_clients  # noqa: E402
import app.clients.mongo as _app_clients_mongo  # noqa: E402
import app.database.repositories as _app_repos  # noqa: E402

_app_clients.MongoClient = MockMongoClient  # type: ignore[attr-defined]
_app_clients_mongo.MongoClient = MockMongoClient  # type: ignore[attr-defined]
_app_repos.ConfigRepository = MockConfigRepository  # type: ignore[attr-defined]


@pytest.fixture
def event_loop():
    """Create an event loop for the test session."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_mongo_client():
    """Mock MongoClient."""
    mock = AsyncMock()
    mock.fetch_all_configs = AsyncMock(return_value=[])
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_config_repository():
    """Mock ConfigRepository."""
    mock = AsyncMock()
    mock.upsert = AsyncMock()
    mock.delete_stale = AsyncMock()
    mock.get_value = AsyncMock(return_value=None)
    mock.stats = AsyncMock(return_value={"projects_loaded": 0, "cache_keys_total": 0})
    return mock


@pytest.fixture
def sample_mongo_configs():
    """Sample MongoDB config documents."""
    return [
        {"project": "project-a", "key": "database_url", "value": "postgres://localhost/db"},
        {"project": "project-a", "key": "api_key", "value": "secret-key-123"},
        {"project": "project-b", "key": "feature_flags", "value": '{"dark_mode": true}'},
    ]


@pytest.fixture
def sample_config_tuples():
    """Sample config data as list of tuples."""
    return [
        ("project-a", "database_url", "postgres://localhost/db"),
        ("project-a", "api_key", "secret-key-123"),
        ("project-b", "feature_flags", '{"dark_mode": true}'),
    ]