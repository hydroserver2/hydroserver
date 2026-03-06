import uuid6
from django.db import models
from .task import Task


class TaskRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    status = models.CharField(max_length=255)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    result = models.JSONField(blank=True, null=True)
