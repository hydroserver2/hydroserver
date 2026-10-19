import uuid
from unittest.mock import MagicMock

import pytest

from hydroserverpy.api.services.etl.data_connection import DataConnectionService
from hydroserverpy.api.services.etl.task import TaskService
from hydroserverpy.api.services.iam.role import RoleService
from hydroserverpy.api.services.iam.workspace import WorkspaceService
from hydroserverpy.api.services.monitoring.task import MonitoringTaskService
from hydroserverpy.api.services.products.rating_curve import RatingCurveService
from hydroserverpy.api.services.products.task import DataProductTaskService


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        if self._payload is None:
            raise ValueError("No JSON content (empty response body)")
        return self._payload


def make_client():
    client = MagicMock()
    client.base_route = "/api/ogc"
    return client


# Payloads mirror the server's *Response serialization, which returns related resources as flat
# IDs/emails rather than nested objects.

SCHEDULE = {
    "enabled": True,
    "startTime": "2026-01-01T00:00:00+00:00",
    "crontab": None,
    "interval": 15,
    "intervalPeriod": "minutes",
    "nextRunAt": "2026-01-01T00:15:00+00:00",
}

def workspace_payload(item_id):
    return {
        "id": item_id,
        "name": "My Workspace",
        "isPrivate": False,
        "ownerEmail": "owner@example.com",
        "pendingTransferToEmail": None,
        "collaboratorRoleId": "00000000-0000-0000-0000-000000000001",
    }


def data_connection_payload(item_id):
    return {
        "id": item_id,
        "name": "My Connection",
        "description": None,
        "sourceUrl": "https://example.com/data.csv",
        "authHeaderName": None,
        "authHeaderValue": None,
        "timezoneType": "offset",
        "timezone": "-0700",
        "workspaceId": "00000000-0000-0000-0000-000000000002",
        "payload": {
            "type": "CSV",
            "timestampKey": "timestamp",
            "timestampFormat": "ISO8601",
            "headerRow": 1,
            "dataStartRow": 2,
            "delimiter": ",",
            "dataIngestionWindow": None,
        },
        "placeholderVariables": [],
        "notification": None,
        "taskCount": 0,
        "taskAttentionCount": 0,
    }


def rating_curve_payload(item_id):
    return {
        "id": item_id,
        "name": "My Rating Curve",
        "description": None,
        "fittingMethod": "linear",
        "points": [[0.0, 0.0], [1.0, 2.5]],
        "monitoringSiteId": "00000000-0000-0000-0000-000000000003",
    }


def etl_task_payload(item_id):
    return {
        "id": item_id,
        "name": "My ETL Task",
        "description": None,
        "workspaceId": "00000000-0000-0000-0000-000000000002",
        "dataConnectionId": "00000000-0000-0000-0000-000000000004",
        "taskVariables": {"site_code": "10109000"},
        "schedule": SCHEDULE,
        "latestRun": None,
        "mappingCount": 1,
    }


def monitoring_task_payload(item_id):
    return {
        "id": item_id,
        "name": "My Monitoring Task",
        "description": None,
        "workspaceId": "00000000-0000-0000-0000-000000000002",
        "monitoringSiteId": "00000000-0000-0000-0000-000000000003",
        "schedule": SCHEDULE,
        "latestRun": None,
        "ruleTypeCounts": {"range": 1, "missing_data": 1},
        "recipients": ["owner@example.com"],
    }


def data_product_task_payload(item_id):
    return {
        "id": item_id,
        "name": "My Data Product Task",
        "description": None,
        "workspaceId": "00000000-0000-0000-0000-000000000002",
        "monitoringSiteId": "00000000-0000-0000-0000-000000000003",
        "schedule": SCHEDULE,
        "latestRun": None,
        "transformationTypes": ["derivation"],
    }


@pytest.fixture(
    params=[
        (WorkspaceService, workspace_payload, {"name": "My Workspace", "is_private": False}),
        (
            DataConnectionService,
            data_connection_payload,
            {
                "name": "My Connection",
                "workspace": "00000000-0000-0000-0000-000000000002",
                "source_url": "https://example.com/data.csv",
                "timestamp_key": "timestamp",
                "payload_type": "CSV",
            },
        ),
        (
            RatingCurveService,
            rating_curve_payload,
            {
                "name": "My Rating Curve",
                "monitoring_site": "00000000-0000-0000-0000-000000000003",
                "fitting_method": "linear",
            },
        ),
        (
            TaskService,
            etl_task_payload,
            {"name": "My ETL Task", "data_connection": "00000000-0000-0000-0000-000000000004"},
        ),
        (
            MonitoringTaskService,
            monitoring_task_payload,
            {"name": "My Monitoring Task", "monitoring_site": "00000000-0000-0000-0000-000000000003"},
        ),
        (
            DataProductTaskService,
            data_product_task_payload,
            {"name": "My Data Product Task", "monitoring_site": "00000000-0000-0000-0000-000000000003"},
        ),
    ],
    ids=["workspace", "data_connection", "rating_curve", "etl_task", "monitoring_task", "data_product_task"],
)
def resource(request):
    service_cls, payload_fn, create_kwargs = request.param
    return service_cls(make_client()), payload_fn, create_kwargs


def test_get_parses_server_response(resource):
    service, payload_fn, _ = resource
    item_id = str(uuid.uuid4())
    service.client.request.return_value = FakeResponse({"data": payload_fn(item_id)})

    result = service.get(item_id)

    assert str(result.uid) == item_id


def test_list_parses_server_response(resource):
    service, payload_fn, _ = resource
    item_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    service.client.request.return_value = FakeResponse(
        {"data": [payload_fn(i) for i in item_ids], "meta": {"numberMatched": 2}}
    )

    result = service.list()

    assert [str(item.uid) for item in result.items] == item_ids


def test_create_and_update_parse_refetched_server_response(resource):
    service, payload_fn, create_kwargs = resource
    item_id = str(uuid.uuid4())
    service.client.request.side_effect = [
        FakeResponse({"id": item_id}, status_code=201),
        FakeResponse({"data": payload_fn(item_id)}),
        FakeResponse(status_code=204),
        FakeResponse({"data": payload_fn(item_id)}),
    ]

    created = service.create(**create_kwargs)
    update_kwargs = {
        k: v for k, v in create_kwargs.items() if k not in ("workspace", "monitoring_site", "data_connection")
    }
    if isinstance(service, RatingCurveService):
        update_kwargs["points"] = []
    updated = service.update(item_id, **update_kwargs)

    assert str(created.uid) == item_id
    assert str(updated.uid) == item_id


def test_workspace_maps_flat_related_fields():
    service = WorkspaceService(make_client())
    item_id = str(uuid.uuid4())
    service.client.request.return_value = FakeResponse({"data": workspace_payload(item_id)})

    workspace = service.get(item_id)

    assert workspace.owner_email == "owner@example.com"
    assert workspace.pending_transfer_to_email is None
    assert str(workspace.collaborator_role_id) == "00000000-0000-0000-0000-000000000001"


def test_related_resources_resolve_from_flat_ids():
    client = make_client()
    dc_service = DataConnectionService(client)
    rc_service = RatingCurveService(client)
    client.request.side_effect = [
        FakeResponse({"data": data_connection_payload(str(uuid.uuid4()))}),
        FakeResponse({"data": rating_curve_payload(str(uuid.uuid4()))}),
    ]

    data_connection = dc_service.get(uuid.uuid4())
    rating_curve = rc_service.get(uuid.uuid4())

    assert data_connection.workspace is client.workspaces.get.return_value
    client.workspaces.get.assert_called_once_with(uid=uuid.UUID("00000000-0000-0000-0000-000000000002"))
    assert rating_curve.monitoring_site is client.monitoring_sites.get.return_value
    client.monitoring_sites.get.assert_called_once_with(uid=uuid.UUID("00000000-0000-0000-0000-000000000003"))


def test_task_models_map_workspace_and_rule_counts():
    client = make_client()
    client.request.side_effect = [
        FakeResponse({"data": monitoring_task_payload(str(uuid.uuid4()))}),
        FakeResponse({"data": etl_task_payload(str(uuid.uuid4()))}),
        FakeResponse({"data": data_product_task_payload(str(uuid.uuid4()))}),
    ]
    workspace_id = uuid.UUID("00000000-0000-0000-0000-000000000002")

    monitoring_task = MonitoringTaskService(client).get(uuid.uuid4())
    etl_task = TaskService(client).get(uuid.uuid4())
    data_product_task = DataProductTaskService(client).get(uuid.uuid4())

    assert monitoring_task.rule_type_counts == {"range": 1, "missing_data": 1}
    assert {monitoring_task.workspace_id, etl_task.workspace_id, data_product_task.workspace_id} == {workspace_id}


def test_role_maps_permissions():
    client = make_client()
    role_id = str(uuid.uuid4())
    client.request.return_value = FakeResponse({"data": {
        "id": role_id,
        "name": "Editor",
        "description": None,
        "workspaceId": None,
        "permissions": [{"resource": "Datastream", "action": "edit"}],
    }})

    role = RoleService(client).get(role_id)

    assert [(p.resource, p.action) for p in role.permissions] == [("Datastream", "edit")]
