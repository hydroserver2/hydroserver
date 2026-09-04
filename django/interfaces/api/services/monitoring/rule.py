import uuid
from typing import Union, Literal

from pydantic import Field, ConfigDict, validate_call
from django.db import transaction
from django.db.models.query import QuerySet
from django.contrib.auth import get_user_model

from core.types import Unset
from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from interfaces.api.http.errors import BadRequestError, PermissionDeniedError, NotFoundError
from interfaces.api.service import APIService
from processing.monitoring.models import MonitoringTask, MonitoringRule


User = get_user_model()

RuleType = Literal["range", "rate_of_change", "persistence", "missing_data"]
WindowIntervalUnits = Literal["minutes", "hours", "days"]


class MonitoringRuleAPIService(APIService):

    order_by_fields = {"id", "rule_type", "datastream_id"}

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get(
        self,
        rule: Union[uuid.UUID, MonitoringRule],
        task: Union[uuid.UUID, MonitoringTask],
        action: Literal["view", "edit", "delete"] = "view",
        principal: User | ServiceAccount | AnonymousPrincipal | Unset = Unset,
    ) -> MonitoringRule:
        """
        Get a monitoring rule, scoped to the given task.
        """

        if isinstance(rule, uuid.UUID):
            try:
                rule = MonitoringRule.objects.select_related(
                    "task__monitoring_site__workspace",
                    "datastream",
                ).get(pk=rule, task=task)
            except MonitoringRule.DoesNotExist:
                raise NotFoundError(f"MonitoringRule with ID {str(rule)} does not exist.")

        if principal is not Unset:
            task_obj = principal.annotate_permissions(
                MonitoringTask.objects.filter(pk=rule.task_id)
            ).get()

            if not principal.can_view(task_obj):
                raise NotFoundError(f"MonitoringRule with ID {str(rule.id)} does not exist.")

            if action != "view" and not getattr(principal, f"can_{action}")(task_obj):
                raise PermissionDeniedError(f"You do not have permission to {action} this rule.")

        return rule

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get_collection(
        self,
        task: Union[uuid.UUID, MonitoringTask],
        principal: User | ServiceAccount | AnonymousPrincipal,
        page: int = Field(gt=0, default=1),
        page_size: int = Field(gt=0, default=100),
        order_by: list[str] = Field(default_factory=list),
        datastream: list[uuid.UUID] | Unset = Unset,
        rule_type: list[str] | Unset = Unset,
    ) -> tuple[int, QuerySet[MonitoringRule]]:
        """
        Return a collection of rules for the given task.
        """

        if isinstance(task, uuid.UUID):
            try:
                task = MonitoringTask.objects.select_related("monitoring_site__workspace").get(pk=task)
            except MonitoringTask.DoesNotExist:
                raise NotFoundError(f"Task with ID {str(task)} does not exist.")

        if not principal.can_view(task):
            raise NotFoundError(f"Task with ID {str(task.id)} does not exist.")

        queryset = MonitoringRule.objects.filter(task=task).select_related("datastream")

        if datastream is not Unset:
            queryset = queryset.filter(datastream__in=datastream)

        if rule_type is not Unset:
            queryset = queryset.filter(rule_type__in=rule_type)

        if not all(term.lstrip("-") in self.order_by_fields for term in order_by):
            raise BadRequestError(f"Invalid order_by field(s): {order_by}")

        queryset = queryset.order_by(*order_by, "datastream_id", "rule_type")

        count = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset:offset + page_size]

        return count, queryset

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def create(
        self,
        task: Union[uuid.UUID, MonitoringTask],
        principal: User | ServiceAccount | AnonymousPrincipal,
        datastream_id: uuid.UUID,
        rule_type: RuleType,
        uid: uuid.UUID = Field(default_factory=uuid.uuid7),
        min_value: float | None = None,
        max_value: float | None = None,
        window_interval: int | None = None,
        window_interval_units: WindowIntervalUnits | None = None,
    ) -> MonitoringRule:
        """
        Create a monitoring rule linked to a task and datastream.
        """

        if isinstance(task, uuid.UUID):
            try:
                task = principal.annotate_permissions(
                    MonitoringTask.objects.select_related("monitoring_site__workspace").filter(pk=task)
                ).get()
            except MonitoringTask.DoesNotExist:
                raise NotFoundError(f"Task with ID {str(task)} does not exist.")

        if not principal.can_view(task):
            raise NotFoundError(f"Task with ID {str(task.id)} does not exist.")
        if not principal.can_edit(task):
            raise PermissionDeniedError("You do not have permission to edit this task.")

        rule = MonitoringRule(
            pk=uid,
            task=task,
            datastream_id=getattr(datastream_id, "pk", datastream_id),
            rule_type=rule_type,
            min_value=min_value,
            max_value=max_value,
            window_interval=window_interval,
            window_interval_units=window_interval_units,
        )
        rule.full_clean()
        rule.save()

        return self.get(rule=rule.pk, task=task)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def update(
        self,
        rule: Union[uuid.UUID, MonitoringRule],
        task: Union[uuid.UUID, MonitoringTask],
        principal: User | ServiceAccount | AnonymousPrincipal,
        min_value: float | None | Unset = Unset,
        max_value: float | None | Unset = Unset,
        window_interval: int | None | Unset = Unset,
        window_interval_units: WindowIntervalUnits | None | Unset = Unset,
    ) -> MonitoringRule:
        """
        Update a monitoring rule's parameters.
        """

        rule = self.get(rule=rule, task=task, action="edit", principal=principal)

        editable_fields = {
            "min_value": min_value,
            "max_value": max_value,
            "window_interval": window_interval,
            "window_interval_units": window_interval_units,
        }
        for field, value in editable_fields.items():
            if value is not Unset:
                setattr(rule, field, value)

        rule.full_clean()
        rule.save()

        return self.get(rule=rule.pk, task=task)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def delete(
        self,
        rule: Union[uuid.UUID, MonitoringRule],
        task: Union[uuid.UUID, MonitoringTask],
        principal: User | ServiceAccount | AnonymousPrincipal,
    ) -> None:
        """
        Delete a monitoring rule.
        """

        rule = self.get(rule=rule, task=task, action="delete", principal=principal)
        rule.delete()
