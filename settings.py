import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB: str = os.getenv("MONGO_DB", "config_db")
    MONGO_COLLECTION: str = os.getenv("MONGO_COLLECTION", "configs")
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "config_store/config.db")
    SYNC_INTERVAL: int = int(os.getenv("SYNC_INTERVAL", "60"))

settings = Settings()
