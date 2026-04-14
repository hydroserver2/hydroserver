import uuid
import uuid6
from typing import Optional, Union, Literal

from pydantic import Field, ConfigDict, validate_call
from django.db import transaction
from django.db.models.query import QuerySet
from django.contrib.auth import get_user_model

from core.types import Unset
from core.iam.models import APIKey
from core.service import ServiceUtils
from core.sta.models import Datastream
from processing.monitoring.models import MonitoringTask, MonitoringRule


User = get_user_model()

RuleType = Literal["range", "rate_of_change", "persistence", "missing_data"]
WindowIntervalUnits = Literal["minutes", "hours", "days"]


class MonitoringRuleService(ServiceUtils):

    order_by_fields = {"id", "rule_type", "datastream_id"}

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get(
        self,
        rule: Union[uuid.UUID, MonitoringRule],
        task: Union[uuid.UUID, MonitoringTask],
        action: Literal["view", "edit", "delete"] = "view",
        principal: User | APIKey | None | Unset = Unset,
    ) -> MonitoringRule:
        """
        Get a monitoring rule, scoped to the given task.
        """

        if isinstance(rule, uuid.UUID):
            try:
                rule = MonitoringRule.objects.select_related(
                    "task__thing__workspace",
                    "datastream",
                ).get(pk=rule, task=task)
            except MonitoringRule.DoesNotExist:
                raise LookupError(f"MonitoringRule with ID {str(rule)} does not exist.")

        if principal is not Unset:
            permissions = rule.task.get_principal_permissions(principal=principal)

            if "view" not in permissions:
                raise LookupError(f"MonitoringRule with ID {str(rule.id)} does not exist.")

            if action not in permissions:
                raise PermissionError(f"You do not have permission to {action} this rule.")

        return rule

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get_collection(
        self,
        task: Union[uuid.UUID, MonitoringTask],
        principal: Optional[User | APIKey] = None,
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
                task = MonitoringTask.objects.select_related("thing__workspace").get(pk=task)
            except MonitoringTask.DoesNotExist:
                raise LookupError(f"Task with ID {str(task)} does not exist.")

        if principal is not None:
            permissions = task.get_principal_permissions(principal=principal)
            if "view" not in permissions:
                raise LookupError(f"Task with ID {str(task.id)} does not exist.")

        queryset = MonitoringRule.objects.filter(task=task).select_related("datastream")

        if datastream is not Unset:
            queryset = queryset.filter(datastream__in=datastream)

        if rule_type is not Unset:
            queryset = queryset.filter(rule_type__in=rule_type)

        if not all(term.lstrip("-") in self.order_by_fields for term in order_by):
            raise ValueError(f"Invalid order_by field(s): {order_by}")

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
        principal: User | APIKey,
        datastream_id: uuid.UUID,
        rule_type: RuleType,
        uid: uuid.UUID = Field(default_factory=uuid6.uuid7),
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
                task = MonitoringTask.objects.select_related("thing__workspace").get(pk=task)
            except MonitoringTask.DoesNotExist:
                raise LookupError(f"Task with ID {str(task)} does not exist.")

        permissions = task.get_principal_permissions(principal=principal)

        if "view" not in permissions:
            raise LookupError(f"Task with ID {str(task.id)} does not exist.")
        if "edit" not in permissions:
            raise PermissionError("You do not have permission to edit this task.")

        try:
            datastream = Datastream.objects.select_related("thing").get(
                pk=datastream_id, thing=task.thing
            )
        except Datastream.DoesNotExist:
            raise LookupError(
                f"Datastream with ID {str(datastream_id)} does not exist on this task's thing."
            )

        self._validate_rule(
            rule_type=rule_type,
            min_value=min_value,
            max_value=max_value,
            window_interval=window_interval,
            window_interval_units=window_interval_units,
        )

        if MonitoringRule.objects.filter(task=task, datastream=datastream, rule_type=rule_type).exists():
            raise ValueError(
                f"A rule of type '{rule_type}' already exists for this datastream on this task."
            )

        rule = MonitoringRule.objects.create(
            pk=uid,
            task=task,
            datastream=datastream,
            rule_type=rule_type,
            min_value=min_value,
            max_value=max_value,
            window_interval=window_interval,
            window_interval_units=window_interval_units,
        )

        return self.get(rule=rule.pk, task=task)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def update(
        self,
        rule: Union[uuid.UUID, MonitoringRule],
        task: Union[uuid.UUID, MonitoringTask],
        principal: User | APIKey,
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

        self._validate_rule(
            rule_type=rule.rule_type,
            min_value=rule.min_value,
            max_value=rule.max_value,
            window_interval=rule.window_interval,
            window_interval_units=rule.window_interval_units,
        )

        rule.save()

        return self.get(rule=rule.pk, task=task)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def delete(
        self,
        rule: Union[uuid.UUID, MonitoringRule],
        task: Union[uuid.UUID, MonitoringTask],
        principal: User | APIKey,
    ) -> None:
        """
        Delete a monitoring rule.
        """

        rule = self.get(rule=rule, task=task, action="delete", principal=principal)
        rule.delete()

    @staticmethod
    def _validate_rule(
        rule_type: str,
        min_value: float | None,
        max_value: float | None,
        window_interval: int | None,
        window_interval_units: str | None,
    ) -> None:
        """
        Validate a monitoring rule.
        """

        has_min = min_value is not None
        has_max = max_value is not None
        has_window = window_interval is not None
        has_window_units = window_interval_units is not None

        if has_window != has_window_units:
            raise ValueError("window_interval and window_interval_units must both be set or both be omitted.")

        if rule_type == "range":
            if not has_min and not has_max:
                raise ValueError("At least one of min_value or max_value is required for rule_type 'range'.")
            if has_min and has_max and min_value >= max_value:
                raise ValueError("min_value must be less than max_value.")
            if has_window:
                raise ValueError("window_interval must not be set for rule_type 'range'.")

        elif rule_type == "rate_of_change":
            if not has_max:
                raise ValueError("max_value is required for rule_type 'rate_of_change'.")
            if not has_window:
                raise ValueError("window_interval and window_interval_units are required for rule_type 'rate_of_change'.")
            if has_min:
                raise ValueError("min_value must not be set for rule_type 'rate_of_change'.")

        elif rule_type == "persistence":
            if not has_window:
                raise ValueError("window_interval and window_interval_units are required for rule_type 'persistence'.")
            if has_min and has_max and min_value >= max_value:
                raise ValueError("min_value must be less than max_value.")

        elif rule_type == "missing_data":
            if not has_window:
                raise ValueError("window_interval and window_interval_units are required for rule_type 'missing_data'.")
            if has_min or has_max:
                raise ValueError("min_value and max_value must not be set for rule_type 'missing_data'.")

        else:
            raise ValueError(f"Invalid rule_type '{rule_type}'.")
