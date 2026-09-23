import pytest

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from tests.core.sta.factories import DatastreamFactory, ObservationFactory


@pytest.mark.django_db(transaction=True)
def test_standardize_metadata_preserves_legacy_values():
    previous = [("sta", "0017_datastream_search_vector_method_search_vector_and_more")]
    latest = [("sta", "0018_standardize_workspace_metadata")]
    executor = MigrationExecutor(connection)
    leaf_nodes = executor.loader.graph.leaf_nodes("sta")
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
        MigrationExecutor(connection).migrate(leaf_nodes)


@pytest.mark.django_db(transaction=True)
def test_metadata_type_migration_preserves_values_and_search():
    previous = [("sta", "0018_standardize_workspace_metadata")]
    latest = [("sta", "0019_standardize_metadata_types_and_sensor_definition")]
    executor = MigrationExecutor(connection)
    executor.migrate(previous)
    try:
        old_apps = executor.loader.project_state(previous).apps
        property_model = old_apps.get_model("sta", "ObservedProperty")
        prop = property_model.objects.create(
            name="Temperature", description="Comments", type="T" * 256,
        )
        method = old_apps.get_model("sta", "Method").objects.create(
            name="Thermometer", description="Comments", type="Instrument",
            sensor_model_definition="https://example.com/sensor",
        )
        with pytest.raises(ValueError, match="ObservedProperty.type"):
            MigrationExecutor(connection).migrate(latest)
        prop.refresh_from_db()
        assert prop.type == "T" * 256
        prop.type = "T" * 255
        prop.save()
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        apps = executor.loader.project_state(latest).apps
        migrated_method = apps.get_model("sta", "Method").objects.get(pk=method.pk)
        assert migrated_method.sensor_model_definition == method.sensor_model_definition
        assert apps.get_model("sta", "ObservedProperty").objects.get(pk=prop.pk).type == prop.type
        migrated_method.name = "Calibration"
        migrated_method.save()
        assert apps.get_model("sta", "Method").objects.filter(search_vector="Calibration").exists()
    finally:
        MigrationExecutor(connection).migrate(latest)
