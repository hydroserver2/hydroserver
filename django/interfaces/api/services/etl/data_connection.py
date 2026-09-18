import uuid

from datetime import datetime
from typing import Optional, Literal, Union, Annotated, get_args

from pydantic import Field, ConfigDict, validate_call
from django.db import IntegrityError, transaction
from django.db.models import Count, Subquery, OuterRef, IntegerField
from django.db.models.functions import Coalesce
from django.db.models.query import QuerySet
from django.contrib.auth import get_user_model
from django.utils import timezone as django_tz

from core.types import Unset
from core.iam.models import ServiceAccount, Workspace
from core.iam.permissions.anonymous import AnonymousPrincipal
from interfaces.api.http.errors import BadRequestError, PermissionDeniedError, NotFoundError
from interfaces.api.service import APIService
from processing.orchestration.attention import attention_filter, latest_run_status_subquery
from processing.orchestration.services import SchedulingService
from processing.etl.models import (
    DataConnection, EtlTask, Payload, PlaceholderVariable,
    DataConnectionNotification, DataConnectionNotificationRecipient,
)
from interfaces.api.schemas.etl.data_connection import (
    DATA_CONNECTION_INCLUDE_RELATIONS,
    DataConnectionSortByFields,
    DataConnectionResponse,
)


User = get_user_model()

ETL_NOTIFICATION_CELERY_TASK = "processing.etl.tasks.send_etl_notification_email"


class DataConnectionAPIService(SchedulingService, APIService):

    INCLUDE_RELATIONS = DATA_CONNECTION_INCLUDE_RELATIONS

    @classmethod
    def _include_query_hints(cls, requested_includes: set[str]) -> list[str]:
        return [cls.INCLUDE_RELATIONS[name]["path"] for name in requested_includes]

    @staticmethod
    def annotate_task_counts(queryset: QuerySet) -> QuerySet:
        now = django_tz.now()
        task_count_subquery = Coalesce(
            Subquery(
                EtlTask.objects
                .filter(data_connection_id=OuterRef("pk"))
                .values("data_connection_id")
                .annotate(count=Count("pk"))
                .values("count"),
                output_field=IntegerField()
            ),
            0
        )
        attention_count_subquery = Coalesce(
            Subquery(
                EtlTask.objects
                .filter(data_connection_id=OuterRef("pk"))
                .annotate(latest_run_status=latest_run_status_subquery())
                .filter(attention_filter(now))
                .values("data_connection_id")
                .annotate(count=Count("pk"))
                .values("count"),
                output_field=IntegerField()
            ),
            0
        )
        # NOTE: task_count uses a scalar subquery rather than Count("etl_tasks", distinct=True).
        # The aggregate form joins every related EtlTask row and adds a GROUP BY, which causes
        # the correlated attention subquery to be evaluated once per joined task row instead of
        # once per data connection (turning ~5 evaluations into thousands).
        return queryset.annotate(
            task_count=task_count_subquery,
            task_attention_count=attention_count_subquery,
        )

    sortby_aliases = {
        "timestampKey": "payload__timestamp_key",
        "timestampFormat": "payload__timestamp_format",
        "workspaceName": "workspace__name",
    }

    @staticmethod
    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get(
        data_connection: uuid.UUID | DataConnection,
        action: Literal["view", "edit", "delete"] = "view",
        principal: User | ServiceAccount | AnonymousPrincipal | Unset = Unset,
    ) -> DataConnection:
        if isinstance(data_connection, uuid.UUID):
            try:
                queryset = DataConnection.objects.select_related("payload").filter(pk=data_connection)
                if principal is not Unset:
                    queryset = principal.annotate_permissions(queryset)
                data_connection = queryset.get()
            except DataConnection.DoesNotExist:
                raise NotFoundError(f"Data connection with ID {str(data_connection)} does not exist.")

        if principal is not Unset:
            if not principal.can_view(data_connection):
                raise NotFoundError(f"Data connection with ID {str(data_connection.id)} does not exist.")

            if action != "view" and not getattr(principal, f"can_{action}")(data_connection):
                raise PermissionDeniedError(f"You do not have permission to {action} this data connection.")

        return data_connection

    def get_item(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        data_connection = self.get(data_connection=uid, action="view", principal=principal)

        queryset = self.annotate_task_counts(
            DataConnection.objects.select_related("payload").prefetch_related("placeholder_variables")
        )
        if requested_includes:
            queryset = queryset.select_related(*self._include_query_hints(requested_includes))
        data_connection = queryset.get(pk=data_connection.pk)

        return {
            "data": DataConnectionResponse.model_validate(data_connection),
            "included": self.resolve_includes(
                [data_connection], requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        sortby: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        filtering = filtering or {}

        queryset = DataConnection.objects

        if "workspace" in filtering:
            queryset = self.apply_filters(queryset, "workspace_id", filtering["workspace"])

        if "payload_type" in filtering:
            queryset = self.apply_filters(queryset, "payload__payload_type", filtering["payload_type"])

        queryset, has_search = self.apply_search(queryset, filtering.get("q"))
        queryset = self.apply_sorting(
            queryset,
            sortby,
            list(get_args(DataConnectionSortByFields)),
            self.sortby_aliases,
            rank=has_search,
        )

        queryset = queryset.prefetch_related("placeholder_variables", "payload")
        if requested_includes:
            queryset = queryset.select_related(*self._include_query_hints(requested_includes))

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()

        # Count before adding the task-count annotations so the COUNT(*) query does not have to
        # evaluate the per-connection task subqueries (they do not affect the row count).
        count = queryset.count()

        queryset = self.annotate_task_counts(queryset)
        queryset, meta = self.apply_pagination(queryset, offset, limit, count=count)

        connections = list(queryset.all())

        return {
            "data": [DataConnectionResponse.model_validate(c) for c in connections],
            "meta": meta,
            "included": self.resolve_includes(
                connections, requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        name: str,
        workspace: uuid.UUID | Workspace,
        source_url: str,
        payload_type: Literal["CSV", "JSON"],
        timestamp_key: str,
        uid: uuid.UUID = Field(default_factory=uuid.uuid7),
        description: str | None = None,
        auth_header_name: str | None = None,
        auth_header_value: str | None = None,
        timestamp_format: str | None = None,
        timezone_type: Literal["offset", "iana"] | None = None,
        timezone: str | None = None,
        header_row: int | None | Unset = Field(Unset, gt=0),
        data_start_row: int | Unset = Field(Unset, gt=0),
        delimiter: Literal[",", "|", "\t", ";", " "] | Unset = Field(Unset, min_length=1, max_length=1),
        jmespath: str | Unset = Unset,
        placeholder_variables: list[dict] | Unset = Unset,
        notification_recipient_emails: list[str] | Unset = Unset,
        notification_crontab: Union[Optional[str], Unset] = Unset,
        notification_interval: Union[Optional[int], Unset] = Unset,
        notification_interval_period: Union[Optional[Literal["minutes", "hours", "days"]], Unset] = Unset,
        notification_start_time: Union[Optional[datetime], Unset] = Unset,
        notification_enabled: Union[bool, Unset] = Unset,
    ) -> dict:
        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=getattr(workspace, "pk", workspace)
        )

        if not principal.can_create("DataConnection", workspace=workspace):
            raise PermissionDeniedError("You do not have permission to create this data connection.")

        data_connection = DataConnection(
            pk=uid,
            workspace=workspace,
            name=name,
            description=description,
            source_url=source_url,
            auth_header_name=auth_header_name,
            auth_header_value=auth_header_value,
            timezone_type=timezone_type,
            timezone=timezone,
        )
        data_connection.full_clean()

        try:
            data_connection.save()
        except IntegrityError:
            raise IntegrityError("The operation could not be completed due to a resource conflict.")

        self.apply_payload(
            data_connection=data_connection,
            payload_type=payload_type,
            timestamp_key=timestamp_key,
            timestamp_format=timestamp_format,
            header_row=header_row,
            data_start_row=data_start_row,
            delimiter=delimiter,
            jmespath=jmespath,
        )

        if placeholder_variables is not Unset:
            self.apply_placeholders(
                data_connection=data_connection,
                placeholder_variables=placeholder_variables,
            )

        if notification_recipient_emails is not Unset:
            self.apply_notification(
                data_connection=data_connection,
                recipient_emails=notification_recipient_emails,
                crontab=notification_crontab,
                interval=notification_interval,
                interval_period=notification_interval_period,
                start_time=notification_start_time,
                enabled=notification_enabled,
            )

        return {"id": data_connection.pk}

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def update(
        self,
        data_connection: uuid.UUID | DataConnection,
        principal: User | ServiceAccount | AnonymousPrincipal,
        name: str | Unset = Unset,
        source_url: str | Unset = Unset,
        auth_header_name: str | None | Unset = Unset,
        auth_header_value: str | None | Unset = Unset,
        payload_type: Literal["CSV", "JSON"] | Unset = Unset,
        timestamp_key: str | Unset = Unset,
        description: str | None | Unset = Unset,
        timestamp_format: str | None | Unset = Unset,
        timezone_type: Literal["offset", "iana"] | None | Unset = Unset,
        timezone: str | None | Unset = Unset,
        header_row: int | None | Unset = Field(Unset, gt=0),
        data_start_row: int | Unset = Field(Unset, gt=0),
        delimiter: str | Unset = Field(Unset, min_length=1, max_length=1),
        jmespath: str | Unset = Unset,
        placeholder_variables: list[dict] | Unset = Unset,
        notification_recipient_emails: list[str] | Unset = Unset,
        notification_crontab: Union[Optional[str], Unset] = Unset,
        notification_interval: Union[Optional[int], Unset] = Unset,
        notification_interval_period: Union[Optional[Literal["minutes", "hours", "days"]], Unset] = Unset,
        notification_start_time: Union[Optional[datetime], Unset] = Unset,
        notification_enabled: Union[bool, Unset] = Unset,
    ) -> None:
        data_connection = self.get(
            data_connection=data_connection,
            action="edit",
            principal=principal
        )

        if any(field is not Unset for field in [payload_type, timestamp_key, timestamp_format,
                                                header_row, data_start_row, delimiter, jmespath]):
            resolved_payload_type = payload_type if payload_type is not Unset else data_connection.payload.payload_type
            self.apply_payload(
                data_connection=data_connection,
                payload_type=resolved_payload_type,
                timestamp_key=timestamp_key,
                timestamp_format=timestamp_format,
                header_row=header_row,
                data_start_row=data_start_row,
                delimiter=delimiter,
                jmespath=jmespath,
            )

        if placeholder_variables is not Unset:
            self.apply_placeholders(
                data_connection=data_connection,
                placeholder_variables=placeholder_variables,
            )

        if notification_recipient_emails is not Unset:
            self.apply_notification(
                data_connection=data_connection,
                recipient_emails=notification_recipient_emails,
                crontab=notification_crontab,
                interval=notification_interval,
                interval_period=notification_interval_period,
                start_time=notification_start_time,
                enabled=notification_enabled,
            )

        editable_fields = {
            "name": name, "source_url": source_url, "description": description,
            "auth_header_name": auth_header_name, "auth_header_value": auth_header_value,
            "timezone_type": timezone_type, "timezone": timezone,
        }

        for field, value in editable_fields.items():
            if value is not Unset:
                setattr(data_connection, field, value)

        data_connection.full_clean()
        data_connection.save()

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def delete(
        self,
        data_connection: uuid.UUID | DataConnection,
        principal: User | ServiceAccount | AnonymousPrincipal,
    ) -> None:
        data_connection = self.get(
            data_connection=data_connection,
            action="delete",
            principal=principal
        )

        data_connection.delete()

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def apply_payload(
        self,
        data_connection: uuid.UUID | DataConnection,
        payload_type: Literal["CSV", "JSON"],
        timestamp_key: str | Unset = Unset,
        timestamp_format: str | None | Unset = Unset,
        header_row: Annotated[int | None, Field(gt=0)] | Unset = Unset,
        data_start_row: Annotated[int, Field(gt=0)] | Unset = Unset,
        delimiter: Annotated[str, Field(min_length=1, max_length=1)] | Unset = Unset,
        jmespath: str | Unset = Unset,
    ):
        data_connection = self.get(data_connection)

        try:
            current_payload = data_connection.payload
        except Payload.DoesNotExist:
            current_payload = None

        if current_payload and current_payload.payload_type != payload_type:
            current_payload.delete()
            current_payload = None

        if payload_type == "CSV":
            fields = {
                "payload_type": payload_type,
                "timestamp_key": timestamp_key,
                "timestamp_format": timestamp_format,
                "header_row": header_row,
                "data_start_row": data_start_row,
                "delimiter": delimiter,
                "jmespath": None,
            }
        elif payload_type == "JSON":
            fields = {
                "payload_type": payload_type,
                "timestamp_key": timestamp_key,
                "timestamp_format": timestamp_format,
                "header_row": None,
                "data_start_row": None,
                "delimiter": None,
                "jmespath": jmespath,
            }
        else:
            raise BadRequestError(f"Unsupported payload type {payload_type}")

        if current_payload:
            for field, value in fields.items():
                if value is not Unset:
                    setattr(current_payload, field, value)
            current_payload.full_clean()
            current_payload.save()
        else:
            new_payload = Payload(
                data_connection=data_connection,
                **{field: value for field, value in fields.items() if value is not Unset},
            )
            new_payload.full_clean()
            new_payload.save()
            data_connection.payload = new_payload

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def apply_placeholders(
        self,
        data_connection: uuid.UUID | DataConnection,
        placeholder_variables: list[dict],
    ):
        data_connection = self.get(data_connection)

        new_placeholders = {(pv["name"], pv["variable_type"]): pv for pv in placeholder_variables}
        current_placeholders = {(pv.name, pv.variable_type): pv for pv in data_connection.placeholder_variables.all()}

        data_connection.placeholder_variables.filter(
            pk__in=[pv.pk for key, pv in current_placeholders.items() if key not in new_placeholders]
        ).delete()

        for key, pv_data in new_placeholders.items():
            name, variable_type = key
            new_format = pv_data.get("timestamp_format")
            if key in current_placeholders:
                existing = current_placeholders[key]
                if existing.timestamp_format != new_format:
                    existing.timestamp_format = new_format
                    existing.full_clean()
                    existing.save()
            else:
                new_placeholder = PlaceholderVariable(
                    data_connection=data_connection,
                    name=name,
                    variable_type=variable_type,
                    timestamp_format=new_format,
                )
                new_placeholder.full_clean()
                new_placeholder.save()

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def apply_notification(
        self,
        data_connection: uuid.UUID | DataConnection,
        recipient_emails: list[str],
        crontab: Union[Optional[str], Unset] = Unset,
        interval: Union[Optional[int], Unset] = Unset,
        interval_period: Union[Optional[Literal["minutes", "hours", "days"]], Unset] = Unset,
        start_time: Union[Optional[datetime], Unset] = Unset,
        enabled: Union[bool, Unset] = Unset,
    ) -> DataConnectionNotification | None:
        data_connection = self.get(data_connection)

        try:
            notification = data_connection.notification
        except DataConnectionNotification.DoesNotExist:
            notification = None

        selected_recipients = set(recipient_emails)

        if not selected_recipients:
            if notification is not None:
                notification.delete()
            return None

        periodic_task = self.apply_schedule(
            periodic_task=notification.periodic_task if notification else None,
            crontab=crontab,
            interval=interval,
            interval_period=interval_period,
            start_time=start_time,
            enabled=enabled,
            celery_task_name=ETL_NOTIFICATION_CELERY_TASK,
            celery_task_kwargs={"data_connection_id": str(data_connection.pk)},
            periodic_task_name=str(data_connection.pk),
        )

        if notification is None:
            notification = DataConnectionNotification.objects.create(
                data_connection=data_connection,
                periodic_task=periodic_task,
            )
        else:
            notification.periodic_task = periodic_task
            notification.save()

        current_recipients = set(notification.recipients.values_list("email", flat=True))

        notification.recipients.filter(
            email__in=current_recipients - selected_recipients
        ).delete()

        for email in selected_recipients - current_recipients:
            DataConnectionNotificationRecipient.objects.create(notification=notification, email=email)

        notification.full_clean()

        return notification
