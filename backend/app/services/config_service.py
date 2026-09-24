import logging
from typing import Optional

from app.clients.mongo import MongoClient
from app.config.settings import Settings, get_settings
from app.core.models import CacheStats
from app.database.repositories.config import ConfigRepository

logger = logging.getLogger(__name__)


class ConfigService:
    """Orchestrates MongoDB → MySQL sync and serves reads from the MySQL cache."""

    def __init__(
        self,
        settings: Settings | None = None,
        mongo: MongoClient | None = None,
        repo: ConfigRepository | None = None,
    ) -> None:
        s = settings or get_settings()
        self._mongo = mongo or MongoClient(s.mongo_uri, s.mongo_db, s.mongo_collection)
        self._repo = repo or ConfigRepository()

    async def sync_from_remote(self) -> None:
        """Pull all configs from MongoDB and refresh the MySQL cache."""
        try:
            logger.info("Starting synchronization from MongoDB to MySQL...")
            mongo_configs = await self._mongo.fetch_all_configs()

            seen: set[tuple[str, str]] = set()
            upsert_data: list[tuple[str, str, str]] = []
            current_keys: list[tuple[str, str]] = []

            for doc in mongo_configs:
                project = doc.get("project")
                key = doc.get("key")
                value = doc.get("value")

                if project and key and (project, key) not in seen:
                    seen.add((project, key))
                    upsert_data.append((project, key, value))
                    current_keys.append((project, key))

            if upsert_data:
                await self._repo.upsert(upsert_data)

            await self._repo.delete_stale(current_keys)

            logger.info("Synchronization complete.")
        except Exception as e:
            logger.error(f"Synchronization failed: {e}")

    async def get_config(self, project: str, key: str) -> Optional[str]:
        """Retrieve a config value from the local MySQL cache."""
        return await self._repo.get_value(project, key)

    async def get_stats(self) -> CacheStats:
        """Return cache statistics from MySQL."""
        stats = await self._repo.stats()
        return CacheStats(**stats)

    async def list_projects(self) -> list[tuple[str, int]]:
        """Return [(project, config_count)] for every distinct project."""
        return await self._repo.distinct_projects()

    async def list_configs(self, project: str) -> list[tuple[str, str]]:
        """Return [(config_key, value)] for every row in `project`."""
        return await self._repo.list_for_project(project)

    async def create_config(
        self, project: str, key: str, value: str
    ) -> None:
        """Create a new (project, key, value).

        Writes through to MongoDB (source of truth) first, then to
        MySQL. Subsequent reads see the new value immediately because
        every read goes through the repo (no in-memory cache layer).
        """
        try:
            await self._mongo.upsert_config(project, key, value)
        except Exception:
            # Don't poison MySQL if Mongo write failed; surface to caller.
            raise
        await self._repo.create(project, key, value)
        logger.info(f"Created config {project}/{key}")

    async def update_config(
        self, project: str, key: str, value: str
    ) -> None:
        """Update an existing (project, key) value.

        Same order as create: Mongo first, then MySQL.
        """
        try:
            await self._mongo.upsert_config(project, key, value)
        except Exception:
            raise
        await self._repo.update(project, key, value)
        logger.info(f"Updated config {project}/{key}")

    async def close(self) -> None:
        """Close the underlying MongoDB connection."""
        await self._mongo.close()