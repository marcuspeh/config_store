"""Tortoise ORM models.

Importing each model module here is required so that `Tortoise.init(
modules={"models": ["app.database.models"]})` discovers the Model classes
and binds them to the configured database connection. Without this, the
model classes still exist in Python (via transitive imports) but
Tortoise's registry won't see them, and queries will fail with
`default_connection for the model ... cannot be None`.
"""

from app.database.models.config import ConfigModel  # noqa: F401

__all__ = ["ConfigModel"]