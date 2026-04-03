import uuid6
from typing import Union, Literal

from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model

from core.iam.models import Workspace, APIKey
from core.iam.models.utils import PermissionChecker
from core.sta.models import Datastream
from processing.orchestration.models.task import Task

from .data_connection import DataConnection


User = get_user_model()


class EtlTaskQuerySet(models.QuerySet):
    def visible(self, principal: Union[User, APIKey]):
        if not principal:
            return self.none()
        elif hasattr(principal, "account_type"):
            if principal.account_type == "admin":
                return self
            else:
                return self.filter(
                    Q(data_connection__workspace__owner=principal)
                    | Q(
                        data_connection__workspace__collaborators__user=principal,
                        data_connection__workspace__collaborators__role__permissions__resource_type__in=[
                            "*",
                            "ETL",
                        ],
                        data_connection__workspace__collaborators__role__permissions__permission_type__in=[
                            "*",
                            "view",
                        ],
                    )
                )
        elif hasattr(principal, "workspace"):
            return self.filter(
                Q(
                    data_connection__workspace__apikeys=principal,
                    data_connection__workspace__apikeys__role__permissions__resource_type__in=[
                        "*",
                        "ETL",
                    ],
                    data_connection__workspace__apikeys__role__permissions__permission_type__in=[
                        "*",
                        "view",
                    ],
                )
            )
        else:
            return self.none()


class EtlTask(Task, PermissionChecker):
    data_connection = models.ForeignKey(
        DataConnection,
        on_delete=models.CASCADE,
        related_name="etl_tasks",
    )
    runtime_variables = models.JSONField(default=dict)

    objects = EtlTaskQuerySet.as_manager()

    def __str__(self):
        return f"{self.name} - {self.id}"

    class Meta:
        app_label = "etl"

    @classmethod
    def can_principal_create(
        cls, principal: Union[User, APIKey, None], workspace: Workspace
    ):
        return cls.check_create_permissions(
            principal=principal, workspace=workspace, resource_type="ETL"
        )

    def get_principal_permissions(
        self, principal: Union[User, APIKey, None]
    ) -> list[Literal["edit", "delete", "view"]]:
        return self.check_object_permissions(
            principal=principal, workspace=self.data_connection.workspace, resource_type="ETL"
        )

    @property
    def workspace(self):
        return self.data_connection.workspace


class EtlMapping(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    etl_task = models.ForeignKey(EtlTask, on_delete=models.CASCADE, related_name="etl_mappings")
    source_identifier = models.CharField(max_length=255)
    target_datastream = models.ForeignKey(Datastream, on_delete=models.CASCADE, related_name="etl_mappings")

    class Meta:
        app_label = "etl"
