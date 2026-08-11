import logging
from typing import Optional

from app.core.models import CacheStats
from app.db.mongodb_manager import MongoDBManager
from app.db.mysql_manager import MySQLManager
from app.config.settings import settings

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self):
        self.mongo = MongoDBManager(
            settings.mongo_uri, settings.mongo_db, settings.mongo_collection
        )
        self.mysql = MySQLManager(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
        )

    async def init(self):
        """Initialize the managers (e.g., MySQL table)."""
        await self.mysql.init_db()

    async def sync_from_remote(self):
        """Perform Remote-to-Local sync (MongoDB to MySQL)."""
        try:
            logger.info("Starting synchronization from MongoDB to MySQL...")
            mongo_configs = await self.mongo.fetch_all_configs()

            seen = set()
            upsert_data = []
            current_keys = []

            for doc in mongo_configs:
                project = doc.get("project")
                key = doc.get("key")
                value = doc.get("value")

                if project and key and (project, key) not in seen:
                    seen.add((project, key))
                    upsert_data.append((project, key, value))
                    current_keys.append((project, key))

            # Update MySQL
            if upsert_data:
                await self.mysql.upsert_configs(upsert_data)

            # Cleanup stale records
            await self.mysql.delete_stale_configs(current_keys)

            logger.info("Synchronization complete.")
        except Exception as e:
            logger.error(f"Synchronization failed: {e}")

    async def get_config(self, project: str, key: str) -> Optional[str]:
        """Retrieve a config value from the local MySQL cache."""
        return await self.mysql.get_config(project, key)

    async def get_stats(self) -> CacheStats:
        """Return cache statistics from MySQL."""
        stats = await self.mysql.get_stats()
        return CacheStats(**stats)

    async def close(self):
        """Close connections."""
        await self.mongo.close()
        await self.mysql.close()