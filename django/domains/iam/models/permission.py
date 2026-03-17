from django.db import models


PERMISSION_CHOICES = (
    ("*", "Full"),
    ("view", "View"),
    ("create", "Create"),
    ("edit", "Edit"),
    ("delete", "Delete"),
)

RESOURCE_TYPE_CHOICES = (
    ("*", "All"),
    ("APIKey", "API Key"),
    ("Role", "Role"),
    ("Collaborator", "Collaborator"),
    ("Task", "Task"),
    ("DataConnection", "Data Connection"),
    ("OrchestrationSystem", "Orchestration System"),
    ("Thing", "Thing"),
    ("Datastream", "Datastream"),
    ("Observation", "Observation"),
    ("Sensor", "Sensor"),
    ("ObservedProperty", "Observed Property"),
    ("ProcessingLevel", "Processing Level"),
    ("Unit", "Unit"),
    ("ResultQualifier", "Result Qualifier"),
)


class Permission(models.Model):
    role = models.ForeignKey(
        "Role", on_delete=models.DO_NOTHING, related_name="permissions"
    )
    permission_type = models.CharField(max_length=50, choices=PERMISSION_CHOICES)
    resource_type = models.CharField(max_length=50, choices=RESOURCE_TYPE_CHOICES)
    # condition = models.JSONField(null=True, blank=True)
