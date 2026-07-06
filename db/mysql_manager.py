import logging
from typing import Optional, List, Tuple
from tortoise import Tortoise
from tortoise.expressions import Q
from tortoise.functions import Count
from .models import ConfigModel

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
        )
        await Tortoise.generate_schemas()
        logger.info(f"MySQL database initialized at {self.host}:{self.port}/{self.database}")

    async def upsert_configs(self, configs: List[Tuple[str, str, str]]):
        """Batch insert or replace configuration records in a single statement."""
        if not configs:
            return

        records = []
        for project, key, value in configs:
            records.append(ConfigModel(project=project, config_key=key, value=value))

        await ConfigModel.bulk_create(records, on_conflict=["project", "config_key"], update_fields=["value"], batch_size=1000)
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
        row = await ConfigModel.annotate(
            projects_count=Count("project", distinct=True),
            keys_count=Count("id"),
        ).values("projects_count", "keys_count").first()

        if row:
            projects_count = row["projects_count"]
            keys_count = row["keys_count"]
        else:
            projects_count = 0
            keys_count = 0

        return {
            "projects_loaded": projects_count,
            "cache_keys_total": keys_count
        }

    async def close(self):
        """Close the Tortoise ORM connection."""
        await Tortoise.close_connections()
        logger.info("MySQL connection closed")