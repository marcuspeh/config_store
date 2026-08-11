from tortoise import fields
from tortoise.models import Model


class ConfigModel(Model):
    """Tortoise ORM model for configs table."""
    id = fields.IntField(pk=True)
    project = fields.CharField(max_length=255)
    config_key = fields.CharField(max_length=255)
    value = fields.TextField()

    class Meta:
        table = "configs"
        unique_together = (("project", "config_key"),)