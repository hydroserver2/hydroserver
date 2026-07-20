import uuid6
from typing import Literal, Optional, Union

from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model

from core.iam.models import APIKey
from core.iam.models.utils import PermissionChecker
from core.sta.models import Datastream


User = get_user_model()


class QCHistoryQuerySet(models.QuerySet):
    def visible(self, principal: Optional[Union[User, APIKey]]):
        if not principal:
            return self.none()
        elif hasattr(principal, "account_type"):
            if principal.account_type == "admin":
                return self
            return self.filter(
                Q(managed_datastream__thing__workspace__owner=principal)
                | Q(
                    managed_datastream__thing__workspace__collaborators__user=principal,
                    managed_datastream__thing__workspace__collaborators__role__permissions__resource_type__in=[
                        "*",
                        "Datastream",
                    ],
                    managed_datastream__thing__workspace__collaborators__role__permissions__permission_type__in=[
                        "*",
                        "view",
                    ],
                )
            )
        elif hasattr(principal, "workspace"):
            return self.filter(
                Q(
                    managed_datastream__thing__workspace__apikeys=principal,
                    managed_datastream__thing__workspace__apikeys__role__permissions__resource_type__in=[
                        "*",
                        "Datastream",
                    ],
                    managed_datastream__thing__workspace__apikeys__role__permissions__permission_type__in=[
                        "*",
                        "view",
                    ],
                )
            )
        else:
            return self.none()


class QCHistory(models.Model, PermissionChecker):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    managed_datastream = models.OneToOneField(
        Datastream, on_delete=models.CASCADE, related_name="qc_history"
    )
    source_datastream = models.ForeignKey(
        Datastream, on_delete=models.SET_NULL, null=True, blank=True, related_name="qc_source_histories"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    phenomenon_time_start = models.DateTimeField(null=True, blank=True)
    phenomenon_time_end = models.DateTimeField(null=True, blank=True)
    source_checksum = models.CharField(max_length=64, null=True, blank=True)
    managed_checksum = models.CharField(max_length=64, null=True, blank=True)

    objects = QCHistoryQuerySet.as_manager()

    class Meta:
        app_label = "quality"

    def __str__(self):
        return f"{self.managed_datastream_id} - {self.id}"

    @classmethod
    def can_principal_create(
        cls,
        principal: Union[User, APIKey, None],
        managed_datastream: Datastream,
    ) -> bool:
        return "edit" in cls.check_object_permissions(
            principal=principal,
            workspace=managed_datastream.thing.workspace,
            resource_type="Datastream",
        )

    def get_principal_permissions(
        self, principal: Union[User, APIKey, None]
    ) -> list[Literal["edit", "delete", "view"]]:
        return self.check_object_permissions(
            principal=principal,
            workspace=self.managed_datastream.thing.workspace,
            resource_type="Datastream",
        )
