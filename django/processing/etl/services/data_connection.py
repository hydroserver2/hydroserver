import uuid
import uuid6
from datetime import datetime
from typing import Optional, Literal, Union, Annotated

from pydantic import Field, ConfigDict, validate_call
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Subquery, OuterRef, IntegerField
from django.db.models.functions import Coalesce
from django.db.models.query import QuerySet
from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchVector, SearchQuery
from django.utils import timezone as django_tz

from hydroserverpy.etl.models import Timestamp

from core.types import Unset
from core.iam.models import APIKey, Workspace
from core.service import ServiceUtils
from processing.orchestration.models import TaskRun
from processing.orchestration.services import SchedulingService
from processing.etl.models import (
    DataConnection, EtlTask, Payload, PlaceholderVariable,
    DataConnectionNotification, DataConnectionNotificationRecipient,
)


User = get_user_model()

ETL_NOTIFICATION_CELERY_TASK = "processing.etl.tasks.send_etl_notification_email"


class DataConnectionService(SchedulingService, ServiceUtils):

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
                .annotate(
                    latest_run_status=Subquery(
                        TaskRun.objects
                        .filter(task_id=OuterRef("pk"))
                        .order_by("-started_at", "-id")
                        .values("status")[:1]
                    )
                )
                .filter(Q(latest_run_status="FAILURE") | Q(next_run_at__lt=now))
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

    order_by_fields = {"id", "name", "payload__timestamp_key", "payload__timestamp_format", "timezone_type", "timezone",
                       "workspace_id", "workspace__name"}

    @staticmethod
    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get(
        data_connection: uuid.UUID | DataConnection,
        action: Literal["view", "edit", "delete"] = "view",
        principal: User | APIKey | None | Unset = Unset,
    ) -> DataConnection:
        """
        Get a data connection.
        """

        if isinstance(data_connection, uuid.UUID):
            try:
                data_connection = DataConnection.objects.get(pk=data_connection)
            except DataConnection.DoesNotExist:
                raise LookupError(f"Data connection with ID {str(data_connection)} does not exist.")

        if principal is not Unset:
            permissions = data_connection.get_principal_permissions(principal=principal)

            if "view" not in permissions:
                raise LookupError(f"Data connection with ID {str(data_connection.id)} does not exist.")

            if action not in permissions:
                raise PermissionError(f"You do not have permission to {action} this data connection.")

        return data_connection

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get_collection(
        self,
        principal: User | APIKey | None = None,
        page: int = Field(gt=0, default=1),
        page_size: int = Field(gt=0, default=100),
        order_by: list[str] = Field(default_factory=list),
        search_term: str | Unset = Unset,
        workspace: list[uuid.UUID | Workspace] | Unset = Unset,
        payload_type: list[str] | Unset = Unset,
    ) -> tuple[int, QuerySet[DataConnection]]:
        """
        Return a collection of data connections.
        """

        queryset = DataConnection.objects

        if search_term is not Unset:
            search_vector = SearchVector(
                "name", "description", "workspace__name", "source_url",
                "timezone_type", "timezone"
            )
            queryset = queryset.annotate(search=search_vector).filter(search=SearchQuery(search_term))

        if workspace is not Unset:
            queryset = queryset.filter(workspace__in=[
                getattr(term, "pk", term) for term in workspace
            ])

        if payload_type is not Unset:
            queryset = queryset.filter(payload__payload_type__in=payload_type)

        if not all(term.lstrip("-") in self.order_by_fields for term in order_by):
            raise ValueError(f"Invalid order_by field(s): {order_by}")

        queryset = queryset.order_by(*order_by, "-id")
        queryset = queryset.select_related("workspace").prefetch_related("placeholder_variables", "payload")
        queryset = queryset.visible(principal=principal).distinct()

        # Count before adding the task-count annotations so the COUNT(*) query does not have to
        # evaluate the per-connection task subqueries (they do not affect the row count).
        count = queryset.count()
        offset = (page - 1) * page_size

        queryset = self.annotate_task_counts(queryset)
        queryset = queryset[offset:offset + page_size]

        return count, queryset

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def create(
        self,
        principal: User | APIKey | None,
        name: str,
        workspace: uuid.UUID | Workspace,
        source_url: str,
        payload_type: Literal["CSV", "JSON"],
        timestamp_key: str,
        uid: uuid.UUID = Field(default_factory=uuid6.uuid7),
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
        placeholder_variables: list[dict] = Field(default_factory=list),
        notification_recipient_emails: list[str] | Unset = Unset,
        notification_crontab: Union[Optional[str], Unset] = Unset,
        notification_interval: Union[Optional[int], Unset] = Unset,
        notification_interval_period: Union[Optional[Literal["minutes", "hours", "days"]], Unset] = Unset,
        notification_start_time: Union[Optional[datetime], Unset] = Unset,
        notification_enabled: Union[bool, Unset] = Unset,
    ) -> DataConnection:
        """
        Create a new data connection.
        """

        workspace, _ = self.get_workspace(
            principal=principal, workspace_id=getattr(workspace, "pk", workspace)
        )

        if not DataConnection.can_principal_create(principal=principal, workspace=workspace):
            raise PermissionError("You do not have permission to create this data connection.")

        if (auth_header_name is None) != (auth_header_value is None):
            raise ValueError("auth_header_name and auth_header_value must both be provided or both be omitted.")

        timestamp = Timestamp(
            timestamp_type="iso" if timestamp_format is None else "custom",
            timestamp_format=timestamp_format,
            timezone_type=timezone_type,
            timezone=timezone,
        )

        try:
            data_connection = DataConnection.objects.create(
                pk=uid,
                workspace=workspace,
                name=name,
                description=description,
                source_url=source_url,
                auth_header_name=auth_header_name,
                auth_header_value=auth_header_value,
                timezone_type=timestamp.timezone_type,
                timezone=timestamp.timezone
            )
        except IntegrityError:
            raise IntegrityError("The operation could not be completed due to a resource conflict.")

        self.apply_payload(
            data_connection=data_connection,
            payload_type=payload_type,
            timestamp_key=timestamp_key,
            timestamp_format=timestamp.timestamp_format,
            header_row=header_row,
            data_start_row=data_start_row,
            delimiter=delimiter,
            jmespath=jmespath,
        )

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

        return self.get(data_connection.pk)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def update(
        self,
        data_connection: uuid.UUID | DataConnection,
        principal: User | APIKey | None,
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
    ) -> DataConnection:
        """
        Update a data connection.
        """

        data_connection = self.get(
            data_connection=data_connection,
            action="edit",
            principal=principal
        )

        resolved_auth_header_name = auth_header_name \
            if auth_header_name is not Unset else data_connection.auth_header_name
        resolved_auth_header_value = auth_header_value \
            if auth_header_value is not Unset else data_connection.auth_header_value

        if (resolved_auth_header_name is None) != (resolved_auth_header_value is None):
            raise ValueError("auth_header_name and auth_header_value must both be provided or both be omitted.")

        if any(field is not Unset for field in [timestamp_format, timezone_type, timezone]):
            timestamp_type: Literal["iso", "custom"] = (
                "iso" if timestamp_format is None
                else "custom" if timestamp_format is not Unset
                else "custom" if data_connection.payload.timestamp_format is not None
                else "iso"
            )
            timestamp = Timestamp(
                timestamp_type=timestamp_type,
                timestamp_format=(
                    timestamp_format if timestamp_format is not Unset else data_connection.payload.timestamp_format
                ),
                timezone_type=(
                    timezone_type if timezone_type is not Unset else data_connection.timezone_type
                ),
                timezone=(
                    timezone if timezone is not Unset else data_connection.timezone
                ),
            )
            data_connection.timezone_type = timestamp.timezone_type
            data_connection.timezone = timestamp.timezone

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
        }

        for field, value in editable_fields.items():
            if value is not Unset:
                setattr(data_connection, field, value)

        data_connection.save()

        return self.get(data_connection.pk)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def delete(
        self,
        data_connection: uuid.UUID | DataConnection,
        principal: User | APIKey | None,
    ) -> None:
        """
        Delete a data connection.
        """

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
        """
        Create or update the payload settings attached to a data connection.
        """

        data_connection = self.get(data_connection)

        try:
            current_payload = data_connection.payload
        except Payload.DoesNotExist:
            current_payload = None

        if current_payload and current_payload.payload_type != payload_type:
            current_payload.delete()
            current_payload = None

        if not current_payload:
            if timestamp_key is Unset:
                raise ValueError("timestamp_key is required when creating a payload.")
            if payload_type == "CSV" and any(field is Unset for field in [header_row, data_start_row, delimiter]):
                raise ValueError("header_row, data_start_row, and delimiter are required when creating a CSV payload.")
            if payload_type == "JSON" and jmespath is Unset:
                raise ValueError("jmespath is required when creating a JSON payload.")

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
            raise NotImplementedError(f"Unsupported payload type {payload_type}")

        if current_payload:
            for field, value in fields.items():
                if value is not Unset:
                    setattr(current_payload, field, value)
            current_payload.save()
        else:
            data_connection.payload = Payload.objects.create(
                data_connection=data_connection,
                **fields
            )

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def apply_placeholders(
        self,
        data_connection: uuid.UUID | DataConnection,
        placeholder_variables: list[dict],
    ):
        """
        Replace placeholder variables on a data connection, preserving existing ones that match.
        """

        data_connection = self.get(data_connection)

        for pv in placeholder_variables:
            if pv.get("timestamp_format"):
                if pv.get("variable_type") not in ("run_time", "latest_observation_timestamp"):
                    raise ValueError(
                        "timestamp_format is only allowed on 'run_time' and 'latest_observation_timestamp' "
                        "placeholder variables."
                    )
                Timestamp._validate_strftime_format(pv["timestamp_format"])  # noqa

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
                    existing.save()
            else:
                PlaceholderVariable.objects.create(
                    data_connection=data_connection,
                    name=name,
                    variable_type=variable_type,
                    timestamp_format=new_format,
                )

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
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
        """
        Create, update, or delete the notification for a data connection.
        """

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

        if not periodic_task:
            raise ValueError("A schedule is required when recipient emails are provided.")

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

        return notification
