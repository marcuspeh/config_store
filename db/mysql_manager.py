import logging
from typing import Optional, List, Tuple
from tortoise import Tortoise
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

        placeholders = ",".join(["(%s,%s,%s)"] * len(configs))
        params = [v for row in configs for v in row]

        await ConfigModel.raw(
            f"""
            INSERT INTO configs (project, config_key, value)
            VALUES {placeholders}
            ON DUPLICATE KEY UPDATE value = VALUES(value)
            """,
            params,
        )
        logger.info(f"Upserted {len(configs)} records into MySQL")

    async def delete_stale_configs(self, current_keys: List[Tuple[str, str]]):
        """Delete records from MySQL that are not in the current_keys list."""
        if not current_keys:
            # No current keys means everything is stale
            deleted = await ConfigModel.all().delete()
            logger.info(f"Deleted {deleted} stale records from MySQL (no current keys)")
            return

        # Use a NOT IN clause via raw SQL for efficiency
        placeholders = ",".join(["(%s,%s)"] * len(current_keys))
        params = [v for pair in current_keys for v in pair]

        await ConfigModel.raw(
            f"""
            DELETE FROM configs
            WHERE (project, config_key) NOT IN ({placeholders})
            """,
            params,
        )
        logger.info(f"Deleted stale records not in current set of {len(current_keys)} keys")

    async def get_config(self, project: str, config_key: str) -> Optional[str]:
        """Retrieve a config value from MySQL."""
        record = await ConfigModel.get_or_none(project=project, config_key=config_key)
        return record.value if record else None

    async def get_stats(self) -> dict:
        """Return cache statistics from MySQL."""
        distinct_projects = await ConfigModel.raw(
            "SELECT COUNT(DISTINCT project) AS count FROM configs"
        )
        projects_count = distinct_projects[0]["count"]
        keys_count = await ConfigModel.all().count()

        return {
            "projects_loaded": projects_count,
            "cache_keys_total": keys_count
        }

    async def close(self):
        """Close the Tortoise ORM connection."""
        await Tortoise.close_connections()
        logger.info("MySQL connection closed")