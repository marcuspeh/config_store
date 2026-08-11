from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # MongoDB (source of truth)
    mongo_uri: str = Field(default="mongodb://localhost:27017")
    mongo_db: str = Field(default="config_db")
    mongo_collection: str = Field(default="configs")

    # Database (individual MySQL fields)
    mysql_host: str = Field(default="localhost")
    mysql_port: int = Field(default=3306)
    mysql_user: str = Field(default="config_store")
    mysql_password: str = Field(default="config_store_password")
    mysql_database: str = Field(default="config_store")

    # Periodic sync interval (seconds)
    sync_interval: int = Field(default=60)

    @property
    def database_url(self) -> str:
        # URL-encode credentials so passwords containing @, :, /, etc. don't
        # break the DSN.
        user = quote_plus(self.mysql_user)
        password = quote_plus(self.mysql_password)
        return (
            f"mysql://{user}:{password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()