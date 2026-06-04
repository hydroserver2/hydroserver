import uuid6

from typing import Union, Literal

from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model

from core.iam.models import Workspace, APIKey
from core.iam.models.utils import PermissionChecker
from core.sta.models import Thing
from processing.orchestration.models.task import Task


User = get_user_model()


class MonitoringTaskQuerySet(models.QuerySet):
    def visible(self, principal: Union[User, APIKey]):
        if not principal:
            return self.none()
        elif hasattr(principal, "account_type"):
            if principal.account_type == "admin":
                return self
            else:
                return self.filter(
                    Q(thing__workspace__owner=principal)
                    | Q(
                        thing__workspace__collaborators__user=principal,
                        thing__workspace__collaborators__role__permissions__resource_type__in=[
                            "*",
                            "DataMonitoring",
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
                    thing__workspace__apikeys=principal,
                    thing__workspace__apikeys__role__permissions__resource_type__in=[
                        "*",
                        "DataMonitoring",
                    ],
                    thing__workspace__apikeys__role__permissions__permission_type__in=[
                        "*",
                        "view",
                    ],
                )
            )
        else:
            return self.none()


class MonitoringTask(Task, PermissionChecker):
    thing = models.ForeignKey(
        Thing,
        on_delete=models.CASCADE,
        related_name="monitoring_tasks",
    )

    objects = MonitoringTaskQuerySet.as_manager()

    class Meta:
        app_label = "monitoring"

    def __str__(self):
        return f"{self.name} - {self.id}"

    @classmethod
    def can_principal_create(
        cls, principal: Union[User, APIKey, None], workspace: Workspace
    ):
        return cls.check_create_permissions(
            principal=principal, workspace=workspace, resource_type="DataMonitoring"
        )

    def get_principal_permissions(
        self, principal: Union[User, APIKey, None]
    ) -> list[Literal["edit", "delete", "view"]]:
        return self.check_object_permissions(
            principal=principal, workspace=self.thing.workspace, resource_type="DataMonitoring"
        )

    @property
    def workspace(self):
        return self.thing.workspace


class MonitoringNotificationRecipient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    task = models.ForeignKey(
        MonitoringTask,
        on_delete=models.CASCADE,
        related_name="recipients",
    )
    email = models.EmailField()

    class Meta:
        app_label = "monitoring"
        constraints = [
            models.UniqueConstraint(
                fields=["task", "email"],
                name="unique_monitoring_notification_recipient_email",
            )
        ]

    def __str__(self):
        return f"{self.task_id} — {self.email}"
