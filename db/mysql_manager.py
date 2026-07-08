import logging
from typing import Optional, List, Tuple
from tortoise import Tortoise
from tortoise.expressions import Q
from tortoise.functions import Count
from db.models import ConfigModel

logger = logging.getLogger(__name__)

class MySQLManager:
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

    async def init_db(self):
        """Initialize Tortoise ORM and create tables."""
        await Tortoise.init(
            db_url=f"mysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}",
            modules={"models": ["db.models"]},
            _enable_global_fallback=True,
        )
        await Tortoise.generate_schemas()
        logger.info(f"MySQL database initialized at {self.host}:{self.port}/{self.database}")

    async def upsert_configs(self, configs: List[Tuple[str, str, str]]):
        """Batch insert or replace configuration records."""
        if not configs:
            return

        for project, key, value in configs:
            obj, _ = await ConfigModel.get_or_create(
                project=project,
                config_key=key,
                defaults={"value": value}
            )
            if obj.value != value:
                obj.value = value
                await obj.save()
        logger.info(f"Upserted {len(configs)} records into MySQL")

    async def delete_stale_configs(self, current_keys: List[Tuple[str, str]]):
        """Delete records from MySQL that are not in the current_keys list using pure ORM."""
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
        logger.info(f"Deleted {total_deleted} stale records not in current set of {len(current_keys)} keys")

    async def get_config(self, project: str, config_key: str) -> Optional[str]:
        """Retrieve a config value from MySQL."""
        record = await ConfigModel.get_or_none(project=project, config_key=config_key)
        return record.value if record else None

    async def get_stats(self) -> dict:
        """Return cache statistics from MySQL."""
        all_configs = await ConfigModel.all().values("project")
        projects = set(c["project"] for c in all_configs)

        return {
            "projects_loaded": len(projects),
            "cache_keys_total": len(all_configs)
        }

    async def close(self):
        """Close the Tortoise ORM connection."""
        await Tortoise.close_connections()
        logger.info("MySQL connection closed")