import uuid6
from typing import Union, Literal

from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django_celery_beat.models import PeriodicTask

from core.iam.models import Workspace, APIKey


User = get_user_model()


class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    periodic_task = models.OneToOneField(
        PeriodicTask, null=True, blank=True, on_delete=models.SET_NULL, related_name="orchestration_task"
    )
    next_run_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "orchestration"

    def __str__(self):
        return self.name

    @classmethod
    def can_principal_create(
        cls, principal: Union[User, APIKey, None], workspace: Workspace
    ) -> bool:
        raise NotImplementedError("Task creation permissions not implemented")

    def get_principal_permissions(
        self, principal: Union[User, APIKey, None]
    ) -> list[Literal["edit", "delete", "view"]]:
        raise NotImplementedError("Task permissions not implemented")

    @property
    def workspace(self) -> Workspace:
        raise NotImplementedError("Task workspace not implemented")


@receiver(pre_delete, sender=Task)
def delete_related_periodic_task(sender, instance, **kwargs):
    periodic_task = instance.periodic_task

    if not periodic_task:
        return

    if periodic_task.crontab_id:
        crontab = periodic_task.crontab
        PeriodicTask.objects.filter(pk=periodic_task.pk).update(crontab=None)
        crontab.delete()

    if periodic_task.interval_id:
        interval = periodic_task.interval
        PeriodicTask.objects.filter(pk=periodic_task.pk).update(interval=None)
        interval.delete()

    Task.objects.filter(pk=instance.pk).update(periodic_task=None)
    periodic_task.delete()
