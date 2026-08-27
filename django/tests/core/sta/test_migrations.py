import importlib

import pytest

from core.sta.models import ObservedProperty, ProcessingLevel, Unit
from tests.core.sta.factories import ProcessingLevelFactory


pytestmark = pytest.mark.django_db

migration = importlib.import_module(
    "core.sta.migrations.0015_rename_metadata_table_fields"
)


class CurrentApps:
    @staticmethod
    def get_model(app_label, model_name):
        assert app_label == "sta"
        return {
            "ObservedProperty": ObservedProperty,
            "ProcessingLevel": ProcessingLevel,
            "Unit": Unit,
        }[model_name]


def test_processing_level_data_migration_preserves_legacy_definitions():
    short_definition = ProcessingLevelFactory(
        global_=True,
        code="0",
        name="Unused",
        definition="Raw data",
        description="Raw-data explanation",
    )
    uri_definition = ProcessingLevelFactory(
        global_=True,
        code="1",
        name="Unused",
        definition="https://example.com/processing-levels/quality-controlled",
        description="Quality-controlled explanation",
    )
    long_legacy_definition = "Detailed legacy processing-level definition. " * 10
    long_definition = ProcessingLevelFactory(
        global_=True,
        code="2",
        name="Unused",
        definition=long_legacy_definition,
        description="Derived-data explanation",
    )

    migration.migrate_processing_level_fields(CurrentApps(), None)

    short_definition.refresh_from_db()
    assert short_definition.name == "Raw data"
    assert short_definition.definition is None
    assert short_definition.description == "Raw-data explanation"

    uri_definition.refresh_from_db()
    assert uri_definition.name == "1"
    assert (
        uri_definition.definition
        == "https://example.com/processing-levels/quality-controlled"
    )
    assert uri_definition.description == "Quality-controlled explanation"

    long_definition.refresh_from_db()
    assert long_definition.name == "2"
    assert long_definition.definition is None
    assert long_legacy_definition in long_definition.description
    assert long_definition.description.endswith("Derived-data explanation")

    migration.prepare_reverse_migration(CurrentApps(), None)

    short_definition.refresh_from_db()
    assert short_definition.definition == "Raw data"
    assert short_definition.description == "Raw-data explanation"

    uri_definition.refresh_from_db()
    assert (
        uri_definition.definition
        == "https://example.com/processing-levels/quality-controlled"
    )
    assert uri_definition.description == "Quality-controlled explanation"

    long_definition.refresh_from_db()
    assert long_definition.definition == long_legacy_definition
    assert long_definition.description == "Derived-data explanation"
