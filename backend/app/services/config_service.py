from typing import Optional

from app.clients.mongo import MongoClient
from app.config.settings import Settings, get_settings
from app.core.models import CacheStats
from app.database.repositories.config import ConfigNotFound, ConfigRepository
from app.logging_setup import client

log = client()


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
        log.info("sync starting source=mongo target=mysql")
        try:
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

            log.info(
                "sync complete fetched=%d upserted=%d", len(mongo_configs), len(upsert_data),
            )
        except Exception as e:
            log.error("sync failed error=%s", e)
            raise

    async def get_config(self, project: str, key: str) -> Optional[str]:
        return await self._repo.get_value(project, key)

    async def get_stats(self) -> CacheStats:
        stats = await self._repo.stats()
        return CacheStats(**stats)

    async def list_projects(self) -> list[tuple[str, int]]:
        return await self._repo.distinct_projects()

    async def list_configs(self, project: str) -> list[tuple[str, str]]:
        return await self._repo.list_for_project(project)

    async def create_config(
        self, project: str, key: str, value: str
    ) -> None:
        """Create a new (project, key, value). Mongo first, then MySQL."""
        log.info("create config project=%s key=%s", project, key)
        try:
            await self._mongo.upsert_config(project, key, value)
        except Exception as e:
            log.error("create config mongo failed project=%s key=%s error=%s", project, key, e)
            raise
        await self._repo.create(project, key, value)
        log.info("create config persisted project=%s key=%s", project, key)

    async def update_config(
        self, project: str, key: str, value: str
    ) -> None:
        """Update an existing (project, key) value. Mongo first, then MySQL."""
        log.info("update config project=%s key=%s", project, key)
        try:
            await self._mongo.upsert_config(project, key, value)
        except Exception as e:
            log.error("update config mongo failed project=%s key=%s error=%s", project, key, e)
            raise
        await self._repo.update(project, key, value)
        log.info("update config persisted project=%s key=%s", project, key)

    async def delete_config(self, project: str, key: str) -> bool:
        """Delete a (project, key) config. Mongo first, then MySQL cache."""
        existing = await self._repo.get_value(project, key)
        if existing is None:
            log.info("delete config missing project=%s key=%s", project, key)
            raise ConfigNotFound(
                f"Config not found for project '{project}' and key '{key}'"
            )
        try:
            await self._mongo.delete_config(project, key)
        except Exception as e:
            log.error("delete config mongo failed project=%s key=%s error=%s", project, key, e)
            raise
        deleted = await self._repo.delete(project, key)
        log.info("delete config persisted project=%s key=%s cache_hit=%s", project, key, deleted)
        return deleted

    async def close(self) -> None:
        await self._mongo.close()