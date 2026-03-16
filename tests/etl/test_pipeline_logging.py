import logging
from io import BytesIO
import pandas as pd
from pydantic import Field

from hydroserverpy.etl.exceptions import ETLError
from hydroserverpy.etl.extractors.base import Extractor
from hydroserverpy.etl.loaders.base import Loader, ETLLoaderResult, ETLTargetResult
from hydroserverpy.etl.models.pipeline import ETLPipeline, ETLStatus
from hydroserverpy.etl.transformers.base import Transformer, ETLDataMapping, ETLTargetPath


test_logger = logging.getLogger(__name__)


class DummyExtractor(Extractor):
    source_uri: str = Field(..., json_schema_extra={"template": True})

    def extract(self, **kwargs):
        runtime_data = self.render_runtime_data(**kwargs)
        test_logger.info("Dummy extractor fetched %s", runtime_data["source_uri"])
        return BytesIO(b"payload")


class DummyTransformer(Transformer):
    def transform(self, payload, data_mappings, **kwargs):
        test_logger.info("Dummy transformer received %s mapping(s)", len(data_mappings))
        return pd.DataFrame(
            {
                "timestamp": ["2026-03-01T00:00:00Z"],
                "value": [1.23],
                "target_id": ["target-1"],
            }
        )


class DummyLoader(Loader):
    def load(self, payload, **kwargs):
        test_logger.info("Dummy loader received %s row(s)", len(payload))
        return ETLLoaderResult(
            success_count=1,
            values_loaded_total=1,
            target_results={
                "target-1": ETLTargetResult(
                    target_identifier="target-1",
                    status="success",
                    values_loaded=1,
                )
            },
        )

    def target_loaded_through(self, target_identifier):
        return None


class FailingLoader(Loader):
    def load(self, payload, **kwargs):
        test_logger.warning("Dummy loader is about to fail")
        raise ETLError("Dummy load failure")

    def target_loaded_through(self, target_identifier):
        return None


def _make_mapping():
    return [
        ETLDataMapping(
            source_identifier="source-1",
            target_paths=[ETLTargetPath(target_identifier="target-1")],
        )
    ]


def test_pipeline_captures_structured_log_entries_for_successful_runs():
    pipeline = ETLPipeline(
        extractor=DummyExtractor(source_uri="https://example.com/{date}.csv"),
        transformer=DummyTransformer(timestamp_key="timestamp"),
        loader=DummyLoader(),
        pre_extract_messages=[
            {
                "level": "INFO",
                "message": (
                    "Checking HydroServer for the most recent data already stored "
                    "(so we only extract new observations)..."
                ),
            }
        ],
    )

    context = pipeline.run(data_mappings=_make_mapping(), date="2026-03-01")

    assert context.status == ETLStatus.SUCCESS
    assert context.log_entries

    messages = [entry["message"] for entry in context.log_entries]
    assert messages[0] == "Starting extract"
    assert "Starting extract" in messages
    assert "Starting transform" in messages
    assert "Starting load" in messages
    assert (
        "Checking HydroServer for the most recent data already stored "
        "(so we only extract new observations)..."
    ) in messages
    assert any(
        message.startswith("Resolved runtime source URI: https://example.com/2026-03-01.csv")
        for message in messages
    )
    assert "Extractor returned payload: {'type': 'BytesIO', 'bytes': 7}" in messages
    assert (
        "Transform result: {'type': 'DataFrame', 'rows': 1, 'columns': 2, 'datastreams': 1}"
        in messages
    )
    assert any("Dummy extractor fetched https://example.com/2026-03-01.csv" in message for message in messages)
    assert "Dummy transformer received 1 mapping(s)" in messages
    assert any("Dummy loader received 1 row(s)" in message for message in messages)
    assert all(
        {"timestamp", "level", "message", "logger", "stage"} <= set(entry.keys())
        for entry in context.log_entries
    )


def test_pipeline_preserves_log_entries_when_raise_on_error_is_false():
    pipeline = ETLPipeline(
        extractor=DummyExtractor(source_uri="https://example.com/{date}.csv"),
        transformer=DummyTransformer(timestamp_key="timestamp"),
        loader=FailingLoader(),
    )

    context = pipeline.run(
        data_mappings=_make_mapping(),
        raise_on_error=False,
        date="2026-03-01",
    )

    assert context.status == ETLStatus.FAILED
    assert isinstance(context.exception, ETLError)
    assert any(
        entry["message"] == "Starting load"
        for entry in context.log_entries
    )
    assert any(
        entry["message"] == "Dummy loader is about to fail"
        and entry["level"] == "WARNING"
        for entry in context.log_entries
    )
    assert any(
        entry["message"] == "Load step failed: Dummy load failure"
        and entry["level"] == "ERROR"
        for entry in context.log_entries
    )
