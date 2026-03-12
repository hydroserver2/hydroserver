import uuid
from typing import Optional, Literal, get_args
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import QuerySet
from domains.iam.models import APIKey
from domains.sta.models import Sensor, SensorEncodingType, MethodType
from interfaces.api.schemas import (
    SensorSummaryResponse,
    SensorDetailResponse,
    SensorPostBody,
    SensorPatchBody,
)
from interfaces.api.schemas.sensor import SensorFields, SensorOrderByFields
from interfaces.api.service import ServiceUtils

User = get_user_model()


class SensorService(ServiceUtils):
    def get_sensor_for_action(
        self,
        principal: User | APIKey,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        expand_related: Optional[bool] = None,
    ):
        try:
            sensor = Sensor.objects
            if expand_related:
                sensor = self.select_expanded_fields(sensor)
            sensor = sensor.get(pk=uid)
        except Sensor.DoesNotExist:
            raise HttpError(404, "Sensor does not exist")

        sensor_permissions = sensor.get_principal_permissions(principal=principal)

        if "view" not in sensor_permissions:
            raise HttpError(404, "Sensor does not exist")

        if action not in sensor_permissions:
            raise HttpError(403, f"You do not have permission to {action} this sensor")

        return sensor

    @staticmethod
    def select_expanded_fields(queryset: QuerySet) -> QuerySet:
        return queryset.select_related("workspace")

    def list(
        self,
        principal: Optional[User | APIKey],
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_by: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        expand_related: Optional[bool] = None,
    ):
        queryset = Sensor.objects

        for field in [
            "workspace_id",
            "datastreams__thing_id",
            "datastreams__id",
            "encoding_type",
            "manufacturer",
            "method_type",
        ]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        if order_by:
            queryset = self.apply_ordering(
                queryset,
                order_by,
                list(get_args(SensorOrderByFields)),
                {"model": "sensor_model"},
            )
        else:
            queryset = queryset.order_by("id")

        if expand_related:
            queryset = self.select_expanded_fields(queryset)

        queryset = queryset.visible(principal=principal).distinct()

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return [
            (
                SensorDetailResponse.model_validate(sensor)
                if expand_related
                else SensorSummaryResponse.model_validate(sensor)
            )
            for sensor in queryset.all()
        ]

    def get(
        self,
        principal: Optional[User | APIKey],
        uid: uuid.UUID,
        expand_related: Optional[bool] = None,
    ):
        sensor = self.get_sensor_for_action(
            principal=principal, uid=uid, action="view", expand_related=expand_related
        )

        return (
            SensorDetailResponse.model_validate(sensor)
            if expand_related
            else SensorSummaryResponse.model_validate(sensor)
        )

    def create(
        self,
        principal: User | APIKey,
        data: SensorPostBody,
        expand_related: Optional[bool] = None,
    ):
        workspace, _ = (
            self.get_workspace(principal=principal, workspace_id=data.workspace_id)
            if data.workspace_id
            else (
                None,
                None,
            )
        )

        if not Sensor.can_principal_create(principal=principal, workspace=workspace):
            raise HttpError(403, "You do not have permission to create this sensor")

        try:
            sensor = Sensor.objects.create(
                pk=data.id,
                workspace=workspace,
                **data.dict(include=set(SensorFields.model_fields.keys())),
            )
        except IntegrityError:
            raise HttpError(409, "The operation could not be completed due to a resource conflict.")

        return self.get(
            principal=principal, uid=sensor.id, expand_related=expand_related
        )

    def update(
        self,
        principal: User | APIKey,
        uid: uuid.UUID,
        data: SensorPatchBody,
        expand_related: Optional[bool] = None,
    ):
        sensor = self.get_sensor_for_action(principal=principal, uid=uid, action="edit")
        sensor_data = data.dict(
            include=set(SensorFields.model_fields.keys()), exclude_unset=True
        )

        for field, value in sensor_data.items():
            setattr(sensor, field, value)

        sensor.save()

        return self.get(
            principal=principal, uid=sensor.id, expand_related=expand_related
        )

    def delete(self, principal: User | APIKey, uid: uuid.UUID):
        sensor = self.get_sensor_for_action(
            principal=principal, uid=uid, action="delete"
        )

        if sensor.datastreams.exists():
            raise HttpError(409, "Sensor in use by one or more datastreams")

        sensor.delete()

        return "Sensor deleted"

    def list_method_types(
        self,
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_desc: bool = False,
    ):
        queryset = MethodType.objects.order_by(f"{'-' if order_desc else ''}name")
        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return queryset.values_list("name", flat=True)

    def list_encoding_types(
        self,
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_desc: bool = False,
    ):
        queryset = SensorEncodingType.objects.order_by(
            f"{'-' if order_desc else ''}name"
        )
        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return queryset.values_list("name", flat=True)
