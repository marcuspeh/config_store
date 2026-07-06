from tortoise import Tortoise, fields
from tortoise.models import Model


class ConfigModel(Model):
    """Tortoise ORM model for configs table."""
    project = fields.CharField(max_length=255, pk=True)
    config_key = fields.CharField(max_length=255, pk=True)
    value = fields.TextField()

    class Meta:
        table = "configs"