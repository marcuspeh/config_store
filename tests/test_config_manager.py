"""Test ConfigManager."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from config_manager import ConfigManager
from models import CacheStats


class TestConfigManager:
    """Tests for ConfigManager class."""

    @pytest.fixture
    def config_manager(self, mock_mongo_manager, mock_mysql_manager):
        """Create a ConfigManager with mocked dependencies."""
        with patch("config_manager.MongoDBManager", return_value=mock_mongo_manager):
            with patch("config_manager.MySQLManager", return_value=mock_mysql_manager):
                manager = ConfigManager()
                yield manager

    @pytest.mark.asyncio
    async def test_init_calls_mysql_init_db(self, config_manager, mock_mysql_manager):
        """Test that init() calls MySQL init_db."""
        await config_manager.init()
        mock_mysql_manager.init_db.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_from_remote_with_empty_mongo(
        self, config_manager, mock_mongo_manager, mock_mysql_manager
    ):
        """Test sync with no configs in MongoDB."""
        mock_mongo_manager.fetch_all_configs.return_value = []

        await config_manager.sync_from_remote()

        mock_mongo_manager.fetch_all_configs.assert_called_once()
        mock_mysql_manager.upsert_configs.assert_not_called()
        mock_mysql_manager.delete_stale_configs.assert_called_once_with([])

    @pytest.mark.asyncio
    async def test_sync_from_remote_with_configs(
        self, config_manager, mock_mongo_manager, mock_mysql_manager, sample_mongo_configs
    ):
        """Test sync with configs in MongoDB."""
        mock_mongo_manager.fetch_all_configs.return_value = sample_mongo_configs

        await config_manager.sync_from_remote()

        mock_mongo_manager.fetch_all_configs.assert_called_once()
        mock_mysql_manager.upsert_configs.assert_called_once()
        upsert_arg = mock_mysql_manager.upsert_configs.call_args[0][0]
        assert len(upsert_arg) == 3
        mock_mysql_manager.delete_stale_configs.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_handles_duplicate_project_key_pairs(
        self, config_manager, mock_mongo_manager, mock_mysql_manager
    ):
        """Test that duplicate (project, key) pairs are deduplicated."""
        mock_mongo_manager.fetch_all_configs.return_value = [
            {"project": "proj", "key": "key1", "value": "val1"},
            {"project": "proj", "key": "key1", "value": "val2"},
            {"project": "proj", "key": "key1", "value": "val3"},
        ]

        await config_manager.sync_from_remote()

        upsert_arg = mock_mysql_manager.upsert_configs.call_args[0][0]
        assert len(upsert_arg) == 1
        assert upsert_arg[0] == ("proj", "key1", "val1")  # First value is kept

    @pytest.mark.asyncio
    async def test_get_config_returns_value(
        self, config_manager, mock_mysql_manager
    ):
        """Test get_config returns value from MySQL."""
        mock_mysql_manager.get_config.return_value = "test-value"

        result = await config_manager.get_config("my-project", "api_key")

        mock_mysql_manager.get_config.assert_called_once_with("my-project", "api_key")
        assert result == "test-value"

    @pytest.mark.asyncio
    async def test_get_config_returns_none_when_not_found(
        self, config_manager, mock_mysql_manager
    ):
        """Test get_config returns None when config not found."""
        mock_mysql_manager.get_config.return_value = None

        result = await config_manager.get_config("nonexistent", "key")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stats_returns_cache_stats(
        self, config_manager, mock_mysql_manager
    ):
        """Test get_stats returns CacheStats."""
        mock_mysql_manager.get_stats.return_value = {
            "projects_loaded": 5,
            "cache_keys_total": 100
        }

        result = await config_manager.get_stats()

        mock_mysql_manager.get_stats.assert_called_once()
        assert isinstance(result, CacheStats)
        assert result.projects_loaded == 5
        assert result.cache_keys_total == 100

    @pytest.mark.asyncio
    async def test_close_calls_both_managers(
        self, config_manager, mock_mongo_manager, mock_mysql_manager
    ):
        """Test close() closes both MongoDB and MySQL connections."""
        await config_manager.close()

        mock_mongo_manager.close.assert_called_once()
        mock_mysql_manager.close.assert_called_once()
