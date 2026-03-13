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

    @staticmethod
    def extract_message(result: dict | None) -> str | None:
        if not isinstance(result, dict):
            return None

        for key in (
            "message",
            "summary",
            "statusMessage",
            "status_message",
            "failureReason",
            "failure_reason",
            "error",
        ):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value

        return None

    @staticmethod
    def extract_failure_count(result: dict | None) -> int | None:
        if not isinstance(result, dict):
            return None

        for key in ("failure_count", "failureCount"):
            value = result.get(key)

            if isinstance(value, bool):
                continue
            if isinstance(value, int):
                return value
            if isinstance(value, float) and value.is_integer():
                return int(value)
            if isinstance(value, str):
                normalized = value.strip()
                if normalized.lstrip("-").isdigit():
                    return int(normalized)

        return None

    @property
    def message(self) -> str | None:
        return self.extract_message(self.result)

    @property
    def failure_count(self) -> int | None:
        return self.extract_failure_count(self.result)
