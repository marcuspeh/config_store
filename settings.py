import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB: str = os.getenv("MONGO_DB", "config_db")
    MONGO_COLLECTION: str = os.getenv("MONGO_COLLECTION", "configs")
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "mysql")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER: str = os.getenv("MYSQL_USER", "config_store")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "config_store_password")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "config_store")
    SYNC_INTERVAL: int = int(os.getenv("SYNC_INTERVAL", "60"))

settings = Settings()