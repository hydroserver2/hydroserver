import pytest

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from tests.core.sta.factories import DatastreamFactory, ObservationFactory


@pytest.mark.django_db(transaction=True)
def test_standardize_metadata_preserves_legacy_values():
    previous = [("sta", "0017_datastream_search_vector_method_search_vector_and_more")]
    latest = [("sta", "0018_standardize_workspace_metadata")]
    executor = MigrationExecutor(connection)
    executor.migrate(previous)
    try:
        old_apps = executor.loader.project_state(previous).apps
        level = old_apps.get_model("sta", "ProcessingLevel").objects.create(
            name="Previous display name", code="0", description="Description " * 30,
            definition="https://example.com/level",
        )
        qualifier = old_apps.get_model("sta", "ResultQualifier").objects.create(
            code="ICE", description="Ice affected", workspace_id=None,
        )
        datastream = DatastreamFactory(processing_level_id=level.pk)
        observation = ObservationFactory(datastream=datastream, result_qualifiers=["ICE"])
        old_property = old_apps.get_model("sta", "ObservedProperty")
        old_property.objects.filter(pk=datastream.observed_property_id).update(code="C" * 256)
        with pytest.raises(ValueError, match="ObservedProperty.code"):
            MigrationExecutor(connection).migrate(latest)
        assert old_property.objects.get(pk=datastream.observed_property_id).code == "C" * 256
        old_property.objects.filter(pk=datastream.observed_property_id).update(code="C" * 255)
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        apps = executor.loader.project_state(latest).apps
        migrated_level = apps.get_model("sta", "ProcessingLevel").objects.get(pk=level.pk)
        migrated_qualifier = apps.get_model("sta", "ResultQualifier").objects.get(pk=qualifier.pk)
        assert migrated_level.name == level.description[:255]
        assert migrated_level.description == level.description
        assert migrated_level.code == level.code
        assert migrated_level.definition == level.definition
        assert migrated_qualifier.name == migrated_qualifier.code == "ICE"
        assert migrated_qualifier.description == qualifier.description
        assert "definition" not in {field.name for field in migrated_qualifier._meta.fields}
        observation.refresh_from_db()
        assert observation.result_qualifiers == ["ICE"]
        assert apps.get_model("sta", "ResultQualifier").objects.filter(search_vector="ICE").exists()
    finally:
        MigrationExecutor(connection).migrate(latest)
