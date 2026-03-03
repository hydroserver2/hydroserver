import uuid6
from typing import Union, Literal, TYPE_CHECKING
from django.db import models
from django.db.models import Q
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from domains.iam.models.utils import PermissionChecker
from django_celery_beat.models import PeriodicTask
from .data_connection import DataConnection
from .orchestration_system import OrchestrationSystem

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model
    from domains.iam.models import Workspace, APIKey

    User = get_user_model()


class TaskQuerySet(models.QuerySet):
    def visible(self, principal: Union["User", "APIKey"]):
        if not principal:
            return self.none()
        elif hasattr(principal, "account_type"):
            if principal.account_type == "admin":
                return self
            else:
                return self.filter(
                    Q(workspace__owner=principal)
                    | Q(
                        workspace__collaborators__user=principal,
                        workspace__collaborators__role__permissions__resource_type__in=[
                            "*",
                            "Task",
                        ],
                        workspace__collaborators__role__permissions__permission_type__in=[
                            "*",
                            "view",
                        ],
                    )
                )
        elif hasattr(principal, "workspace"):
            return self.filter(
                Q(
                    workspace__apikeys=principal,
                    workspace__apikeys__role__permissions__resource_type__in=[
                        "*",
                        "Task",
                    ],
                    workspace__apikeys__role__permissions__permission_type__in=[
                        "*",
                        "view",
                    ],
                )
            )
        else:
            return self.none()


class Task(models.Model, PermissionChecker):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    name = models.CharField(max_length=255)
    workspace = models.ForeignKey(
        "iam.Workspace", related_name="tasks", on_delete=models.CASCADE
    )
    data_connection = models.ForeignKey(DataConnection, on_delete=models.CASCADE, related_name="tasks")
    orchestration_system = models.ForeignKey(
        OrchestrationSystem, on_delete=models.CASCADE, related_name="tasks"
    )
    periodic_task = models.OneToOneField(
        PeriodicTask, null=True, blank=True, on_delete=models.SET_NULL, related_name="etl_task"
    )
    paused = models.BooleanField(default=False)
    next_run_at = models.DateTimeField(null=True, blank=True)
    extractor_variables = models.JSONField(default=dict)
    transformer_variables = models.JSONField(default=dict)
    loader_variables = models.JSONField(default=dict)

    objects = TaskQuerySet.as_manager()

    def __str__(self):
        return f"{self.name} - {self.id}"

    @classmethod
    def can_principal_create(
        cls, principal: Union["User", "APIKey", None], workspace: "Workspace"
    ):
        return cls.check_create_permissions(
            principal=principal, workspace=workspace, resource_type="Task"
        )

    def get_principal_permissions(
        self, principal: Union["User", "APIKey", None]
    ) -> list[Literal["edit", "delete", "view"]]:
        permissions = self.check_object_permissions(
            principal=principal, workspace=self.data_connection.workspace, resource_type="Task"
        )

        return permissions


class TaskMapping(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="mappings")
    source_identifier = models.CharField(max_length=255)


class TaskMappingPath(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    task_mapping = models.ForeignKey(TaskMapping, on_delete=models.CASCADE, related_name="paths")
    target_identifier = models.CharField(max_length=255)
    data_transformations = models.JSONField(default=dict)


@receiver(pre_delete, sender=Task)
def delete_related_periodic_task(sender, instance, **kwargs):
    periodic_task = instance.periodic_task

    if not periodic_task:
        return

    if periodic_task.crontab_id:
        periodic_task.crontab.delete()
    if periodic_task.interval_id:
        periodic_task.interval.delete()

    periodic_task.delete()
