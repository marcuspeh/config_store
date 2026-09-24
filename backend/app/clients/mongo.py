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

    async def upsert_config(self, project: str, key: str, value: str) -> None:
        """Upsert a single (project, key, value) document in MongoDB.

        Mongo is the source of truth — every write must land here so
        the next `sync_from_remote` doesn't wipe the corresponding
        MySQL row via `delete_stale`.
        """
        try:
            await self._collection.update_one(
                {"project": project, "key": key},
                {"$set": {"project": project, "key": key, "value": value}},
                upsert=True,
            )
        except Exception as e:
            logger.error(f"Failed to upsert config in MongoDB: {e}")
            raise

    async def delete_config(self, project: str, key: str) -> None:
        """Remove a (project, key) document from MongoDB.

        No-op if it doesn't exist — mirrors the upsert's tolerance so
        callers can use it idempotently.
        """
        try:
            await self._collection.delete_one({"project": project, "key": key})
        except Exception as e:
            logger.error(f"Failed to delete config from MongoDB: {e}")
            raise

    async def close(self) -> None:
        """Close the MongoDB connection."""
        self._client.close()