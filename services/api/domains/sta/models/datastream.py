import uuid6
import typing
from typing import Literal, Optional, Union
from django.db import models
from django.db.models import Q
from django.conf import settings
from domains.iam.models import Workspace
from domains.iam.models.utils import PermissionChecker
from .thing import Thing
from .sensor import Sensor
from .unit import Unit
from .processing_level import ProcessingLevel
from .observed_property import ObservedProperty

if typing.TYPE_CHECKING:
    from django.contrib.auth import get_user_model
    from domains.iam.models import Workspace, APIKey

    User = get_user_model()


class DatastreamQuerySet(models.QuerySet):
    def visible(self, principal: Optional[Union["User", "APIKey"]]):
        if hasattr(principal, "account_type"):
            if principal.account_type == "admin":
                return self
            else:
                return self.filter(
                    Q(
                        thing__workspace__is_private=False,
                        thing__is_private=False,
                        is_private=False,
                    )
                    | Q(thing__workspace__owner=principal)
                    | Q(
                        thing__workspace__collaborators__user=principal,
                        thing__workspace__collaborators__role__permissions__resource_type__in=[
                            "*",
                            "Datastream",
                        ],
                        thing__workspace__collaborators__role__permissions__permission_type__in=[
                            "*",
                            "view",
                        ],
                    )
                )
        elif hasattr(principal, "workspace"):
            return self.filter(
                Q(
                    thing__workspace__is_private=False,
                    thing__is_private=False,
                    is_private=False,
                )
                | Q(
                    thing__workspace__apikeys=principal,
                    thing__workspace__apikeys__role__permissions__resource_type__in=[
                        "*",
                        "Datastream",
                    ],
                    thing__workspace__apikeys__role__permissions__permission_type__in=[
                        "*",
                        "view",
                    ],
                )
            )
        else:
            return self.filter(
                Q(
                    thing__workspace__is_private=False,
                    thing__is_private=False,
                    is_private=False,
                )
            )


class Datastream(models.Model, PermissionChecker):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()
    thing = models.ForeignKey(
        Thing, on_delete=models.DO_NOTHING, related_name="datastreams"
    )
    sensor = models.ForeignKey(
        Sensor, on_delete=models.DO_NOTHING, related_name="datastreams"
    )
    observed_property = models.ForeignKey(
        ObservedProperty, on_delete=models.DO_NOTHING, related_name="datastreams"
    )
    processing_level = models.ForeignKey(
        ProcessingLevel, on_delete=models.DO_NOTHING, related_name="datastreams"
    )
    unit = models.ForeignKey(
        Unit, on_delete=models.DO_NOTHING, related_name="datastreams"
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
        return f"{self.name} - {self.id}"

    @classmethod
    def can_principal_create(
        cls, principal: Optional[Union["User", "APIKey"]], workspace: "Workspace"
    ):
        return cls.check_create_permissions(
            principal=principal, workspace=workspace, resource_type="Datastream"
        )

    def get_principal_permissions(
        self, principal: Optional[Union["User", "APIKey"]]
    ) -> list[Literal["edit", "delete", "view"]]:
        permissions = self.check_object_permissions(
            principal=principal,
            workspace=self.thing.workspace,
            resource_type="Datastream",
        )

        if (
            not self.thing.workspace.is_private
            and not self.thing.is_private
            and not self.is_private
            and "view" not in list(permissions)
        ):
            permissions = list(permissions) + ["view"]

        return permissions

    def delete(self, *args, **kwargs):
        self.delete_contents(filter_arg=self, filter_suffix="")
        super().delete(*args, **kwargs)

    @staticmethod
    def delete_contents(filter_arg: models.Model, filter_suffix: Optional[str]):
        from domains.sta.models import (
            Observation,
            DatastreamTag,
            DatastreamFileAttachment,
        )

        datastream_relation_filter = (
            f"datastream__{filter_suffix}" if filter_suffix else "datastream"
        )

        Observation.delete_contents(
            filter_arg=filter_arg, filter_suffix=datastream_relation_filter
        )
        obs_qs = Observation.objects.filter(**{datastream_relation_filter: filter_arg})
        obs_qs._raw_delete(using=obs_qs.db)  # noqa

        DatastreamTag.objects.filter(
            **{datastream_relation_filter: filter_arg}
        ).delete()
        DatastreamFileAttachment.objects.filter(
            **{datastream_relation_filter: filter_arg}
        ).delete()


class DatastreamTagQuerySet(models.QuerySet):
    def visible(self, principal: Optional[Union["User", "APIKey"]]):
        if hasattr(principal, "account_type"):
            if principal.account_type == "admin":
                return self
            else:
                return self.filter(
                    Q(
                        datastream__thing__workspace__is_private=False,
                        datastream__thing__is_private=False,
                        datastream__is_private=False,
                    )
                    | Q(datastream__thing__workspace__owner=principal)
                    | Q(
                        datastream__thing__workspace__collaborators__user=principal,
                        datastream__thing__workspace__collaborators__role__permissions__resource_type__in=[
                            "*",
                            "Datastream",
                        ],
                        datastream__thing__workspace__collaborators__role__permissions__permission_type__in=[
                            "*",
                            "view",
                        ],
                    )
                )
        elif hasattr(principal, "workspace"):
            return self.filter(
                Q(
                    datastream__thing__workspace__is_private=False,
                    datastream__thing__is_private=False,
                    datastream__is_private=False,
                )
                | Q(
                    datastream__thing__workspace__apikeys=principal,
                    datastream__thing__workspace__apikeys__role__permissions__resource_type__in=[
                        "*",
                        "Datastream",
                    ],
                    datastream__thing__workspace__apikeys__role__permissions__permission_type__in=[
                        "*",
                        "view",
                    ],
                )
            )
        else:
            return self.filter(
                Q(
                    datastream__thing__workspace__is_private=False,
                    datastream__thing__is_private=False,
                    datastream__is_private=False,
                )
            )


class DatastreamTag(models.Model, PermissionChecker):
    datastream = models.ForeignKey(
        Datastream, related_name="datastream_tags", on_delete=models.DO_NOTHING
    )
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.key}: {self.value} - {self.id}"

    objects = DatastreamTagQuerySet.as_manager()


def datastream_file_attachment_storage_path(instance, filename):
    return f"datastreams/{instance.datastream.id}/{filename}"


class DatastreamFileAttachment(models.Model, PermissionChecker):
    datastream = models.ForeignKey(
        Datastream,
        related_name="datastream_file_attachments",
        on_delete=models.DO_NOTHING,
    )
    name = models.CharField(max_length=255)
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
