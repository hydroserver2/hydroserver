import uuid

import pytest

from processing.products.tasks import run_data_product_task

pytestmark = pytest.mark.django_db


def test_run_data_product_task_raises_for_nonexistent_task():
    with pytest.raises(Exception, match="Encountered an unexpected data product error."):
        run_data_product_task(str(uuid.uuid4()))
