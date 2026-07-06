from motor.motor_asyncio import AsyncIOMotorClient
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class MongoDBManager:
    def __init__(self, uri: str, db_name: str, collection_name: str):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    async def fetch_all_configs(self) -> List[Dict[str, str]]:
        """Retrieve all configuration documents from MongoDB."""
        configs = []
        try:
            cursor = self.collection.find({}, {"_id": 0, "project": 1, "key": 1, "value": 1})
            async for document in cursor:
                configs.append(document)
            logger.info(f"Fetched {len(configs)} configurations from MongoDB")
        except Exception as e:
            logger.error(f"Failed to fetch configs from MongoDB: {e}")
            raise
        return configs

    async def close(self):
        """Close the MongoDB connection."""
        self.client.close()