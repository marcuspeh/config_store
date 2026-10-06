"""Pytest configuration and fixtures."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

import app.clients as _app_clients
import app.clients.mongo as _app_clients_mongo
import app.database.repositories as _app_repos

sys.path.insert(0, str(Path(__file__).parent.parent))


class MockMongoClient:
    def __init__(self, *args, **kwargs):
        pass

    async def fetch_all_configs(self):
        return []

    async def upsert_config(self, project, key, value):
        pass

    async def delete_config(self, project, key):
        pass

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

    async def distinct_projects(self):
        return []

    async def list_for_project(self, project):
        return []

    async def create(self, project, key, value):
        pass

    async def update(self, project, key, value):
        pass

    async def delete(self, project, key):
        return False


# Patch the client + repository classes so ConfigService can be built without
# real Mongo / Tortoise instances.
_app_clients.MongoClient = MockMongoClient  # type: ignore[attr-defined]
_app_clients_mongo.MongoClient = MockMongoClient  # type: ignore[attr-defined]
_app_repos.ConfigRepository = MockConfigRepository  # type: ignore[attr-defined]


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_mongo_client():
    mock = AsyncMock()
    mock.fetch_all_configs = AsyncMock(return_value=[])
    mock.upsert_config = AsyncMock()
    mock.delete_config = AsyncMock()
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_config_repository():
    mock = AsyncMock()
    mock.upsert = AsyncMock()
    mock.delete_stale = AsyncMock()
    mock.get_value = AsyncMock(return_value=None)
    mock.stats = AsyncMock(return_value={"projects_loaded": 0, "cache_keys_total": 0})
    mock.distinct_projects = AsyncMock(return_value=[])
    mock.list_for_project = AsyncMock(return_value=[])
    mock.create = AsyncMock()
    mock.update = AsyncMock()
    mock.delete = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def sample_mongo_configs():
    return [
        {"project": "project-a", "key": "database_url", "value": "postgres://localhost/db"},
        {"project": "project-a", "key": "api_key", "value": "secret-key-123"},
        {"project": "project-b", "key": "feature_flags", "value": '{"dark_mode": true}'},
    ]


@pytest.fixture
def sample_config_tuples():
    return [
        ("project-a", "database_url", "postgres://localhost/db"),
        ("project-a", "api_key", "secret-key-123"),
        ("project-b", "feature_flags", '{"dark_mode": true}'),
    ]
