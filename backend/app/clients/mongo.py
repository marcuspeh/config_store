import logging
from typing import List, Dict

from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)


class MongoClient:
    """Thin async wrapper over MongoDB used as the source-of-truth config store."""

    def __init__(self, uri: str, db_name: str, collection_name: str) -> None:
        self._client = AsyncIOMotorClient(uri)
        self._collection = self._client[db_name][collection_name]

    async def fetch_all_configs(self) -> List[Dict[str, str]]:
        """Retrieve all configuration documents from MongoDB."""
        configs: List[Dict[str, str]] = []
        try:
            cursor = self._collection.find(
                {}, {"_id": 0, "project": 1, "key": 1, "value": 1}
            )
            async for document in cursor:
                configs.append(document)
            logger.info(f"Fetched {len(configs)} configurations from MongoDB")
        except Exception as e:
            logger.error(f"Failed to fetch configs from MongoDB: {e}")
            raise
        return configs

    async def close(self) -> None:
        """Close the MongoDB connection."""
        self._client.close()