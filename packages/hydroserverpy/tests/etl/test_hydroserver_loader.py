import pandas as pd
import pytest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from hydroserverpy import HydroServer
from hydroserverpy.etl.loaders.hydroserver import HydroServerLoader
from hydroserverpy.etl.exceptions import ETLError


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

def _make_datastream(uid="target-1", phenomenon_end_time=None):
    return SimpleNamespace(uid=uid, phenomenon_end_time=phenomenon_end_time)


def _make_loader(datastreams=None, **kwargs):
    """Build a HydroServerLoader with a mocked HydroServer client.

    `datastreams` maps target_id -> a datastream object, or an Exception
    instance to be raised from client.datastreams.get for that target_id.
    """

    datastreams = datastreams or {}
    client = MagicMock(spec=HydroServer)

    def _get(target_id):
        result = datastreams[target_id]
        if isinstance(result, Exception):
            raise result
        return result

    client.datastreams.get.side_effect = _get
    defaults = dict(client=client)
    defaults.update(kwargs)
    return HydroServerLoader(**defaults), client


def _make_payload(target_id="target-1", timestamps=None, values=None):
    if timestamps is None:
        timestamps = ["2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z", "2026-01-03T00:00:00Z"]
    if values is None:
        values = [1.0, 2.0, 3.0]
    return pd.DataFrame({
        "timestamp": pd.to_datetime(timestamps, utc=True),
        "value": values,
        "target_id": target_id,
    })


def _dt(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def _loaded_timestamps(client):
    """Return the timestamps from the most recent load_observations call."""
    chunk = client.datastreams.load_observations.call_args.kwargs["observations"]
    return list(chunk["timestamp"])


# ---------------------------------------------------------------------------
# load – fallback filtering (no data ingestion window configured)
# ---------------------------------------------------------------------------

class TestHydroServerLoaderPhenomenonEndTimeFallback:

    def test_loads_all_observations_when_no_cutoff_and_no_window(self):
        loader, client = _make_loader({"target-1": _make_datastream()})
        result = loader.load(_make_payload())

        assert result.target_results["target-1"].status == "success"
        assert result.target_results["target-1"].values_loaded == 3
        assert client.datastreams.load_observations.call_args.kwargs["mode"] == "append"

    def test_skips_observations_at_or_before_phenomenon_end_time(self):
        datastream = _make_datastream(phenomenon_end_time=_dt("2026-01-02T00:00:00"))
        loader, client = _make_loader({"target-1": datastream})
        result = loader.load(_make_payload())

        # Only 2026-01-03 is strictly after the cutoff.
        assert result.target_results["target-1"].values_loaded == 1
        assert _loaded_timestamps(client) == [_dt("2026-01-03T00:00:00")]

    def test_skips_target_with_no_observations_after_cutoff(self):
        datastream = _make_datastream(phenomenon_end_time=_dt("2026-01-03T00:00:00"))
        loader, client = _make_loader({"target-1": datastream})
        result = loader.load(_make_payload())

        assert result.target_results["target-1"].status == "skipped"
        assert result.skipped_count == 1
        client.datastreams.load_observations.assert_not_called()


# ---------------------------------------------------------------------------
# load – data ingestion window filtering
# ---------------------------------------------------------------------------

class TestHydroServerLoaderDataIngestionWindow:

    def test_window_start_is_inclusive(self):
        loader, client = _make_loader({"target-1": _make_datastream()})
        loader.load(_make_payload(), data_ingestion_window_start=_dt("2026-01-02T00:00:00"))

        assert _loaded_timestamps(client) == [_dt("2026-01-02T00:00:00"), _dt("2026-01-03T00:00:00")]

    def test_window_end_is_inclusive(self):
        loader, client = _make_loader({"target-1": _make_datastream()})
        loader.load(_make_payload(), data_ingestion_window_end=_dt("2026-01-02T00:00:00"))

        assert _loaded_timestamps(client) == [_dt("2026-01-01T00:00:00"), _dt("2026-01-02T00:00:00")]

    def test_window_start_and_end_combined(self):
        loader, client = _make_loader({"target-1": _make_datastream()})
        loader.load(
            _make_payload(),
            data_ingestion_window_start=_dt("2026-01-02T00:00:00"),
            data_ingestion_window_end=_dt("2026-01-02T00:00:00"),
        )

        assert _loaded_timestamps(client) == [_dt("2026-01-02T00:00:00")]

    def test_window_start_overrides_phenomenon_end_time_cutoff(self):
        # phenomenon_end_time would normally exclude 2026-01-02, but an explicit
        # window start takes priority and only bounds by the window itself.
        datastream = _make_datastream(phenomenon_end_time=_dt("2026-01-02T00:00:00"))
        loader, client = _make_loader({"target-1": datastream})
        loader.load(_make_payload(), data_ingestion_window_start=_dt("2026-01-01T00:00:00"))

        assert _loaded_timestamps(client) == [
            _dt("2026-01-01T00:00:00"), _dt("2026-01-02T00:00:00"), _dt("2026-01-03T00:00:00"),
        ]

    def test_mode_is_insert_when_window_start_is_set(self):
        loader, client = _make_loader({"target-1": _make_datastream()})
        loader.load(_make_payload(), data_ingestion_window_start=_dt("2026-01-01T00:00:00"))

        assert client.datastreams.load_observations.call_args.kwargs["mode"] == "insert"

    def test_mode_is_append_when_window_start_is_not_set(self):
        loader, client = _make_loader({"target-1": _make_datastream()})
        loader.load(_make_payload(), data_ingestion_window_end=_dt("2026-01-03T00:00:00"))

        assert client.datastreams.load_observations.call_args.kwargs["mode"] == "append"

    def test_replace_mode_issues_single_delete_over_full_range_before_inserting(self):
        loader, client = _make_loader({"target-1": _make_datastream()}, chunk_size=1)
        loader.load(_make_payload(), data_ingestion_window_start=_dt("2026-01-01T00:00:00"))

        client.datastreams.delete_observations.assert_called_once_with(
            uid="target-1",
            phenomenon_time_start=_dt("2026-01-01T00:00:00"),
            phenomenon_time_end=_dt("2026-01-03T00:00:00"),
        )
        assert client.datastreams.load_observations.call_count == 3
        assert all(
            call.kwargs["mode"] == "insert" for call in client.datastreams.load_observations.call_args_list
        )

    def test_replace_mode_skips_inserts_when_delete_fails(self):
        loader, client = _make_loader({"target-1": _make_datastream()})
        client.datastreams.delete_observations.side_effect = Exception("boom")

        result = loader.load(_make_payload(), data_ingestion_window_start=_dt("2026-01-01T00:00:00"))

        assert result.target_results["target-1"].status == "failed"
        client.datastreams.load_observations.assert_not_called()


# ---------------------------------------------------------------------------
# load – datastream resolution errors
# ---------------------------------------------------------------------------

class TestHydroServerLoaderDatastreamResolution:

    def test_raises_etl_error_for_missing_datastream(self):
        loader, client = _make_loader({"target-1": Exception("404 Not Found")})

        with pytest.raises(ETLError, match="could not find one or more destination datastreams"):
            loader.load(_make_payload())

    def test_raises_etl_error_for_unexpected_lookup_failure(self):
        loader, client = _make_loader({"target-1": Exception("500 Internal Server Error")})

        with pytest.raises(ETLError, match="could not find a destination datastream"):
            loader.load(_make_payload())


# ---------------------------------------------------------------------------
# load – chunking
# ---------------------------------------------------------------------------

class TestHydroServerLoaderChunking:

    def test_uploads_in_multiple_chunks_when_over_chunk_size(self):
        loader, client = _make_loader({"target-1": _make_datastream()}, chunk_size=2)
        result = loader.load(_make_payload())

        assert client.datastreams.load_observations.call_count == 2
        assert result.target_results["target-1"].values_loaded == 3


# ---------------------------------------------------------------------------
# target_loaded_through
# ---------------------------------------------------------------------------

class TestHydroServerLoaderTargetLoadedThrough:

    def test_returns_phenomenon_end_time(self):
        cutoff = _dt("2026-01-02T00:00:00")
        loader, client = _make_loader({"target-1": _make_datastream(phenomenon_end_time=cutoff)})

        assert loader.target_loaded_through("target-1") == cutoff

    def test_returns_none_when_never_loaded(self):
        loader, client = _make_loader({"target-1": _make_datastream(phenomenon_end_time=None)})

        assert loader.target_loaded_through("target-1") is None

    def test_raises_etl_error_for_missing_datastream(self):
        loader, client = _make_loader({"target-1": Exception("404 Not Found")})

        with pytest.raises(ETLError, match="could not find a destination datastream"):
            loader.target_loaded_through("target-1")
