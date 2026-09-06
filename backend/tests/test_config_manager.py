"""Test ConfigService."""
import pytest
from unittest.mock import patch

from app.core.models import CacheStats
from app.services.config_service import ConfigService


class TestConfigService:
    """Tests for ConfigService."""

    @pytest.fixture
    def config_service(self, mock_mongo_client, mock_config_repository):
        """Create a ConfigService with mocked dependencies."""
        with patch("app.services.config_service.MongoClient", return_value=mock_mongo_client):
            with patch(
                "app.services.config_service.ConfigRepository",
                return_value=mock_config_repository,
            ):
                service = ConfigService()
                yield service

    @pytest.mark.asyncio
    async def test_sync_from_remote_with_empty_mongo(
        self, config_service, mock_mongo_client, mock_config_repository
    ):
        """Test sync with no configs in MongoDB."""
        mock_mongo_client.fetch_all_configs.return_value = []

        await config_service.sync_from_remote()

        mock_mongo_client.fetch_all_configs.assert_called_once()
        mock_config_repository.upsert.assert_not_called()
        mock_config_repository.delete_stale.assert_called_once_with([])

    @pytest.mark.asyncio
    async def test_sync_from_remote_with_configs(
        self,
        config_service,
        mock_mongo_client,
        mock_config_repository,
        sample_mongo_configs,
    ):
        """Test sync with configs in MongoDB."""
        mock_mongo_client.fetch_all_configs.return_value = sample_mongo_configs

        await config_service.sync_from_remote()

        mock_mongo_client.fetch_all_configs.assert_called_once()
        mock_config_repository.upsert.assert_called_once()
        upsert_arg = mock_config_repository.upsert.call_args[0][0]
        assert len(upsert_arg) == 3
        mock_config_repository.delete_stale.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_handles_duplicate_project_key_pairs(
        self, config_service, mock_mongo_client, mock_config_repository
    ):
        """Test that duplicate (project, key) pairs are deduplicated."""
        mock_mongo_client.fetch_all_configs.return_value = [
            {"project": "proj", "key": "key1", "value": "val1"},
            {"project": "proj", "key": "key1", "value": "val2"},
            {"project": "proj", "key": "key1", "value": "val3"},
        ]

        await config_service.sync_from_remote()

        upsert_arg = mock_config_repository.upsert.call_args[0][0]
        assert len(upsert_arg) == 1
        assert upsert_arg[0] == ("proj", "key1", "val1")  # First value is kept

    @pytest.mark.asyncio
    async def test_get_config_returns_value(
        self, config_service, mock_config_repository
    ):
        """Test get_config returns value from MySQL."""
        mock_config_repository.get_value.return_value = "test-value"

        result = await config_service.get_config("my-project", "api_key")

        mock_config_repository.get_value.assert_called_once_with("my-project", "api_key")
        assert result == "test-value"

    @pytest.mark.asyncio
    async def test_get_config_returns_none_when_not_found(
        self, config_service, mock_config_repository
    ):
        """Test get_config returns None when config not found."""
        mock_config_repository.get_value.return_value = None

        result = await config_service.get_config("nonexistent", "key")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stats_returns_cache_stats(
        self, config_service, mock_config_repository
    ):
        """Test get_stats returns CacheStats."""
        mock_config_repository.stats.return_value = {
            "projects_loaded": 5,
            "cache_keys_total": 100,
        }

        result = await config_service.get_stats()

        mock_config_repository.stats.assert_called_once()
        assert isinstance(result, CacheStats)
        assert result.projects_loaded == 5
        assert result.cache_keys_total == 100

    @pytest.mark.asyncio
    async def test_close_calls_mongo_client(
        self, config_service, mock_mongo_client
    ):
        """Test close() closes the MongoDB connection."""
        await config_service.close()

        mock_mongo_client.close.assert_called_once()