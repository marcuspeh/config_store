"""Test Pydantic models."""
import pytest
from pydantic import ValidationError

from models import ConfigResponse, CacheStats, HealthResponse


class TestConfigResponse:
    """Tests for ConfigResponse model."""

    def test_valid_config_response(self):
        """Test creating a valid ConfigResponse."""
        response = ConfigResponse(
            project="my-project",
            key="database_url",
            value="postgres://localhost:5432/mydb"
        )
        assert response.project == "my-project"
        assert response.key == "database_url"
        assert response.value == "postgres://localhost:5432/mydb"

    def test_config_response_string_values(self):
        """Test that all fields must be strings."""
        with pytest.raises(ValidationError):
            ConfigResponse(project=123, key="key", value="value")

        with pytest.raises(ValidationError):
            ConfigResponse(project="proj", key="key", value=456)

    def test_config_response_empty_strings(self):
        """Test that empty strings are valid."""
        response = ConfigResponse(project="", key="", value="")
        assert response.project == ""
        assert response.key == ""


class TestCacheStats:
    """Tests for CacheStats model."""

    def test_valid_cache_stats(self):
        """Test creating a valid CacheStats."""
        stats = CacheStats(projects_loaded=5, cache_keys_total=100)
        assert stats.projects_loaded == 5
        assert stats.cache_keys_total == 100

    def test_cache_stats_zero_values(self):
        """Test zero values are valid."""
        stats = CacheStats(projects_loaded=0, cache_keys_total=0)
        assert stats.projects_loaded == 0
        assert stats.cache_keys_total == 0

    def test_cache_stats_must_be_integers(self):
        """Test that stats fields must be integers."""
        with pytest.raises(ValidationError):
            CacheStats(projects_loaded="five", cache_keys_total=100)

        with pytest.raises(ValidationError):
            CacheStats(projects_loaded=5, cache_keys_total=100.5)


class TestHealthResponse:
    """Tests for HealthResponse model."""

    def test_valid_health_response(self):
        """Test creating a valid HealthResponse."""
        stats = CacheStats(projects_loaded=3, cache_keys_total=50)
        response = HealthResponse(status="ok", stats=stats)
        assert response.status == "ok"
        assert response.stats.projects_loaded == 3
        assert response.stats.cache_keys_total == 50

    def test_health_response_with_different_status(self):
        """Test HealthResponse with various status values."""
        stats = CacheStats(projects_loaded=0, cache_keys_total=0)

        response = HealthResponse(status="refreshed", stats=stats)
        assert response.status == "refreshed"

    def test_health_response_requires_stats(self):
        """Test that stats field is required."""
        with pytest.raises(ValidationError):
            HealthResponse(status="ok")
