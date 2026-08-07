import pandas as pd
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from processing.etl.loader import HydroServerInternalLoader
from hydroserverpy.etl.exceptions import ETLError
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory
from tests.processing.etl.factories import EtlTaskFactory


pytestmark = pytest.mark.django_db

NONEXISTENT = "00000000-0000-0000-0000-000000000000"

# Shared phenomenon_end_time cutoff used by most datastreams in this file.
CUTOFF = datetime(2025, 2, 10, 9, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def task_instance():
    return EtlTaskFactory()


def _make_payload(target_id, timestamps=None, values=None):
    if timestamps is None:
        timestamps = ["2025-02-09T00:00:00Z", "2025-02-10T09:00:00Z", "2025-02-11T00:00:00Z"]
    if values is None:
        values = [1.0, 2.0, 3.0]
    return pd.DataFrame({
        "timestamp": pd.to_datetime(timestamps, utc=True),
        "value": values,
        "target_id": target_id,
    })


def _load(payload, task_instance, **kwargs):
    """Run HydroServerInternalLoader.load with observation writes stubbed out."""

    loader = HydroServerInternalLoader(**{k: v for k, v in kwargs.items() if k == "chunk_size"})
    load_kwargs = {k: v for k, v in kwargs.items() if k != "chunk_size"}

    with patch("processing.etl.loader.observation_service") as mock_service:
        result = loader.load(payload, task_instance=task_instance, **load_kwargs)

    return result, mock_service


def _dt(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# load – fallback filtering (no data ingestion window configured)
# ---------------------------------------------------------------------------

class TestHydroServerInternalLoaderPhenomenonEndTimeFallback:

    def test_skips_observations_at_or_before_phenomenon_end_time(self, task_instance):
        ds1 = str(DatastreamFactory(
            monitoring_site=MonitoringSiteFactory(workspace=task_instance.workspace), phenomenon_end_time=CUTOFF,
        ).pk)
        payload = _make_payload(target_id=ds1)

        result, mock_service = _load(payload, task_instance)

        # Only 2025-02-11 is strictly after CUTOFF.
        assert result.target_results[ds1].values_loaded == 1
        chunk = mock_service.bulk_create.call_args.kwargs["data"].data
        assert chunk == [[pd.Timestamp("2025-02-11T00:00:00", tz="UTC"), 3.0]]

    def test_skips_target_with_no_observations_after_cutoff(self, task_instance):
        ds1 = str(DatastreamFactory(
            monitoring_site=MonitoringSiteFactory(workspace=task_instance.workspace), phenomenon_end_time=CUTOFF,
        ).pk)
        payload = _make_payload(
            target_id=ds1, timestamps=["2025-02-09T00:00:00Z", "2025-02-10T09:00:00Z"], values=[1.0, 2.0],
        )

        result, mock_service = _load(payload, task_instance)

        assert result.target_results[ds1].status == "skipped"
        assert result.skipped_count == 1
        mock_service.bulk_create.assert_not_called()

    def test_mode_is_append_by_default(self, task_instance):
        ds1 = str(DatastreamFactory(
            monitoring_site=MonitoringSiteFactory(workspace=task_instance.workspace), phenomenon_end_time=CUTOFF,
        ).pk)
        payload = _make_payload(target_id=ds1)

        result, mock_service = _load(payload, task_instance)

        mock_service.bulk_create.assert_called_once()
        assert mock_service.bulk_create.call_args.kwargs["mode"] == "append"


# ---------------------------------------------------------------------------
# load – data ingestion window filtering
# ---------------------------------------------------------------------------

class TestHydroServerInternalLoaderDataIngestionWindow:

    def test_window_start_is_inclusive(self, task_instance):
        ds1 = str(DatastreamFactory(
            monitoring_site=MonitoringSiteFactory(workspace=task_instance.workspace), phenomenon_end_time=CUTOFF,
        ).pk)
        payload = _make_payload(target_id=ds1)

        result, mock_service = _load(
            payload, task_instance, data_ingestion_window_start=_dt("2025-02-10T09:00:00"),
        )

        chunk = mock_service.bulk_create.call_args.kwargs["data"].data
        assert [row[0] for row in chunk] == [
            pd.Timestamp("2025-02-10T09:00:00", tz="UTC"), pd.Timestamp("2025-02-11T00:00:00", tz="UTC"),
        ]

    def test_window_end_is_inclusive(self, task_instance):
        # No phenomenon_end_time, so the fallback filter at loader.py doesn't apply and
        # only window_end bounds the result.
        ds1 = str(DatastreamFactory(
            monitoring_site=MonitoringSiteFactory(workspace=task_instance.workspace), phenomenon_end_time=None,
        ).pk)
        payload = _make_payload(target_id=ds1)

        result, mock_service = _load(
            payload, task_instance, data_ingestion_window_end=_dt("2025-02-10T09:00:00"),
        )

        chunk = mock_service.bulk_create.call_args.kwargs["data"].data
        assert [row[0] for row in chunk] == [
            pd.Timestamp("2025-02-09T00:00:00", tz="UTC"), pd.Timestamp("2025-02-10T09:00:00", tz="UTC"),
        ]

    def test_window_start_overrides_phenomenon_end_time_cutoff(self, task_instance):
        # phenomenon_end_time (CUTOFF) would normally exclude 2025-02-09 and 2025-02-10,
        # but an explicit window start takes priority and only bounds by the window itself.
        ds1 = str(DatastreamFactory(
            monitoring_site=MonitoringSiteFactory(workspace=task_instance.workspace), phenomenon_end_time=CUTOFF,
        ).pk)
        payload = _make_payload(target_id=ds1)

        result, mock_service = _load(
            payload, task_instance, data_ingestion_window_start=_dt("2025-02-09T00:00:00"),
        )

        assert result.target_results[ds1].values_loaded == 3

    def test_mode_is_insert_when_window_start_is_set(self, task_instance):
        ds1 = str(DatastreamFactory(
            monitoring_site=MonitoringSiteFactory(workspace=task_instance.workspace), phenomenon_end_time=CUTOFF,
        ).pk)
        payload = _make_payload(target_id=ds1)

        result, mock_service = _load(
            payload, task_instance, data_ingestion_window_start=_dt("2025-02-09T00:00:00"),
        )

        assert mock_service.bulk_create.call_args.kwargs["mode"] == "insert"

    def test_replace_mode_issues_single_delete_over_full_range_before_inserting(self, task_instance):
        ds1 = str(DatastreamFactory(
            monitoring_site=MonitoringSiteFactory(workspace=task_instance.workspace), phenomenon_end_time=CUTOFF,
        ).pk)
        payload = _make_payload(target_id=ds1)

        result, mock_service = _load(
            payload, task_instance, chunk_size=1, data_ingestion_window_start=_dt("2025-02-09T00:00:00"),
        )

        mock_service.bulk_delete.assert_called_once()
        delete_data = mock_service.bulk_delete.call_args.kwargs["data"]
        assert delete_data.phenomenon_time_start == pd.Timestamp("2025-02-09T00:00:00", tz="UTC")
        assert delete_data.phenomenon_time_end == pd.Timestamp("2025-02-11T00:00:00", tz="UTC")
        assert mock_service.bulk_create.call_count == 3
        assert all(call.kwargs["mode"] == "insert" for call in mock_service.bulk_create.call_args_list)

    def test_replace_mode_skips_inserts_when_delete_fails(self, task_instance):
        ds1 = str(DatastreamFactory(
            monitoring_site=MonitoringSiteFactory(workspace=task_instance.workspace), phenomenon_end_time=CUTOFF,
        ).pk)
        payload = _make_payload(target_id=ds1)

        loader = HydroServerInternalLoader()
        with patch("processing.etl.loader.observation_service") as mock_service:
            mock_service.bulk_delete.side_effect = Exception("boom")
            result = loader.load(
                payload, task_instance=task_instance, data_ingestion_window_start=_dt("2025-02-09T00:00:00"),
            )

        assert result.target_results[ds1].status == "failed"
        mock_service.bulk_create.assert_not_called()


# ---------------------------------------------------------------------------
# load – shared pre-filter across multiple targets in one payload
# ---------------------------------------------------------------------------

class TestHydroServerInternalLoaderMultiTargetPrefilter:

    def test_each_target_still_applies_its_own_tighter_cutoff(self, task_instance):
        # DS2's cutoff is later than DS1's, so the shared pre-filter (which uses
        # the earliest/minimum cutoff) must not cause DS2 to load a row that
        # falls before DS2's own, later cutoff.
        ds1 = str(DatastreamFactory(
            monitoring_site=MonitoringSiteFactory(workspace=task_instance.workspace), phenomenon_end_time=CUTOFF,
        ).pk)
        ds2 = str(DatastreamFactory(
            monitoring_site=MonitoringSiteFactory(workspace=task_instance.workspace),
            phenomenon_end_time=CUTOFF + timedelta(days=1),
        ).pk)
        payload = pd.concat(
            [
                _make_payload(target_id=ds1, timestamps=["2025-02-10T12:00:00Z"], values=[1.0]),
                _make_payload(target_id=ds2, timestamps=["2025-02-10T12:00:00Z"], values=[2.0]),
            ],
            ignore_index=True,
        )

        result, mock_service = _load(payload, task_instance)

        assert result.target_results[ds1].values_loaded == 1
        assert result.target_results[ds2].status == "skipped"

    def test_prefilter_is_skipped_when_any_target_has_no_cutoff(self, task_instance):
        # If the pre-filter ran using DS1's cutoff regardless, it would wrongly
        # trim DS2's row even though DS2 has never been loaded and should
        # receive everything, including timestamps before DS1's cutoff.
        ds1 = str(DatastreamFactory(
            monitoring_site=MonitoringSiteFactory(workspace=task_instance.workspace), phenomenon_end_time=CUTOFF,
        ).pk)
        ds2 = str(DatastreamFactory(
            monitoring_site=MonitoringSiteFactory(workspace=task_instance.workspace), phenomenon_end_time=None,
        ).pk)
        payload = pd.concat(
            [
                _make_payload(target_id=ds1, timestamps=["2025-02-11T00:00:00Z"], values=[1.0]),
                _make_payload(target_id=ds2, timestamps=["1970-01-02T00:00:00Z"], values=[2.0]),
            ],
            ignore_index=True,
        )

        result, mock_service = _load(payload, task_instance)

        assert result.target_results[ds1].values_loaded == 1
        assert result.target_results[ds2].values_loaded == 1


# ---------------------------------------------------------------------------
# load – datastream resolution errors
# ---------------------------------------------------------------------------

class TestHydroServerInternalLoaderDatastreamResolution:

    def test_raises_etl_error_for_missing_datastream(self, task_instance):
        payload = _make_payload(target_id=NONEXISTENT)

        with pytest.raises(ETLError, match="do not exist on this HydroServer instance"):
            _load(payload, task_instance)


# ---------------------------------------------------------------------------
# load – chunking
# ---------------------------------------------------------------------------

class TestHydroServerInternalLoaderChunking:

    def test_uploads_in_multiple_chunks_when_over_chunk_size(self, task_instance):
        ds1 = str(DatastreamFactory(
            monitoring_site=MonitoringSiteFactory(workspace=task_instance.workspace), phenomenon_end_time=CUTOFF,
        ).pk)
        payload = _make_payload(
            target_id=ds1,
            timestamps=["2025-02-11T00:00:00Z", "2025-02-12T00:00:00Z", "2025-02-13T00:00:00Z"],
            values=[1.0, 2.0, 3.0],
        )

        result, mock_service = _load(payload, task_instance, chunk_size=2)

        assert mock_service.bulk_create.call_count == 2
        assert result.target_results[ds1].values_loaded == 3


# ---------------------------------------------------------------------------
# target_loaded_through
# ---------------------------------------------------------------------------

class TestHydroServerInternalLoaderTargetLoadedThrough:

    def test_returns_phenomenon_end_time(self):
        datastream = DatastreamFactory(phenomenon_end_time=CUTOFF)
        loader = HydroServerInternalLoader()

        assert loader.target_loaded_through(str(datastream.pk)) == CUTOFF

    def test_returns_epoch_when_never_loaded(self):
        datastream = DatastreamFactory(phenomenon_end_time=None)
        loader = HydroServerInternalLoader()

        assert loader.target_loaded_through(str(datastream.pk)) == datetime(1970, 1, 1, tzinfo=timezone.utc)

    def test_raises_etl_error_for_missing_datastream(self):
        loader = HydroServerInternalLoader()

        with pytest.raises(ETLError, match="does not exist on this HydroServer instance"):
            loader.target_loaded_through(NONEXISTENT)
