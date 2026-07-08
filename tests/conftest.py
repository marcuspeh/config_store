"""Pytest configuration and fixtures."""
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent))


# Pre-create mock classes
class MockMongoDBManager:
    def __init__(self, *args, **kwargs):
        pass

    async def fetch_all_configs(self):
        return []

    async def close(self):
        pass


class MockMySQLManager:
    def __init__(self, *args, **kwargs):
        pass

    async def init_db(self):
        pass

    async def upsert_configs(self, configs):
        pass

    async def delete_stale_configs(self, keys):
        pass

    async def get_config(self, project, key):
        return None

    async def get_stats(self):
        return {"projects_loaded": 0, "cache_keys_total": 0}

    async def close(self):
        pass


# Create and install the mock db module BEFORE any other imports
mock_db_module = MagicMock()
mock_db_module.MongoDBManager = MockMongoDBManager
mock_db_module.MySQLManager = MockMySQLManager
mock_db_module.models = MagicMock()

# Pre-load mock db modules to prevent broken Tortoise model from loading
sys.modules['db'] = mock_db_module
sys.modules['db.models'] = mock_db_module.models
sys.modules['db.mongodb_manager'] = mock_db_module
sys.modules['db.mysql_manager'] = mock_db_module


@pytest.fixture
def event_loop():
    """Create an event loop for the test session."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_mongo_manager():
    """Mock MongoDB manager."""
    mock = AsyncMock()
    mock.fetch_all_configs = AsyncMock(return_value=[])
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_mysql_manager():
    """Mock MySQL manager."""
    mock = AsyncMock()
    mock.init_db = AsyncMock()
    mock.upsert_configs = AsyncMock()
    mock.delete_stale_configs = AsyncMock()
    mock.get_config = AsyncMock(return_value=None)
    mock.get_stats = AsyncMock(return_value={"projects_loaded": 0, "cache_keys_total": 0})
    mock.close = AsyncMock()
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
