import uuid
from typing import Optional, Literal, Sequence, get_args
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import QuerySet, Min, Max, Count, F
from django.contrib.postgres.aggregates import ArrayAgg
from django.utils import timezone
from django.http import StreamingHttpResponse
from core.service import ServiceUtils
from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import (
    Datastream,
    Observation,
    DatastreamTag,
    DatastreamFileAttachment,
    DatastreamAggregation,
    DatastreamStatus,
    SampledMedium,
    FileAttachmentType,
)
from interfaces.api.schemas import (
    DatastreamPostBody,
    DatastreamPatchBody,
    TagPostBody,
    TagDeleteBody,
    FileAttachmentPostBody,
    FileAttachmentDeleteBody,
)
from interfaces.api.schemas.sta.datastream import (
    DatastreamOrderByFields,
    DatastreamSummaryResponse,
    DatastreamDetailResponse,
)
from core.sta.services import (
    MonitoringSiteService,
    ObservedPropertyService,
    ProcessingLevelService,
    MethodService,
    UnitService,
)

User = get_user_model()

monitoring_site_service = MonitoringSiteService()
observed_property_service = ObservedPropertyService()
processing_level_service = ProcessingLevelService()
method_service = MethodService()
unit_service = UnitService()


class DatastreamService(ServiceUtils):
    @staticmethod
    def handle_http_404_error(operation, *args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except HttpError as e:
            if e.status_code == 404:
                raise HttpError(400, str(e))
            else:
                raise e

    def get_datastream_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        expand_related: Optional[bool] = None,
        raise_400: bool = False,
    ):
        queryset = Datastream.objects.filter(pk=uid)
        if expand_related:
            queryset = self.select_expanded_fields(queryset)
        else:
            queryset = queryset.select_related("monitoring_site").prefetch_related(
                "datastream_tags", "datastream_file_attachments"
            )
        queryset = principal.annotate_permissions(queryset)

        try:
            datastream = queryset.get()
        except Datastream.DoesNotExist:
            raise HttpError(404 if not raise_400 else 400, "Datastream does not exist")

        if not principal.can_view(datastream):
            raise HttpError(404 if not raise_400 else 400, "Datastream does not exist")

        if action != "view" and not getattr(principal, f"can_{action}")(datastream):
            raise HttpError(
                403 if not raise_400 else 400,
                f"You do not have permission to {action} this datastream",
            )

        return datastream

    @staticmethod
    def select_expanded_fields(queryset: QuerySet) -> QuerySet:
        return queryset.select_related(
            "monitoring_site__workspace",
            "monitoring_site",
            "method",
            "observed_property",
            "unit",
            "processing_level",
        ).prefetch_related("datastream_tags", "datastream_file_attachments")

    @staticmethod
    def apply_tag_filter(queryset, tags: list[str]):
        if not tags:
            return queryset

        for tag in tags:
            if ":" not in tag:
                raise ValueError(f"Invalid tag format: '{tag}'. Must be 'key:value'.")

            key, value = tag.split(":", 1)

            queryset = queryset.filter(datastream_tags__key=key, datastream_tags__value=value)

        return queryset.distinct()

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_by: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        expand_related: Optional[bool] = None,
    ):
        queryset = Datastream.objects

        for field in [
            "monitoring_site__workspace_id",
            "monitoring_site_id",
            "method_id",
            "observed_property_id",
            "processing_level_id",
            "unit_id",
            "observations__result_qualifier_id",
            "observation_type",
            "sampled_medium",
            "status",
            "result_type",
            "is_private",
            "value_count__lte",
            "value_count__gte",
            "phenomenon_begin_time__lte",
            "phenomenon_begin_time__gte",
            "phenomenon_end_time__lte",
            "phenomenon_end_time__gte",
            "result_begin_time__lte",
            "result_begin_time__gte",
            "result_end_time__lte",
            "result_end_time__gte",
        ]:
            if field in filtering:
                if field == "is_private":
                    queryset = self.apply_filters(
                        queryset, f"is_private", filtering[field]
                    )
                    queryset = self.apply_filters(
                        queryset, f"monitoring_site__is_private", filtering[field]
                    )
                    queryset = self.apply_filters(
                        queryset, f"monitoring_site__workspace__is_private", filtering[field]
                    )
                elif field == "observations__result_qualifier_id":
                    queryset = Datastream.objects.none()
                else:
                    queryset = self.apply_filters(queryset, field, filtering[field])

        queryset = self.apply_tag_filter(queryset, filtering.get("tag"))

        if order_by:
            queryset = self.apply_ordering(
                queryset,
                order_by,
                list(get_args(DatastreamOrderByFields)),
            )
        else:
            queryset = queryset.order_by("id")

        if expand_related:
            queryset = self.select_expanded_fields(queryset)
        else:
            queryset = queryset.select_related("monitoring_site").prefetch_related(
                "datastream_tags", "datastream_file_attachments"
            )

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return [
            (
                DatastreamDetailResponse.model_validate(datastream)
                if expand_related
                else DatastreamSummaryResponse.model_validate(datastream)
            )
            for datastream in queryset.all()
        ]

    def list_visualization_bootstrap(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        filtering: Optional[dict] = None,
    ) -> dict[str, Sequence[dict]]:
        filtering = filtering or {}
        queryset = principal.filter_by_permission(Datastream.objects, "can_view")

        if "monitoring_site__workspace_id" in filtering:
            queryset = self.apply_filters(
                queryset,
                "monitoring_site__workspace_id",
                filtering["monitoring_site__workspace_id"],
            )

        datastream_rows = list(
            queryset.select_related("monitoring_site", "observed_property", "processing_level")
            .order_by("id")
            .values(
                "id",
                "name",
                "monitoring_site_id",
                "monitoring_site__workspace_id",
                "monitoring_site__name",
                "monitoring_site__code",
                "observed_property_id",
                "observed_property__name",
                "observed_property__code",
                "processing_level_id",
                "processing_level__definition",
                "unit_id",
                "no_data_value",
                "value_count",
                "phenomenon_begin_time",
                "phenomenon_end_time",
                "intended_time_spacing",
                "intended_time_spacing_unit",
            )
            .distinct()
        )

        monitoring_sites_by_id: dict[str, dict] = {}
        observed_properties_by_id: dict[str, dict] = {}
        processing_levels_by_id: dict[str, dict] = {}
        datastreams: list[dict] = []

        for row in datastream_rows:
            monitoring_site_id = str(row["monitoring_site_id"])
            observed_property_id = str(row["observed_property_id"])
            processing_level_id = str(row["processing_level_id"])

            monitoring_sites_by_id.setdefault(
                monitoring_site_id,
                {
                    "id": monitoring_site_id,
                    "workspace_id": str(row["monitoring_site__workspace_id"]),
                    "name": row["monitoring_site__name"],
                    "code": row["monitoring_site__code"],
                },
            )
            observed_properties_by_id.setdefault(
                observed_property_id,
                {
                    "id": observed_property_id,
                    "name": row["observed_property__name"],
                    "code": row["observed_property__code"],
                },
            )
            processing_levels_by_id.setdefault(
                processing_level_id,
                {
                    "id": processing_level_id,
                    "definition": row["processing_level__definition"],
                },
            )
            datastreams.append(
                {
                    "id": str(row["id"]),
                    "name": row["name"],
                    "monitoring_site_id": monitoring_site_id,
                    "observed_property_id": observed_property_id,
                    "processing_level_id": processing_level_id,
                    "unit_id": str(row["unit_id"]),
                    "no_data_value": row["no_data_value"],
                    "value_count": row["value_count"],
                    "phenomenon_begin_time": row["phenomenon_begin_time"],
                    "phenomenon_end_time": row["phenomenon_end_time"],
                    "intended_time_spacing": row["intended_time_spacing"],
                    "intended_time_spacing_unit": row["intended_time_spacing_unit"],
                }
            )

        return {
            "monitoring_sites": list(monitoring_sites_by_id.values()),
            "datastreams": datastreams,
            "observed_properties": list(observed_properties_by_id.values()),
            "processing_levels": list(processing_levels_by_id.values()),
        }

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        expand_related: Optional[bool] = None,
    ):
        datastream = self.get_datastream_for_action(
            principal=principal, uid=uid, action="view", expand_related=expand_related
        )

        return (
            DatastreamDetailResponse.model_validate(datastream)
            if expand_related
            else DatastreamSummaryResponse.model_validate(datastream)
        )

    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: DatastreamPostBody,
        expand_related: Optional[bool] = None,
    ):
        monitoring_site = self.handle_http_404_error(
            monitoring_site_service.get, principal=principal, uid=data.monitoring_site_id
        )
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=monitoring_site.workspace_id
        )

        if not principal.can_create("Datastream", workspace=workspace):
            raise HttpError(403, "You do not have permission to create this datastream")

        observed_property = self.handle_http_404_error(
            observed_property_service.get,
            principal=principal,
            uid=data.observed_property_id,
        )
        if observed_property.workspace_id not in (
            monitoring_site.workspace_id,
            None,
        ):
            raise HttpError(
                400,
                "The given observed property cannot be associated with this datastream",
            )

        processing_level = self.handle_http_404_error(
            processing_level_service.get,
            principal=principal,
            uid=data.processing_level_id,
        )
        if processing_level.workspace_id not in (
            monitoring_site.workspace_id,
            None,
        ):
            raise HttpError(
                400,
                "The given processing level cannot be associated with this datastream",
            )

        method = self.handle_http_404_error(
            method_service.get, principal=principal, uid=data.method_id
        )
        if method.workspace_id not in (
            monitoring_site.workspace_id,
            None,
        ):
            raise HttpError(
                400, "The given method cannot be associated with this datastream"
            )

        unit = self.handle_http_404_error(
            unit_service.get, principal=principal, uid=data.unit_id
        )
        if unit.workspace_id not in (
            monitoring_site.workspace_id,
            None,
        ):
            raise HttpError(
                400, "The given unit cannot be associated with this datastream"
            )

        try:
            datastream = Datastream.objects.create(
                pk=data.id,
                **data.dict(include=set(DatastreamPostBody.model_fields.keys()) - {"tags"})
            )
        except IntegrityError:
            raise HttpError(409, "The operation could not be completed due to a resource conflict.")

        if data.tags:
            keys = [tag.key for tag in data.tags]
            if len(keys) != len(set(keys)):
                raise HttpError(400, "Duplicate tag keys are not allowed")
            DatastreamTag.objects.bulk_create([
                DatastreamTag(datastream=datastream, key=tag.key, value=tag.value)
                for tag in data.tags
            ])

        return self.get(
            principal=principal, uid=datastream.id, expand_related=expand_related
        )

    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data: DatastreamPatchBody,
        expand_related: Optional[bool] = None,
    ):
        datastream = self.get_datastream_for_action(
            principal=principal, uid=uid, action="edit"
        )
        datastream_data = data.dict(
            include=set(DatastreamPatchBody.model_fields.keys()), exclude_unset=True
        )

        monitoring_site = (
            self.handle_http_404_error(
                monitoring_site_service.get, principal=principal, uid=data.monitoring_site_id
            )
            if data.monitoring_site_id
            else None
        )
        if monitoring_site and monitoring_site.workspace_id != datastream.monitoring_site.workspace_id:
            raise HttpError(
                400,
                "You cannot associate this datastream with a monitoring_site in another workspace",
            )

        observed_property = (
            self.handle_http_404_error(
                observed_property_service.get,
                principal=principal,
                uid=data.observed_property_id,
            )
            if data.observed_property_id
            else None
        )
        if observed_property and observed_property.workspace_id not in (
            datastream.monitoring_site.workspace_id,
            None,
        ):
            raise HttpError(
                400,
                "The given observed property cannot be associated with this datastream",
            )

        processing_level = (
            self.handle_http_404_error(
                processing_level_service.get,
                principal=principal,
                uid=data.processing_level_id,
            )
            if data.processing_level_id
            else None
        )
        if processing_level and processing_level.workspace_id not in (
            datastream.monitoring_site.workspace_id,
            None,
        ):
            raise HttpError(
                400,
                "The given processing level cannot be associated with this datastream",
            )

        method = (
            self.handle_http_404_error(
                method_service.get, principal=principal, uid=data.method_id
            )
            if data.method_id
            else None
        )
        if method and method.workspace_id not in (
            datastream.monitoring_site.workspace_id,
            None,
        ):
            raise HttpError(
                400, "The given method cannot be associated with this datastream"
            )

        unit = (
            self.handle_http_404_error(
                unit_service.get, principal=principal, uid=data.unit_id
            )
            if data.unit_id
            else None
        )
        if unit and unit.workspace_id not in (
            datastream.monitoring_site.workspace_id,
            None,
        ):
            raise HttpError(
                400, "The given unit cannot be associated with this datastream"
            )

        for field, value in datastream_data.items():
            setattr(datastream, field, value)

        datastream.save()

        return self.get(
            principal=principal, uid=datastream.id, expand_related=expand_related
        )

    def delete(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID):
        datastream = self.get_datastream_for_action(
            principal=principal, uid=uid, action="delete", expand_related=True
        )
        datastream.delete()

        return "Datastream deleted"

    def get_tags(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID):
        datastream = self.get_datastream_for_action(
            principal=principal, uid=uid, action="view"
        )

        return datastream.datastream_tags.all()

    @staticmethod
    def get_tag_keys(
        principal: User | ServiceAccount | AnonymousPrincipal,
        workspace_id: Optional[uuid.UUID],
        datastream_id: Optional[uuid.UUID],
    ):
        queryset = DatastreamTag.objects.filter(
            datastream__in=principal.filter_by_permission(Datastream.objects, "can_view")
        )

        if workspace_id:
            queryset = queryset.filter(datastream__monitoring_site__workspace_id=workspace_id)

        if datastream_id:
            queryset = queryset.filter(datastream_id=datastream_id)

        tags = queryset.values("key").annotate(values=ArrayAgg(F("value"), distinct=True))

        return {entry["key"]: entry["values"] for entry in tags}

    def add_tag(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID, data: TagPostBody):
        datastream = self.get_datastream_for_action(
            principal=principal, uid=uid, action="edit"
        )

        if DatastreamTag.objects.filter(datastream=datastream, key=data.key).exists():
            raise HttpError(400, "Tag already exists")

        return DatastreamTag.objects.create(
            datastream=datastream, key=data.key, value=data.value
        )

    def update_tag(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID, data: TagPostBody):
        datastream = self.get_datastream_for_action(
            principal=principal, uid=uid, action="edit"
        )

        try:
            tag = DatastreamTag.objects.get(datastream=datastream, key=data.key)
        except DatastreamTag.DoesNotExist:
            raise HttpError(404, "Tag does not exist")

        tag.value = data.value
        tag.save()

        return tag

    def remove_tag(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID, data: TagDeleteBody):
        datastream = self.get_datastream_for_action(
            principal=principal, uid=uid, action="edit"
        )

        queryset = DatastreamTag.objects.filter(datastream=datastream, key=data.key)

        if data.value is not None:
            queryset = queryset.filter(value=data.value)

        deleted_count, _ = queryset.delete()

        if deleted_count == 0:
            raise HttpError(404, "Tag does not exist")

        return f"{deleted_count} tag(s) deleted"

    def get_file_attachments(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        filtering: Optional[dict] = None,
    ):
        datastream = self.get_datastream_for_action(
            principal=principal, uid=uid, action="view"
        )

        queryset = datastream.datastream_file_attachments

        if filtering.get("file_attachment_type"):
            queryset = self.apply_filters(queryset, "file_attachment_type", filtering["file_attachment_type"])

        return queryset.all()

    def add_file_attachment(
        self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID, file, data: FileAttachmentPostBody
    ):
        datastream = self.get_datastream_for_action(
            principal=principal, uid=uid, action="edit"
        )

        if DatastreamFileAttachment.objects.filter(
            datastream=datastream, name=file.name
        ).exists():
            raise HttpError(400, "File attachment already exists")

        return DatastreamFileAttachment.objects.create(
            datastream=datastream,
            name=file.name,
            description=data.description,
            file_attachment=file,
            file_attachment_type=data.file_attachment_type,
        )

    def replace_file_attachment(
        self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID, file, data: FileAttachmentPostBody
    ):
        self.remove_file_attachment(
            principal=principal, uid=uid, data=FileAttachmentDeleteBody(name=file.name)
        )

        return self.add_file_attachment(
            principal=principal, uid=uid, file=file, data=data
        )

    def remove_file_attachment(
        self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID, data: FileAttachmentDeleteBody
    ):
        datastream = self.get_datastream_for_action(
            principal=principal, uid=uid, action="edit"
        )

        try:
            file_attachment = DatastreamFileAttachment.objects.get(
                datastream=datastream, name=data.name
            )
        except DatastreamFileAttachment.DoesNotExist:
            raise HttpError(404, "File attachment does not exist")

        file_attachment.file_attachment.delete()
        file_attachment.delete()

    def list_aggregation_statistics(
        self,
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_desc: bool = False,
    ):
        queryset = DatastreamAggregation.objects.order_by(
            f"{'-' if order_desc else ''}name"
        )
        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return queryset.values_list("name", flat=True)

    def list_statuses(
        self,
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_desc: bool = False,
    ):
        queryset = DatastreamStatus.objects.order_by(f"{'-' if order_desc else ''}name")
        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return queryset.values_list("name", flat=True)

    def list_sampled_mediums(
        self,
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_desc: bool = False,
    ):
        queryset = SampledMedium.objects.order_by(f"{'-' if order_desc else ''}name")
        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return queryset.values_list("name", flat=True)

    def list_file_attachment_types(
        self,
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_desc: bool = False,
    ):
        queryset = FileAttachmentType.objects.order_by(
            f"{'-' if order_desc else ''}name"
        )
        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return queryset.values_list("name", flat=True)

    @staticmethod
    def generate_csv(datastream: Datastream, observations=None):
        if observations is None:
            observations = Observation.objects.filter(datastream=datastream).order_by(
                "phenomenon_time"
            )

        latitude = (
            round(datastream.monitoring_site.latitude, 6)
            if datastream.monitoring_site.latitude
            else "None"
        )
        longitude = (
            round(datastream.monitoring_site.longitude, 6)
            if datastream.monitoring_site.longitude
            else "None"
        )
        elevation_m = (
            round(datastream.monitoring_site.elevation_m, 6)
            if datastream.monitoring_site.elevation_m
            else "None"
        )

        yield (
            f"# =============================================================================\n"
            f"# Generated on: {timezone.now().isoformat()}\n"
            f"# \n"
            f"# Workspace:\n"
            f"# -------------------------------------\n"
            f"# Name: {datastream.monitoring_site.workspace.name}\n"
            f"# Owner: {datastream.monitoring_site.workspace.owner.name}\n"
            f"# Contact Email: {datastream.monitoring_site.workspace.owner.email}\n"
            f"#\n"
            f"# Site Information:\n"
            f"# -------------------------------------\n"
            f"# Name: {datastream.monitoring_site.name}\n"
            f"# Description: {datastream.monitoring_site.description}\n"
            f"# Code: {datastream.monitoring_site.code}\n"
            f"# Type: {datastream.monitoring_site.type}\n"
            f"#\n"
            f"# Location Information:\n"
            f"# -------------------------------------\n"
            f"# Latitude: {latitude}\n"
            f"# Longitude: {longitude}\n"
            f"# Elevation_m: {elevation_m}\n"
            f"# ElevationDatum: {datastream.monitoring_site.elevation_datum}\n"
            f"# State: {datastream.monitoring_site.admin_area_1}\n"
            f"# County: {datastream.monitoring_site.admin_area_2}\n"
            f"#\n"
            f"# Datastream Information:\n"
            f"# -------------------------------------\n"
            f"# Name: {datastream.name}\n"
            f"# Description: {datastream.description}\n"
            f"# ObservationType: {datastream.observation_type}\n"
            f"# ResultType: {datastream.result_type}\n"
            f"# Status: {datastream.status}\n"
            f"# SampledMedium: {datastream.sampled_medium}\n"
            f"# ValueCount: {datastream.value_count}\n"
            f"# NoDataValue: {datastream.no_data_value}\n"
            f"# IntendedTimeSpacing: {datastream.intended_time_spacing}\n"
            f"# IntendedTimeSpacingUnit: {datastream.intended_time_spacing_unit}\n"
            f"# AggregationStatistic: {datastream.aggregation_statistic}\n"
            f"# TimeAggregationInterval: {datastream.time_aggregation_interval}\n"
            f"# TimeAggregationIntervalUnit: {datastream.time_aggregation_interval_unit}\n"
            f"#\n"
            f"# Method Information:\n"
            f"# -------------------------------------\n"
            f"# Name: {datastream.method.name}\n"
            f"# Description: {datastream.method.description}\n"
            f"# Code: {datastream.method.code}\n"
            f"# Type: {datastream.method.type}\n"
            f"# Definition: {datastream.method.definition}\n"
            f"# SensorModelManufacturer: {datastream.method.sensor_model_manufacturer}\n"
            f"# SensorModel: {datastream.method.sensor_model}\n"
            f"# SensorModelDefinition: {datastream.method.sensor_model_definition}\n"
            f"#\n"
            f"# Observed Property Information:\n"
            f"# -------------------------------------\n"
            f"# Name: {datastream.observed_property.name}\n"
            f"# Definition: {datastream.observed_property.definition}\n"
            f"# Description: {datastream.observed_property.description}\n"
            f"# VariableType: {datastream.observed_property.observed_property_type}\n"
            f"# VariableCode: {datastream.observed_property.code}\n"
            f"#\n"
            f"# Unit Information:\n"
            f"# -------------------------------------\n"
            f"# Name: {datastream.unit.name}\n"
            f"# Symbol: {datastream.unit.symbol}\n"
            f"# Definition: {datastream.unit.definition}\n"
            f"# UnitType: {datastream.unit.unit_type}\n"
            f"#\n"
            f"# Processing Level Information:\n"
            f"# -------------------------------------\n"
            f"# Code: {datastream.processing_level.code}\n"
            f"# Definition: {datastream.processing_level.definition}\n"
            f"# Explanation: {datastream.processing_level.explanation}\n"
            f"#\n"
            f"# Data Disclaimer:\n"
            f"# -------------------------------------\n"
            f"# Output date/time values are in UTC unless they were input to HydroServer without time zone offset information. In that case, date/time values are output as they were supplied to HydroServer.\n"
            f"# {datastream.monitoring_site.data_disclaimer if datastream.monitoring_site.data_disclaimer else ''}\n"
            f"# =============================================================================\n"
        )

        yield "ResultTime,Result,ResultQualifiers\n"

        for observation in observations.values_list(
            "phenomenon_time", "result", "quality_code"
        ):
            if observation[2]:
                yield f'{observation[0].isoformat()},{observation[1]},"{observation[2]}"\n'
            else:
                yield f"{observation[0].isoformat()},{observation[1]},\n"

    def get_csv(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID):
        datastream = self.get_datastream_for_action(
            principal=principal, uid=uid, action="view"
        )
        visible_observations = principal.filter_by_permission(
            Observation.objects, "can_view"
        ).filter(
            datastream=datastream
        ).order_by("phenomenon_time")

        response = StreamingHttpResponse(
            self.generate_csv(datastream, observations=visible_observations),
            content_type="text/csv",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{datastream.name}.csv"'
        )

        return response

    @staticmethod
    def update_observation_statistics(
        datastream: Datastream,
        fields: Sequence[
            Literal[
                "phenomenon_begin_time",
                "phenomenon_end_time",
                "result_begin_time",
                "result_end_time",
                "value_count",
            ]
        ],
    ) -> None:
        aggregations = {}

        if "phenomenon_begin_time" in fields:
            aggregations["phenomenon_begin_time"] = Min("phenomenon_time")
        if "phenomenon_end_time" in fields:
            aggregations["phenomenon_end_time"] = Max("phenomenon_time")
        if "result_begin_time" in fields:
            aggregations["result_begin_time"] = Min("result_time")
        if "result_end_time" in fields:
            aggregations["result_end_time"] = Max("result_time")
        if "value_count" in fields:
            aggregations["value_count"] = Count("id")

        if not aggregations:
            return

        aggregate = Observation.objects.filter(datastream=datastream).aggregate(
            **aggregations
        )

        if "phenomenon_begin_time" in fields:
            datastream.phenomenon_begin_time = aggregate.get("phenomenon_begin_time")
        if "phenomenon_end_time" in fields:
            datastream.phenomenon_end_time = aggregate.get("phenomenon_end_time")
        if "result_begin_time" in fields:
            datastream.result_begin_time = aggregate.get("result_begin_time")
        if "result_end_time" in fields:
            datastream.result_end_time = aggregate.get("result_end_time")
        if "value_count" in fields:
            datastream.value_count = aggregate.get("value_count")

        datastream.save()
