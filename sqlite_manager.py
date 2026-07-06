import aiosqlite
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

class SQLiteManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init_db(self):
        """Create the configs table if it doesn't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS configs (
                    project TEXT,
                    key TEXT,
                    value TEXT,
                    PRIMARY KEY (project, key)
                )
            """)
            await db.commit()
        logger.info(f"SQLite database initialized at {self.db_path}")

    async def upsert_configs(self, configs: List[Tuple[str, str, str]]):
        """Batch insert or replace configuration records."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany("""
                INSERT OR REPLACE INTO configs (project, key, value)
                VALUES (?, ?, ?)
            """, configs)
            await db.commit()
        logger.info(f"Upserted {len(configs)} records into SQLite")

    async def delete_stale_configs(self, current_keys: List[Tuple[str, str]]):
        """Delete records from SQLite that are not in the current_keys list."""
        async with aiosqlite.connect(self.db_path) as db:
            # Fetch all existing keys in SQLite
            async with db.execute("SELECT project, key FROM configs") as cursor:
                existing_keys = await cursor.fetchall()

            keys_to_delete = [key for key in existing_keys if key not in current_keys]

            if keys_to_delete:
                await db.executemany("""
                    DELETE FROM configs WHERE project = ? AND key = ?
                """, keys_to_delete)
                await db.commit()
                logger.info(f"Deleted {len(keys_to_delete)} stale records from SQLite")

    async def get_config(self, project: str, key: str) -> Optional[str]:
        """Retrieve a config value from SQLite."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT value FROM configs WHERE project = ? AND key = ?
            """, (project, key)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def get_stats(self) -> dict:
        """Return cache statistics from SQLite."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(DISTINCT project) FROM configs") as cursor:
                projects_count = (await cursor.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM configs") as cursor:
                keys_count = (await cursor.fetchone())[0]
        
        return {
            "projects_loaded": projects_count,
            "cache_keys_total": keys_count
        }
