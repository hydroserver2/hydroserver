import json
import uuid

from datetime import timedelta
from smtplib import SMTPException
from unittest import mock

import pytest

from celery.exceptions import Retry
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone as django_tz

from hydroserver.celery import app as celery_app
from interfaces.api.services.etl.data_connection import DataConnectionAPIService
from processing.etl.tasks import run_etl_task, send_etl_notification_email
from processing.orchestration.models import TaskRun
from tests.processing.etl.factories import DataConnectionFactory, EtlTaskFactory

pytestmark = pytest.mark.django_db


def test_run_etl_task_raises_for_nonexistent_task():
    with pytest.raises(Exception, match="Encountered an unexpected ETL error."):
        run_etl_task(str(uuid.uuid4()))


def _make_notification():
    data_connection = DataConnectionFactory()
    task = EtlTaskFactory(data_connection=data_connection)
    notification = DataConnectionAPIService().apply_notification(
        data_connection=data_connection,
        recipient_emails=["a@example.com", "b@example.com"],
        crontab="0 9 * * *",
    )
    return notification, task


def test_notification_schedule_runs_on_worker_and_emails_each_recipient(mailoutbox):
    notification, task = _make_notification()
    TaskRun.objects.create(task=task, status="FAILURE", message="Source returned 500.")
    TaskRun.objects.create(task=task, status="SUCCESS", message="Loaded 10 observations.")
    TaskRun.objects.create(
        task=task, status="FAILURE", message="Old failure.", started_at=django_tz.now() - timedelta(days=3)
    )

    # Dispatch the stored schedule the way a worker would.
    periodic_task = notification.periodic_task
    celery_app.loader.import_default_modules()
    result = celery_app.tasks[periodic_task.task].apply(kwargs=json.loads(periodic_task.kwargs))

    assert result.successful()
    assert sorted(m.to for m in mailoutbox) == [["a@example.com"], ["b@example.com"]]
    html = mailoutbox[0].alternatives[0][0]
    assert task.name in html
    assert "Loaded 10 observations." in html
    assert "Source returned 500." in html
    assert "Old failure." not in html
    assert f"/orchestration/ingestion?task_id={task.id}" in html


def test_notification_retries_only_failed_recipients(mailoutbox):
    notification, _ = _make_notification()
    real_send = EmailMultiAlternatives.send

    def send(msg, *args, **kwargs):
        if msg.to == ["b@example.com"]:
            raise SMTPException("Mailbox unavailable.")
        return real_send(msg, *args, **kwargs)

    with (
        mock.patch.object(EmailMultiAlternatives, "send", send),
        mock.patch.object(send_etl_notification_email, "retry", return_value=Retry()) as retry,
        pytest.raises(Retry),
    ):
        send_etl_notification_email(str(notification.pk))

    assert [m.to for m in mailoutbox] == [["a@example.com"]]
    assert retry.call_args.kwargs["kwargs"] == {
        "data_connection_id": str(notification.pk),
        "recipients": ["b@example.com"],
    }
