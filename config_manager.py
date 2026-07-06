import logging
from typing import List, Tuple, Optional

from .models import CacheStats
from .mongodb_manager import MongoDBManager
from .sqlite_manager import SQLiteManager
from .settings import settings

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self):
        self.mongo = MongoDBManager(settings.MONGO_URI, settings.MONGO_DB, settings.MONGO_COLLECTION)
        self.sqlite = SQLiteManager(settings.SQLITE_DB_PATH)

    async def init(self):
        """Initialize the managers (e.g., SQLite table)."""
        await self.sqlite.init_db()

    async def sync_from_remote(self):
        """Perform Remote-to-Local sync (MongoDB to SQLite)."""
        try:
            logger.info("Starting synchronization from MongoDB to SQLite...")
            mongo_configs = await self.mongo.fetch_all_configs()
            
            # Prepare data for SQLite upsert and tracking
            upsert_data = []
            current_keys = []
            
            for doc in mongo_configs:
                project = doc.get("project")
                key = doc.get("key")
                value = doc.get("value")
                
                if project and key:
                    upsert_data.append((project, key, value))
                    current_keys.append((project, key))

            # Update SQLite
            if upsert_data:
                await self.sqlite.upsert_configs(upsert_data)
            
            # Cleanup stale records
            await self.sqlite.delete_stale_configs(current_keys)
            
            logger.info("Synchronization complete.")
        except Exception as e:
            logger.error(f"Synchronization failed: {e}")

    async def get_config(self, project: str, key: str) -> Optional[str]:
        """Retrieve a config value from the local SQLite cache."""
        return await self.sqlite.get_config(project, key)

    async def get_stats(self) -> CacheStats:
        """Return cache statistics from SQLite."""
        stats = await self.sqlite.get_stats()
        return CacheStats(**stats)

    async def close(self):
        """Close connections."""
        await self.mongo.close()
