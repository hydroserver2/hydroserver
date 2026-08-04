import uuid

from django.db import models

from core.sta.models import Datastream


class QCHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
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

    class Meta:
        app_label = "quality"

    def __str__(self):
        return f"{self.managed_datastream_id} - {self.id}"
