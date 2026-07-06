import aiomysql
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

class MySQLManager:
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self._pool: Optional[aiomysql.Pool] = None

    async def init_db(self):
        """Create the connection pool and configs table if it doesn't exist."""
        self._pool = await aiomysql.create_pool(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            db=self.database,
            autocommit=True
        )
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS configs (
                        project VARCHAR(255),
                        config_key VARCHAR(255),
                        value TEXT,
                        PRIMARY KEY (project, config_key)
                    )
                """)
        logger.info(f"MySQL database initialized at {self.host}:{self.port}/{self.database}")

    async def upsert_configs(self, configs: List[Tuple[str, str, str]]):
        """Batch insert or replace configuration records."""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.executemany("""
                    INSERT INTO configs (project, config_key, value)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE value = VALUES(value)
                """, configs)
            await conn.commit()
        logger.info(f"Upserted {len(configs)} records into MySQL")

    async def delete_stale_configs(self, current_keys: List[Tuple[str, str]]):
        """Delete records from MySQL that are not in the current_keys list."""
        if not current_keys:
            return

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Fetch all existing keys in MySQL
                await cursor.execute("SELECT project, config_key FROM configs")
                existing_keys = await cursor.fetchall()

                keys_to_delete = [key for key in existing_keys if key not in current_keys]

                if keys_to_delete:
                    await cursor.executemany("""
                        DELETE FROM configs WHERE project = %s AND config_key = %s
                    """, keys_to_delete)
                    await conn.commit()
                    logger.info(f"Deleted {len(keys_to_delete)} stale records from MySQL")

    async def get_config(self, project: str, config_key: str) -> Optional[str]:
        """Retrieve a config value from MySQL."""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT value FROM configs WHERE project = %s AND config_key = %s
                """, (project, config_key))
                row = await cursor.fetchone()
                return row[0] if row else None

    async def get_stats(self) -> dict:
        """Return cache statistics from MySQL."""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT COUNT(DISTINCT project) FROM configs")
                projects_count = (await cursor.fetchone())[0]
                await cursor.execute("SELECT COUNT(*) FROM configs")
                keys_count = (await cursor.fetchone())[0]

        return {
            "projects_loaded": projects_count,
            "cache_keys_total": keys_count
        }

    async def close(self):
        """Close the connection pool."""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            logger.info("MySQL connection pool closed")