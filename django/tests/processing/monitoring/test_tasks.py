import uuid

import pytest

from processing.monitoring.tasks import run_monitoring_task

pytestmark = pytest.mark.django_db


def test_run_monitoring_task_raises_for_nonexistent_task():
    with pytest.raises(Exception, match="Encountered an unexpected data monitoring error."):
        run_monitoring_task(str(uuid.uuid4()))
