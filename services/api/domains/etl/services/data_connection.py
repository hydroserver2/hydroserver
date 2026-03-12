import uuid
from typing import Optional, Literal, get_args
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import QuerySet
from domains.iam.models import APIKey
from domains.etl.models import DataConnection
from interfaces.api.schemas import (
    DataConnectionSummaryResponse,
    DataConnectionDetailResponse,
    DataConnectionPostBody,
    DataConnectionPatchBody,
)
from interfaces.api.schemas.data_connection import (
    DataConnectionFields,
    DataConnectionOrderByFields,
)
from interfaces.api.service import ServiceUtils

User = get_user_model()


class DataConnectionService(ServiceUtils):

    def get_data_connection_for_action(
        self,
        principal: User | APIKey,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        expand_related: Optional[bool] = None,
        raise_400: bool = False,
    ):
        try:
            data_connection = DataConnection.objects
            if expand_related:
                data_connection = self.select_expanded_fields(data_connection)
            data_connection = data_connection.get(pk=uid)
        except DataConnection.DoesNotExist:
            raise HttpError(
                404 if not raise_400 else 400, "ETL Data Connection does not exist"
            )

        data_connection_permissions = (
            data_connection.get_principal_permissions(principal=principal)
        )

        if "view" not in data_connection_permissions:
            raise HttpError(
                404 if not raise_400 else 400, "ETL Data Connection does not exist"
            )

        if action not in data_connection_permissions:
            raise HttpError(
                403 if not raise_400 else 400,
                f"You do not have permission to {action} this ETL data connection",
            )

        return data_connection

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
        queryset = DataConnection.objects

        for field in [
            "workspace_id",
            "data_connection_type",
            "extractor_type",
            "transformer_type",
            "loader_type"
        ]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        if order_by:
            queryset = self.apply_ordering(
                queryset,
                order_by,
                list(get_args(DataConnectionOrderByFields)),
                {"type": "data_connection_type"},
            )
        else:
            queryset = queryset.order_by("id")

        if expand_related:
            queryset = self.select_expanded_fields(queryset)

        queryset = queryset.visible(principal=principal).distinct()

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return [
            (
                DataConnectionDetailResponse.model_validate(data_connection)
                if expand_related
                else DataConnectionSummaryResponse.model_validate(
                    data_connection
                )
            )
            for data_connection in queryset.all()
        ]

    def get(
        self,
        principal: Optional[User | APIKey],
        uid: uuid.UUID,
        expand_related: Optional[bool] = None,
    ):
        data_connection = self.get_data_connection_for_action(
            principal=principal, uid=uid, action="view", expand_related=expand_related
        )

        return (
            DataConnectionDetailResponse.model_validate(data_connection)
            if expand_related
            else DataConnectionSummaryResponse.model_validate(data_connection)
        )

    def create(
        self,
        principal: User | APIKey,
        data: DataConnectionPostBody,
    ):
        workspace, _ = (
            self.get_workspace(principal=principal, workspace_id=data.workspace_id)
            if data.workspace_id
            else (
                None,
                None,
            )
        )

        if not DataConnection.can_principal_create(
            principal=principal, workspace=workspace
        ):
            raise HttpError(
                403, "You do not have permission to create this ETL data connection"
            )

        try:
            data_connection = DataConnection.objects.create(
                pk=data.id,
                workspace=workspace,
                extractor_type=data.extractor.settings_type if data.extractor else None,
                extractor_settings=data.extractor.settings if data.extractor else {},
                transformer_type=data.transformer.settings_type if data.transformer else None,
                transformer_settings=data.transformer.settings if data.transformer else {},
                loader_type=data.loader.settings_type if data.loader else None,
                loader_settings=data.loader.settings if data.loader else {},
                **data.dict(include=set(DataConnectionFields.model_fields.keys())),
            )
        except IntegrityError:
            raise HttpError(409, "The operation could not be completed due to a resource conflict.")

        return self.get(
            principal=principal,
            uid=data_connection.id,
            expand_related=True,
        )

    def update(
        self,
        principal: User | APIKey,
        uid: uuid.UUID,
        data: DataConnectionPatchBody,
    ):
        data_connection = self.get_data_connection_for_action(
            principal=principal, uid=uid, action="edit"
        )
        data_connection_data = data.dict(
            include=set(DataConnectionFields.model_fields.keys() | {"extractor", "transformer", "loader"}),
            exclude_unset=True,
        )

        for field, value in data_connection_data.items():
            if field in ["extractor", "transformer", "loader"]:
                if "settings_type" in value:
                    setattr(data_connection, f"{field}_type", value["settings_type"])
                if "settings" in value:
                    setattr(data_connection, f"{field}_settings", value["settings"] or {})
            else:
                setattr(data_connection, field, value)

        data_connection.save()

        return self.get(
            principal=principal,
            uid=data_connection.id,
            expand_related=True,
        )

    def delete(self, principal: User | APIKey, uid: uuid.UUID):
        data_connection = self.get_data_connection_for_action(
            principal=principal, uid=uid, action="delete", expand_related=True
        )

        data_connection.delete()

        return "ETL Data Connection deleted"
