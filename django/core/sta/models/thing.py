import uuid

from django.db import models
from django.conf import settings

from core.iam.models import Workspace
from core.iam.permissions.registry import register_resource_type


class ThingQuerySet(models.QuerySet):
    def with_location(self):
        return self.prefetch_related("locations").annotate()

    def delete(self):
        from .datastream import Datastream

        Datastream.objects.filter(thing__in=self).delete()

        return super().delete()


@register_resource_type(privacy_chain=["is_private", "workspace__is_private"])
class Thing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    workspace = models.ForeignKey(
        Workspace, related_name="things", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=200)
    description = models.TextField()
    sampling_feature_type = models.CharField(max_length=200)
    sampling_feature_code = models.CharField(max_length=200)
    site_type = models.CharField(max_length=200)
    is_private = models.BooleanField(default=False)
    data_disclaimer = models.TextField(null=True, blank=True)

    objects = ThingQuerySet.as_manager()

    def __str__(self):
        return f"{self.name} - {self.id}"

    def delete(self, *args, **kwargs):
        return type(self).objects.filter(pk=self.pk).delete()

    @property
    def location(self):
        if (
            hasattr(self, "_prefetched_objects_cache")
            and "locations" in self._prefetched_objects_cache  # noqa
        ):
            locations = self._prefetched_objects_cache["locations"]
            return locations[0] if locations else None
        return self.locations.first()


class ThingTag(models.Model):
    thing = models.ForeignKey(
        Thing, related_name="thing_tags", on_delete=models.CASCADE
    )
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.key}: {self.value} - {self.id}"


def thing_file_attachment_storage_path(instance, filename):
    return f"things/{instance.thing.id}/{filename}"


class ThingFileAttachment(models.Model):
    thing = models.ForeignKey(
        Thing, related_name="thing_file_attachments", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file_attachment = models.FileField(upload_to=thing_file_attachment_storage_path)
    file_attachment_type = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.name} - {self.id}"

    @property
    def link(self):
        storage = self.file_attachment.storage

        try:
            file_attachment_link = storage.url(self.file_attachment.name, expire=3600)
        except TypeError:
            file_attachment_link = storage.url(self.file_attachment.name)

        if settings.MEDIA_STORAGE_IS_LOCAL:
            file_attachment_link = settings.PROXY_BASE_URL + file_attachment_link

        return file_attachment_link

    class Meta:
        unique_together = ("thing", "name")


class SamplingFeatureType(models.Model):
    name = models.CharField(max_length=200, unique=True)


class SiteTypeManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)


class SiteType(models.Model):
    name = models.CharField(max_length=200, unique=True)
    objects = SiteTypeManager()

    def natural_key(self):
        return (self.name,)


class FileAttachmentType(models.Model):
    name = models.CharField(max_length=200, unique=True)
