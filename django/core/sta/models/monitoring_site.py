import uuid

from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.conf import settings

from core.iam.models import Workspace
from core.iam.permissions.registry import register_resource_type

from .mixins import LinkedResourceMixin
from .validators import validate_tags


class MonitoringSiteQuerySet(models.QuerySet):
    def delete(self):
        from .datastream import Datastream

        Datastream.objects.filter(monitoring_site__in=self).delete()

        return super().delete()


@register_resource_type(privacy_chain=["is_private", "workspace__is_private"])
class MonitoringSite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        Workspace, related_name="monitoring_sites", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=200)
    description = models.TextField()
    code = models.CharField(max_length=200)
    type = models.CharField(max_length=200)
    latitude = models.DecimalField(max_digits=22, decimal_places=16)
    longitude = models.DecimalField(max_digits=22, decimal_places=16)
    elevation_m = models.DecimalField(
        max_digits=22, decimal_places=16, null=True, blank=True
    )
    elevation_datum = models.CharField(max_length=255, null=True, blank=True)
    admin_area_1 = models.CharField(max_length=200, null=True, blank=True)
    admin_area_2 = models.CharField(max_length=200, null=True, blank=True)
    country = models.CharField(max_length=2, null=True, blank=True)
    is_private = models.BooleanField(default=False)
    data_disclaimer = models.TextField(null=True, blank=True)
    tags = models.JSONField(default=dict, blank=True, validators=[validate_tags])

    objects = MonitoringSiteQuerySet.as_manager()

    class Meta:
        indexes = [
            GinIndex(
                fields=["tags"],
                name="sta_monitoringsite_tags_gin",
                opclasses=["jsonb_path_ops"],
            ),
        ]

    def __str__(self):
        return f"{self.name} - {self.id}"

    def delete(self, *args, **kwargs):
        return type(self).objects.filter(pk=self.pk).delete()


def monitoring_site_file_attachment_storage_path(instance, filename):
    return f"monitoring-sites/{instance.monitoring_site.id}/{filename}"


class MonitoringSiteLinkedResource(LinkedResourceMixin, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    monitoring_site = models.ForeignKey(
        MonitoringSite, related_name="monitoring_site_linked_resources", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to=monitoring_site_file_attachment_storage_path, blank=True, default="")
    url = models.URLField(blank=True, default="", max_length=2000)
    type = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.name} - {self.id}"

    @property
    def link(self):
        if self.url:
            return self.url

        storage = self.file.storage

        try:
            file_link = storage.url(self.file.name, expire=3600)
        except TypeError:
            file_link = storage.url(self.file.name)

        if settings.MEDIA_STORAGE_IS_LOCAL:
            file_link = settings.PROXY_BASE_URL + file_link

        return file_link

    class Meta:
        unique_together = ("monitoring_site", "name")
        constraints = [
            models.CheckConstraint(
                condition=(
                    (models.Q(file="") & ~models.Q(url="")) |
                    (~models.Q(file="") & models.Q(url=""))
                ),
                name="monitoring_site_linked_resource_file_xor_url",
            )
        ]


class SiteTypeManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)


class SiteType(models.Model):
    name = models.CharField(max_length=200, unique=True)
    objects = SiteTypeManager()

    def natural_key(self):
        return (self.name,)


class LinkedResourceType(models.Model):
    name = models.CharField(max_length=200, unique=True)
