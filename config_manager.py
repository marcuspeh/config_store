import logging
from typing import Optional

from models import CacheStats
from db.mongodb_manager import MongoDBManager
from db.mysql_manager import MySQLManager
from settings import settings

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self):
        self.mongo = MongoDBManager(settings.MONGO_URI, settings.MONGO_DB, settings.MONGO_COLLECTION)
        self.mysql = MySQLManager(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            database=settings.MYSQL_DATABASE
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