import uuid

from django.db import models
from django.conf import settings

from core.iam.permissions.registry import register_resource_type

from .thing import Thing
from .sensor import Sensor
from .unit import Unit
from .processing_level import ProcessingLevel
from .observed_property import ObservedProperty


class DatastreamQuerySet(models.QuerySet):
    def delete(self):
        from .observation import Observation

        Observation.objects.filter(datastream__in=self).delete()

        return super().delete()


@register_resource_type(workspace_field="thing__workspace", privacy_chain=[
    "is_private", "thing__is_private",
    "thing__workspace__is_private"
])
class Datastream(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()
    thing = models.ForeignKey(
        Thing, on_delete=models.CASCADE, related_name="datastreams"
    )
    sensor = models.ForeignKey(
        Sensor, on_delete=models.PROTECT, related_name="datastreams"
    )
    observed_property = models.ForeignKey(
        ObservedProperty, on_delete=models.PROTECT, related_name="datastreams"
    )
    processing_level = models.ForeignKey(
        ProcessingLevel, on_delete=models.PROTECT, related_name="datastreams"
    )
    unit = models.ForeignKey(
        Unit, on_delete=models.PROTECT, related_name="datastreams"
    )
    observation_type = models.CharField(max_length=255)
    result_type = models.CharField(max_length=255)
    status = models.CharField(max_length=255, null=True, blank=True)
    observed_area = models.CharField(max_length=255, null=True, blank=True)  # Unused
    sampled_medium = models.CharField(max_length=255)
    value_count = models.IntegerField(null=True, blank=True)
    no_data_value = models.FloatField()
    intended_time_spacing = models.FloatField(null=True, blank=True)
    intended_time_spacing_unit = models.CharField(max_length=255, null=True, blank=True)
    aggregation_statistic = models.CharField(max_length=255)
    time_aggregation_interval = models.FloatField()
    time_aggregation_interval_unit = models.CharField(max_length=255)
    phenomenon_begin_time = models.DateTimeField(null=True, blank=True)
    phenomenon_end_time = models.DateTimeField(null=True, blank=True)
    result_end_time = models.DateTimeField(null=True, blank=True)  # Unused
    result_begin_time = models.DateTimeField(null=True, blank=True)  # Unused
    is_private = models.BooleanField(default=True)
    is_visible = models.BooleanField(default=True)

    objects = DatastreamQuerySet.as_manager()

    def __str__(self):
        return f"{self.name} — {self.id}"

    def delete(self, *args, **kwargs):
        return type(self).objects.filter(pk=self.pk).delete()


class DatastreamTag(models.Model):
    datastream = models.ForeignKey(
        Datastream, related_name="datastream_tags", on_delete=models.CASCADE
    )
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.key}: {self.value} - {self.id}"


def datastream_file_attachment_storage_path(instance, filename):
    return f"datastreams/{instance.datastream.id}/{filename}"


class DatastreamFileAttachment(models.Model):
    datastream = models.ForeignKey(
        Datastream,
        related_name="datastream_file_attachments",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file_attachment = models.FileField(
        upload_to=datastream_file_attachment_storage_path
    )
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

        if settings.DEPLOYMENT_BACKEND == "local":
            file_attachment_link = settings.PROXY_BASE_URL + file_attachment_link

        return file_attachment_link

    class Meta:
        unique_together = ("datastream", "name")


class DatastreamAggregation(models.Model):
    name = models.CharField(max_length=255, unique=True)


class DatastreamStatus(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name_plural = "Datastream statuses"


class SampledMedium(models.Model):
    name = models.CharField(max_length=255, unique=True)
