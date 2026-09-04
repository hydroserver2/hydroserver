import uuid

import pytest

from processing.etl.tasks import run_etl_task

pytestmark = pytest.mark.django_db


def test_run_etl_task_raises_for_nonexistent_task():
    with pytest.raises(Exception, match="Encountered an unexpected ETL error."):
        run_etl_task(str(uuid.uuid4()))
