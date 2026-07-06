import logging
from typing import Optional, List, Tuple
from tortoise import Tortoise, fields
from tortoise.models import Model

logger = logging.getLogger(__name__)

class ConfigModel(Model):
    """Tortoise ORM model for configs table."""
    project = fields.CharField(max_length=255, pk=True)
    config_key = fields.CharField(max_length=255, pk=True)
    value = fields.TextField()

    class Meta:
        table = "configs"

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
            modules={"models": ["mysql_manager"]},
        )
        await Tortoise.generate_schemas()
        logger.info(f"MySQL database initialized at {self.host}:{self.port}/{self.database}")

    async def upsert_configs(self, configs: List[Tuple[str, str, str]]):
        """Batch insert or replace configuration records."""
        for project, key, value in configs:
            await ConfigModel.update_or_create(
                project=project,
                config_key=key,
                defaults={"value": value}
            )
        logger.info(f"Upserted {len(configs)} records into MySQL")

    async def delete_stale_configs(self, current_keys: List[Tuple[str, str]]):
        """Delete records from MySQL that are not in the current_keys list."""
        if not current_keys:
            return

        existing = await ConfigModel.all().values_list("project", "config_key")
        keys_to_delete = [key for key in existing if key not in current_keys]

        if keys_to_delete:
            for project, key in keys_to_delete:
                await ConfigModel.filter(project=project, config_key=key).delete()
            logger.info(f"Deleted {len(keys_to_delete)} stale records from MySQL")

    async def get_config(self, project: str, config_key: str) -> Optional[str]:
        """Retrieve a config value from MySQL."""
        record = await ConfigModel.get_or_none(project=project, config_key=config_key)
        return record.value if record else None

    async def get_stats(self) -> dict:
        """Return cache statistics from MySQL."""
        projects_count = await ConfigModel.distinct().count()
        keys_count = await ConfigModel.all().count()

        return {
            "projects_loaded": projects_count,
            "cache_keys_total": keys_count
        }

    async def close(self):
        """Close the Tortoise ORM connection."""
        await Tortoise.close_connections()
        logger.info("MySQL connection closed")