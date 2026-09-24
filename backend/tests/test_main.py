"""Test FastAPI endpoints."""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.models import CacheStats
from app.database.repositories.config import (
    ConfigAlreadyExists,
    ConfigNotFound,
)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self):
        """Test /health returns healthy status."""
        mock_stats = CacheStats(projects_loaded=5, cache_keys_total=100)

        with patch("app.main.config_service") as mock_manager:
            mock_manager.get_stats = AsyncMock(return_value=mock_stats)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["stats"]["projects_loaded"] == 5
        assert data["stats"]["cache_keys_total"] == 100

    @pytest.mark.asyncio
    async def test_health_with_empty_cache(self):
        """Test /health with empty cache."""
        mock_stats = CacheStats(projects_loaded=0, cache_keys_total=0)

        with patch("app.main.config_service") as mock_manager:
            mock_manager.get_stats = AsyncMock(return_value=mock_stats)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["stats"]["projects_loaded"] == 0
        assert data["stats"]["cache_keys_total"] == 0


class TestConfigEndpoint:
    """Tests for /config/{project}/{key} endpoint."""

    @pytest.mark.asyncio
    async def test_get_config_success(self):
        """Test successful config retrieval."""
        with patch("app.main.config_service") as mock_manager:
            mock_manager.get_config = AsyncMock(return_value="postgres://localhost/db")

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/config/my-project/database_url")

        assert response.status_code == 200
        data = response.json()
        assert data["project"] == "my-project"
        assert data["key"] == "database_url"
        assert data["value"] == "postgres://localhost/db"

    @pytest.mark.asyncio
    async def test_get_config_not_found(self):
        """Test 404 when config does not exist."""
        with patch("app.main.config_service") as mock_manager:
            mock_manager.get_config = AsyncMock(return_value=None)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/config/nonexistent/config")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_config_special_characters_in_key(self):
        """Test config retrieval with special characters."""
        with patch("app.main.config_service") as mock_manager:
            mock_manager.get_config = AsyncMock(return_value='{"key": "value"}')

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/config/project/feature_flags")

        assert response.status_code == 200
        assert response.json()["value"] == '{"key": "value"}'


class TestRefreshEndpoint:
    """Tests for /refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_success(self):
        """Test successful cache refresh."""
        mock_stats = CacheStats(projects_loaded=10, cache_keys_total=50)

        with patch("app.main.config_service") as mock_manager:
            mock_manager.sync_from_remote = AsyncMock()
            mock_manager.get_stats = AsyncMock(return_value=mock_stats)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/refresh")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "refreshed"
        assert data["stats"]["projects_loaded"] == 10

    @pytest.mark.asyncio
    async def test_refresh_calls_sync(self):
        """Test that /refresh calls sync_from_remote."""
        mock_stats = CacheStats(projects_loaded=0, cache_keys_total=0)

        with patch("app.main.config_service") as mock_manager:
            mock_manager.sync_from_remote = AsyncMock()
            mock_manager.get_stats = AsyncMock(return_value=mock_stats)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.post("/refresh")

            mock_manager.sync_from_remote.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_returns_stats_after_sync(self):
        """Test that /refresh returns updated stats."""
        mock_stats_after = CacheStats(projects_loaded=5, cache_keys_total=20)

        with patch("app.main.config_service") as mock_manager:
            mock_manager.sync_from_remote = AsyncMock()
            mock_manager.get_stats = AsyncMock(return_value=mock_stats_after)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/refresh")

        assert response.json()["stats"]["projects_loaded"] == 5
        assert response.json()["stats"]["cache_keys_total"] == 20


class TestProjectsListEndpoint:
    """Tests for GET /projects."""

    @pytest.mark.asyncio
    async def test_list_projects_returns_sorted_rows(self):
        """Projects are returned sorted by name ASC with config counts."""
        with patch("app.main.config_service") as mock_manager:
            mock_manager.list_projects = AsyncMock(
                return_value=[("project-a", 2), ("project-b", 1)]
            )

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/projects")

        assert response.status_code == 200
        data = response.json()
        assert data == [
            {"project": "project-a", "config_count": 2},
            {"project": "project-b", "config_count": 1},
        ]

    @pytest.mark.asyncio
    async def test_list_projects_empty(self):
        """Empty cache returns [] not 404."""
        with patch("app.main.config_service") as mock_manager:
            mock_manager.list_projects = AsyncMock(return_value=[])

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/projects")

        assert response.status_code == 200
        assert response.json() == []


class TestProjectConfigsEndpoint:
    """Tests for GET /projects/{project}/configs."""

    @pytest.mark.asyncio
    async def test_list_project_configs_returns_sorted_rows(self):
        """Configs are returned sorted by config_key ASC."""
        with patch("app.main.config_service") as mock_manager:
            mock_manager.list_configs = AsyncMock(
                return_value=[
                    ("api_key", "secret-key-123"),
                    ("database_url", "postgres://localhost/db"),
                ]
            )

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/projects/project-a/configs")

        assert response.status_code == 200
        data = response.json()
        assert data == [
            {"config_key": "api_key", "value": "secret-key-123"},
            {"config_key": "database_url", "value": "postgres://localhost/db"},
        ]

    @pytest.mark.asyncio
    async def test_list_project_configs_unknown_project_returns_empty(self):
        """Unknown project returns [] not 404 (frontend renders empty state)."""
        with patch("app.main.config_service") as mock_manager:
            mock_manager.list_configs = AsyncMock(return_value=[])

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/projects/nonexistent/configs")

        assert response.status_code == 200
        assert response.json() == []


class TestCreateConfigEndpoint:
    """Tests for POST /config/{project}/{key}."""

    @pytest.mark.asyncio
    async def test_create_success_returns_201(self):
        """Successful create returns 201 with the new ConfigResponse."""
        with patch("app.main.config_service") as mock_manager:
            mock_manager.create_config = AsyncMock()

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/config/my-project/new_key",
                    json={"value": "hello"},
                )

        assert response.status_code == 201
        body = response.json()
        assert body == {
            "project": "my-project",
            "key": "new_key",
            "value": "hello",
        }
        mock_manager.create_config.assert_awaited_once_with(
            "my-project", "new_key", "hello"
        )

    @pytest.mark.asyncio
    async def test_create_duplicate_returns_409(self):
        """Duplicate (project, key) returns 409 Conflict."""
        with patch("app.main.config_service") as mock_manager:
            mock_manager.create_config = AsyncMock(
                side_effect=ConfigAlreadyExists("dup")
            )

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/config/my-project/existing_key",
                    json={"value": "x"},
                )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_missing_value_returns_422(self):
        """Empty body (no `value` field) is rejected by Pydantic with 422."""
        with patch("app.main.config_service") as mock_manager:
            mock_manager.create_config = AsyncMock()

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/config/my-project/k",
                    json={},
                )

        assert response.status_code == 422
        mock_manager.create_config.assert_not_called()


class TestUpdateConfigEndpoint:
    """Tests for PUT /config/{project}/{key}."""

    @pytest.mark.asyncio
    async def test_update_success_returns_200(self):
        """Successful update returns 200 with the new ConfigResponse."""
        with patch("app.main.config_service") as mock_manager:
            mock_manager.update_config = AsyncMock()

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.put(
                    "/config/my-project/db_url",
                    json={"value": "postgres://new-host/db"},
                )

        assert response.status_code == 200
        body = response.json()
        assert body == {
            "project": "my-project",
            "key": "db_url",
            "value": "postgres://new-host/db",
        }
        mock_manager.update_config.assert_awaited_once_with(
            "my-project", "db_url", "postgres://new-host/db"
        )

    @pytest.mark.asyncio
    async def test_update_missing_returns_404(self):
        """Updating a non-existent config returns 404 (no upsert)."""
        with patch("app.main.config_service") as mock_manager:
            mock_manager.update_config = AsyncMock(
                side_effect=ConfigNotFound("missing")
            )

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.put(
                    "/config/my-project/missing_key",
                    json={"value": "x"},
                )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()