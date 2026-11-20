import json
from unittest.mock import patch

import pytest

from interfaces.api.merge_patch import MERGE_PATCH_MEDIA_TYPE, merge_patch
from interfaces.api.urls import api
from interfaces.api.views.etl.task import etl_task_service
from interfaces.api.views.quality.operation import qc_operation_service
from interfaces.api.views.sta.datastream import datastream_service
from interfaces.api.views.sta.monitoring_site import monitoring_site_service
from tests.core.iam.factories import UserFactory, WorkspaceFactory
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory
from tests.interfaces.api.helpers import MERGE_PATCH_CASES as CASES
from tests.processing.etl.factories import DataConnectionFactory, EtlTaskFactory
from tests.processing.quality.factories import QCHistoryFactory, QCOperationFactory, QCSessionFactory


@pytest.mark.django_db
@pytest.mark.parametrize("resource", ["task", "task_schedule", "monitoring_site", "datastream", "qc_operation"])
def test_patch_omitting_json_preserves_changes_after_permission_read(client, resource):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    site = MonitoringSiteFactory(workspace=workspace)
    initial_json = {"station": "A", "parameter": "temperature"}
    latest_json = {**initial_json, "station": "B", "units": "C"}
    changes = {"name": "Renamed"}

    if resource in {"task", "task_schedule"}:
        instance = EtlTaskFactory(
            data_connection=DataConnectionFactory(workspace=workspace), task_variables=initial_json
        )
        service, reader, field = etl_task_service, "get_task_for_action", "task_variables"
        url = f"/api/ogc/collections/etl-tasks/items/{instance.pk}"
        if resource == "task_schedule":
            changes = {"schedule": {"interval": 5, "intervalPeriod": "minutes", "enabled": False}}
    elif resource == "monitoring_site":
        instance = site
        instance.tags = initial_json
        instance.save()
        service, reader, field = monitoring_site_service, "get_monitoring_site_for_action", "tags"
        url = f"/api/ogc/collections/monitoring-sites/items/{instance.pk}"
    elif resource == "datastream":
        instance = DatastreamFactory(monitoring_site=site, tags=initial_json)
        service, reader, field = datastream_service, "get_datastream_for_action", "tags"
        url = f"/api/ogc/collections/datastreams/items/{instance.pk}"
    else:
        history = QCHistoryFactory(
            managed_datastream=DatastreamFactory(monitoring_site=site),
            source_datastream=DatastreamFactory(monitoring_site=site),
        )
        session = QCSessionFactory(history=history)
        instance = QCOperationFactory(session=session, arguments=initial_json)
        service, reader, field = qc_operation_service, "get", "arguments"
        changes = {"comment": "Updated comment"}
        url = (
            f"/api/ogc/collections/quality-control-histories/items/{history.pk}"
            f"/sessions/{session.pk}/operations/{instance.pk}"
        )

    read_for_action = getattr(service, reader)

    def read_then_update_json(*args, **kwargs):
        stale_instance = read_for_action(*args, **kwargs)
        # Reproduce a JSON write finishing after the permission read, before
        # this request saves its instance. No timing or threads needed.
        type(instance).objects.filter(pk=instance.pk).update(**{field: latest_json})
        return stale_instance

    client.force_login(owner)
    with patch.object(service, reader, side_effect=read_then_update_json):
        response = client.patch(url, data=changes, content_type=MERGE_PATCH_MEDIA_TYPE)

    assert response.status_code == 204, response.content
    instance.refresh_from_db()
    assert getattr(instance, field) == latest_json
    if resource == "task_schedule":
        schedule = client.get(url).json()["data"]["schedule"]
        for name, value in changes["schedule"].items():
            assert schedule[name] == value
    else:
        for name, value in changes.items():
            assert getattr(instance, name) == value


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_shared_client_patches_produce_updated_resource(case):
    original_before = json.dumps(case["original"])
    patch_before = json.dumps(case["patch"])
    assert merge_patch(case["original"], case["patch"]) == case["updated"]
    assert json.dumps(case["original"]) == original_before
    assert json.dumps(case["patch"]) == patch_before


# RFC 7396, Appendix A, including non-object targets and patches.
@pytest.mark.parametrize("target, patch, expected", [
    ({"a": "b"}, {"a": "c"}, {"a": "c"}),
    ({"a": "b"}, {"b": "c"}, {"a": "b", "b": "c"}),
    ({"a": "b"}, {"a": None}, {}),
    ({"a": "b", "b": "c"}, {"a": None}, {"b": "c"}),
    ({"a": ["b"]}, {"a": "c"}, {"a": "c"}),
    ({"a": "c"}, {"a": ["b"]}, {"a": ["b"]}),
    ({"a": {"b": "c"}}, {"a": {"b": "d", "c": None}}, {"a": {"b": "d"}}),
    ({"a": [{"b": "c"}]}, {"a": [1]}, {"a": [1]}),
    (["a", "b"], ["c", "d"], ["c", "d"]),
    ({"a": "b"}, ["c"], ["c"]),
    ({"a": "foo"}, None, None),
    ({"a": "foo"}, "bar", "bar"),
    ({"e": None}, {"a": 1}, {"e": None, "a": 1}),
    ([1, 2], {"a": "b", "c": None}, {"a": "b"}),
    ({}, {"a": {"bb": {"ccc": None}}}, {"a": {"bb": {}}}),
])
def test_rfc_7396_examples(target, patch, expected):
    assert merge_patch(target, patch) == expected


def test_openapi_documents_json_patches_without_changing_multipart_requests():
    paths = api.get_openapi_schema(path_prefix="/api/ogc/")["paths"]
    task = paths["/api/ogc/collections/etl-tasks/items/{task_id}"]["patch"]
    assert set(task["requestBody"]["content"]) == {"application/json", MERGE_PATCH_MEDIA_TYPE}
    for path_item in paths.values():
        content = path_item.get("patch", {}).get("requestBody", {}).get("content", {})
        if "application/json" in content:
            assert content[MERGE_PATCH_MEDIA_TYPE] == content["application/json"]
    attachment = paths[
        "/api/ogc/collections/datastreams/items/{datastream_id}/linked-resources/{linked_resource_id}"
    ]["patch"]
    assert MERGE_PATCH_MEDIA_TYPE not in attachment["requestBody"]["content"]
