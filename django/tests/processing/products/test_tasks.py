import uuid
from unittest.mock import patch

import pandas as pd
import pytest

from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL
from processing.products.tasks import _load_to_datastream, run_data_product_task
from tests.processing.products.factories import DataProductTransformationFactory

pytestmark = pytest.mark.django_db


def test_run_data_product_task_raises_for_nonexistent_task():
    with pytest.raises(Exception, match="Encountered an unexpected data product error."):
        run_data_product_task(str(uuid.uuid4()))


def test_load_to_datastream_writes_observations_tagged_with_the_output_datastream_id():
    transformation = DataProductTransformationFactory()
    result_df = pd.DataFrame({
        TIMESTAMP_COL: pd.to_datetime(
            ["2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"], utc=True
        ),
        RESULT_COL: [1.0, 2.0],
    })

    with patch("processing.products.tasks.observation_service") as mock_service:
        loaded = _load_to_datastream(transformation, result_df)

    assert loaded == 2
    mock_service.bulk_create.assert_called_once()
    call_kwargs = mock_service.bulk_create.call_args.kwargs
    assert call_kwargs["datastream_id"] == transformation.output_datastream.pk
    assert call_kwargs["data"].datastream_id == transformation.output_datastream.pk
    assert call_kwargs["data"].fields == ["phenomenonTime", "result"]
    assert list(call_kwargs["data"].data) == [
        [pd.Timestamp("2026-01-01T00:00:00", tz="UTC"), 1.0],
        [pd.Timestamp("2026-01-01T01:00:00", tz="UTC"), 2.0],
    ]
