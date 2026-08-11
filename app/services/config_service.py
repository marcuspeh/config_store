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

    async def close(self) -> None:
        """Close the underlying MongoDB connection."""
        await self._mongo.close()