from tortoise import Tortoise

from app.config.settings import get_settings


async def init_db() -> None:
    """Initialize Tortoise ORM and create tables."""
    settings = get_settings()
    await Tortoise.init(
        db_url=settings.database_url,
        modules={"models": ["app.database.models"]},
        _enable_global_fallback=True,
    )
    await Tortoise.generate_schemas()


async def close_db() -> None:
    """Close all Tortoise ORM connections."""
    await Tortoise.close_connections()