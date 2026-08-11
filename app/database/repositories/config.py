import logging
from typing import Optional, List, Tuple

from tortoise.expressions import Q

from app.database.models.config import ConfigModel

logger = logging.getLogger(__name__)


class ConfigRepository:
    """Async repository for cached configs stored in MySQL."""

    async def upsert(self, configs: List[Tuple[str, str, str]]) -> None:
        """Insert new (project, key, value) rows or update existing ones."""
        if not configs:
            return

        for project, key, value in configs:
            obj, _ = await ConfigModel.get_or_create(
                project=project,
                config_key=key,
                defaults={"value": value},
            )
            if obj.value != value:
                obj.value = value
                await obj.save()
        logger.info(f"Upserted {len(configs)} records into MySQL")

    async def delete_stale(self, current_keys: List[Tuple[str, str]]) -> None:
        """Delete rows that are not present in `current_keys`."""
        if not current_keys:
            deleted = await ConfigModel.all().delete()
            logger.info(f"Deleted {deleted} stale records from MySQL (no current keys)")
            return

        batch_size = 500
        total_deleted = 0
        for i in range(0, len(current_keys), batch_size):
            batch = current_keys[i:i + batch_size]
            conditions = [Q(project=p, config_key=k) for p, k in batch]
            keep_conditions = Q(*conditions, join_type="OR")
            total_deleted += await ConfigModel.filter(~keep_conditions).delete()
        logger.info(
            f"Deleted {total_deleted} stale records not in current set "
            f"of {len(current_keys)} keys"
        )

    async def get_value(self, project: str, config_key: str) -> Optional[str]:
        """Retrieve a single config value by (project, key)."""
        record = await ConfigModel.get_or_none(project=project, config_key=config_key)
        return record.value if record else None

    async def stats(self) -> dict:
        """Return cache statistics: number of distinct projects and total keys."""
        all_configs = await ConfigModel.all().values("project")
        projects = {c["project"] for c in all_configs}
        return {
            "projects_loaded": len(projects),
            "cache_keys_total": len(all_configs),
        }