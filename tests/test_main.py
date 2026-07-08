"""Test FastAPI endpoints."""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from main import app
from models import CacheStats


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self):
        """Test /health returns healthy status."""
        mock_stats = CacheStats(projects_loaded=5, cache_keys_total=100)

        with patch("main.config_manager") as mock_manager:
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

        with patch("main.config_manager") as mock_manager:
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
        with patch("main.config_manager") as mock_manager:
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
        with patch("main.config_manager") as mock_manager:
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
        with patch("main.config_manager") as mock_manager:
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

        with patch("main.config_manager") as mock_manager:
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

        with patch("main.config_manager") as mock_manager:
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

        with patch("main.config_manager") as mock_manager:
            mock_manager.sync_from_remote = AsyncMock()
            mock_manager.get_stats = AsyncMock(return_value=mock_stats_after)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/refresh")

        assert response.json()["stats"]["projects_loaded"] == 5
        assert response.json()["stats"]["cache_keys_total"] == 20
