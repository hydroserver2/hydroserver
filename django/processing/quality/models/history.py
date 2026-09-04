import uuid

from django.core.exceptions import ObjectDoesNotExist, ValidationError
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

    def clean(self):
        if not self.managed_datastream_id or not self.source_datastream_id:
            return

        try:
            managed_workspace_id = self.managed_datastream.monitoring_site.workspace_id
        except ObjectDoesNotExist:
            return

        try:
            source_workspace_id = self.source_datastream.monitoring_site.workspace_id
        except ObjectDoesNotExist:
            return

        if managed_workspace_id != source_workspace_id:
            raise ValidationError(
                "The managed datastream and source datastream must belong to the same workspace."
            )

        if self.managed_datastream.processing_level_id == self.source_datastream.processing_level_id:
            raise ValidationError(
                "The managed datastream must have a different processing level than the source datastream."
            )
