import json
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from hydroserverpy.api.models.etl.task import EtlTask
from hydroserverpy.api.services.etl.task import TaskService
from hydroserverpy.api.services.etl.data_connection import DataConnectionService
from hydroserverpy.api.utils import create_merge_patch


CASES = json.loads((Path(__file__).parents[4] / "django" / "contracts" / "merge-patch-cases.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_create_merge_patch_matches_shared_contract(case):
    before = json.dumps(case)
    assert create_merge_patch(case["original"], case["updated"]) == case["patch"]
    assert json.dumps(case) == before


def test_create_merge_patch_preserves_top_level_omissions_and_explicit_none():
    assert create_merge_patch(
        {"name": "Task", "description": "Remove me"},
        {"name": ..., "description": None},
    ) == {"description": None}


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_task_save_generates_merge_patch_from_server_snapshot(case):
    client = MagicMock()
    client.base_route = "api/ogc"
    client.etltasks = TaskService(client)
    fields = {"id": str(uuid4()), "name": "Task", "dataConnectionId": str(uuid4())}
    task = EtlTask(client=client, **fields, **case["original"])
    task.task_variables = case["updated"]["taskVariables"]
    client.request.return_value.json.return_value = {"data": {**fields, **case["updated"]}}

    task.save()

    args, kwargs = client.request.call_args_list[0]
    assert args[0] == "patch"
    assert kwargs["headers"]["Content-type"] == "application/merge-patch+json"
    body = json.loads(kwargs["data"])
    if "taskVariables" in case["patch"]:
        assert body["taskVariables"] == case["patch"]["taskVariables"]
    else:
        assert "taskVariables" not in body


def test_task_update_preserves_omissions_and_variable_deletion_markers():
    client = MagicMock()
    client.base_route = "api/ogc"
    service = TaskService(client)
    service.get = MagicMock()

    service.update(uuid4(), description=None, task_variables={"parameter": None})
    body = json.loads(client.request.call_args.kwargs["data"])
    assert body == {"description": None, "taskVariables": {"parameter": None}}


def test_task_update_does_not_send_unsupplied_variables():
    client = MagicMock()
    service = TaskService(client)
    service.get = MagicMock()

    service.update(uuid4(), name="Renamed")

    assert json.loads(client.request.call_args.kwargs["data"]) == {"name": "Renamed"}


def test_connection_update_preserves_unsupplied_placeholder_list():
    client = MagicMock()
    service = DataConnectionService(client)
    service.get = MagicMock()

    service.update(uuid4(), name="Connection", source_url="https://example.com/data.csv",
                   timestamp_key="time", payload_type="CSV")

    assert "placeholderVariables" not in json.loads(client.request.call_args.kwargs["data"])


def test_task_update_sends_explicit_none_variables_for_server_validation():
    client = MagicMock()
    service = TaskService(client)
    service.get = MagicMock()

    service.update(uuid4(), name="Renamed", task_variables=None)

    assert json.loads(client.request.call_args.kwargs["data"]) == {"name": "Renamed", "taskVariables": None}
