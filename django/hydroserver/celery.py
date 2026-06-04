import os
from celery import Celery

from processing.orchestration.tracked_task import TrackedTask


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hydroserver.settings")

app = Celery("hydroserver")
app.Task = TrackedTask
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
