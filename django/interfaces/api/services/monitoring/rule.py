import uuid

from typing import Literal, Optional, get_args
from django.contrib.auth import get_user_model
from django.db import transaction

from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from processing.monitoring.models import MonitoringTask, MonitoringRule
from interfaces.api.http.errors import NotFoundError, PermissionDeniedError
from interfaces.api.service import APIService
from interfaces.api.schemas.monitoring.rule import (
    MonitoringRuleFields,
    MonitoringRuleOrderByFields,
    MonitoringRulePatchBody,
    MonitoringRulePostBody,
    MonitoringRuleResponse,
    MONITORING_RULE_INCLUDE_RELATIONS,
)

User = get_user_model()


class MonitoringRuleAPIService(APIService):
    INCLUDE_RELATIONS = MONITORING_RULE_INCLUDE_RELATIONS

    @staticmethod
    def get_task_for_action(
        principal: User | ServiceAccount | AnonymousPrincipal,
        task_id: uuid.UUID,
        action: Literal["view", "edit", "delete"],
    ) -> MonitoringTask:
        try:
            task = MonitoringTask.objects.select_related(
                "monitoring_site__workspace"
            ).get(pk=task_id)
        except MonitoringTask.DoesNotExist:
            raise NotFoundError(f"Task with ID {task_id} does not exist.")

        if not principal.can_view(task):
            raise NotFoundError(f"Task with ID {task_id} does not exist.")

        if action != "view" and not getattr(principal, f"can_{action}")(task):
            raise PermissionDeniedError(
                f"You do not have permission to {action} rules on this task."
            )

        return task

    def get_rule_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        task_id: uuid.UUID,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        select_related: Optional[list[str]] = None,
        prefetch_related: Optional[list[str]] = None,
    ) -> MonitoringRule:
        task = self.get_task_for_action(principal, task_id, action)
        queryset = MonitoringRule.objects.filter(task=task, pk=uid)

        if select_related:
            queryset = queryset.select_related(*select_related)
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)

        try:
            return queryset.get()
        except MonitoringRule.DoesNotExist:
            raise NotFoundError(f"MonitoringRule with ID {uid} does not exist.")

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        task_id: uuid.UUID,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        order_by: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        task = self.get_task_for_action(principal, task_id, "view")
        queryset = MonitoringRule.objects.filter(task=task)

        for field in ["datastream_id", "rule_type"]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        if order_by:
            queryset = self.apply_ordering(
                queryset, order_by, list(get_args(MonitoringRuleOrderByFields))
            )
        else:
            queryset = queryset.order_by("datastream_id", "rule_type")

        if requested_includes:
            select_paths = [
                self.INCLUDE_RELATIONS[name]["path"] for name in requested_includes
            ]
            queryset = queryset.select_related(*select_paths)
            if "datastream" in requested_includes:
                queryset = queryset.select_related(
                    "datastream__monitoring_site"
                ).prefetch_related("datastream__datastream_linked_resources")

        queryset, meta = self.apply_pagination(queryset, offset, limit)
        rules = list(queryset.all())

        return {
            "data": [MonitoringRuleResponse.model_validate(r) for r in rules],
            "meta": meta,
            "included": self.resolve_includes(
                rules, requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        task_id: uuid.UUID,
        uid: uuid.UUID,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        select_paths = [
            self.INCLUDE_RELATIONS[name]["path"] for name in requested_includes
        ]
        prefetch_paths = []

        if "datastream" in requested_includes:
            select_paths.append("datastream__monitoring_site")
            prefetch_paths.append("datastream__datastream_linked_resources")

        rule = self.get_rule_for_action(
            principal=principal,
            task_id=task_id,
            uid=uid,
            action="view",
            select_related=select_paths,
            prefetch_related=prefetch_paths,
        )

        return {
            "data": MonitoringRuleResponse.model_validate(rule),
            "included": self.resolve_includes(
                [rule], requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    @transaction.atomic
    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        task_id: uuid.UUID,
        data: MonitoringRulePostBody,
    ):
        task = self.get_task_for_action(principal, task_id, "edit")

        rule = MonitoringRule(
            pk=data.id,
            task=task,
            datastream_id=data.datastream_id,
            rule_type=data.rule_type,
            **data.dict(include=set(MonitoringRuleFields.model_fields.keys())),
        )
        rule.full_clean()
        rule.save()

        return {"id": rule.pk}

    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        task_id: uuid.UUID,
        uid: uuid.UUID,
        data: MonitoringRulePatchBody,
    ):
        rule = self.get_rule_for_action(
            principal=principal, task_id=task_id, uid=uid, action="edit"
        )

        rule_data = data.dict(
            include=set(MonitoringRuleFields.model_fields.keys()), exclude_unset=True
        )
        for field, value in rule_data.items():
            setattr(rule, field, value)

        rule.full_clean()
        rule.save()

    def delete(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        task_id: uuid.UUID,
        uid: uuid.UUID,
    ):
        rule = self.get_rule_for_action(
            principal=principal, task_id=task_id, uid=uid, action="delete"
        )
        rule.delete()
