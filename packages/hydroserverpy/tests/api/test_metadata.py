import json
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from hydroserverpy.api.services.sta.method import MethodService
from hydroserverpy.api.services.sta.observed_property import ObservedPropertyService
from hydroserverpy.api.services.sta.processing_level import ProcessingLevelService
from hydroserverpy.api.services.sta.result_qualifier import ResultQualifierService
from hydroserverpy.api.services.sta.unit import UnitService


@pytest.mark.parametrize("service_class,fields", [
    (MethodService, {"type": "Instrument Deployment", "description": "Comments"}),
    (ObservedPropertyService, {"type": "Hydrology", "description": "Comments"}),
    (ProcessingLevelService, {"description": "Comments"}),
    (ResultQualifierService, {"description": "Comments"}),
    (UnitService, {"type": "Length", "symbol": "m"}),
])
def test_create_metadata_without_optional_fields(service_class, fields):
    client = MagicMock(base_route="api/data")
    uid = str(uuid4())
    payload = {"id": uid, "name": "Name", **fields}
    if service_class != ResultQualifierService:
        payload["definition"] = None
    if service_class != UnitService:
        payload["code"] = None
    client.request.side_effect = [
        MagicMock(json=lambda: {"id": uid}),
        MagicMock(json=lambda: {"data": payload.copy()}),
    ]
    created = service_class(client).create(name="Name", **fields)
    assert created.name == "Name"
    if service_class == ResultQualifierService:
        assert "definition" not in created.model_dump()
    else:
        assert created.definition is None
    if service_class != UnitService:
        assert created.code is None


def test_qualifier_name_can_be_saved_independently_of_code():
    client = MagicMock(base_route="api/data")
    service = ResultQualifierService(client)
    client.resultqualifiers = service
    uid = str(uuid4())
    original = {"id": uid, "name": "Estimated", "description": "Comments", "code": "EXT"}
    updated = {**original, "name": "Provisional"}
    client.request.side_effect = [
        MagicMock(json=lambda: {"data": original.copy()}),
        MagicMock(),
        MagicMock(json=lambda: {"data": updated.copy()}),
    ]
    qualifier = service.get(uid)
    qualifier.name = updated["name"]
    qualifier.save()
    patch_body = json.loads(client.request.call_args_list[1].kwargs["data"])
    assert patch_body == {"name": updated["name"]}
    assert qualifier.code == "EXT"
    assert qualifier.unsaved_changes == {}


@pytest.mark.parametrize("service_class,args,kwargs,expected", [
    (ResultQualifierService, ("ICE", "Ice affected"), {},
     {"name": "ICE", "description": "Ice affected", "code": None}),
    (ResultQualifierService, ("ICE",), {"description": "Ice affected"},
     {"name": "ICE", "description": "Ice affected", "code": None}),
    (ResultQualifierService, ("ICE", "Ice affected"), {"code": "EXT"},
     {"name": "ICE", "description": "Ice affected", "code": "EXT"}),
    (ResultQualifierService, (), {"name": "ICE", "description": "Ice affected", "code": "EXT"},
     {"name": "ICE", "description": "Ice affected", "code": "EXT"}),
    (ProcessingLevelService, ("Raw", "Unprocessed"), {},
     {"name": "Raw", "description": "Unprocessed", "code": None}),
    (ProcessingLevelService, ("Raw", "Unprocessed"), {"code": "0"},
     {"name": "Raw", "description": "Unprocessed", "code": "0"}),
    (ProcessingLevelService, (), {"code": "0", "name": "Raw", "description": "Unprocessed"},
     {"name": "Raw", "description": "Unprocessed", "code": "0"}),
])
def test_metadata_create_argument_mapping(service_class, args, kwargs, expected):
    client = MagicMock(base_route="api/data")
    uid, workspace_id = str(uuid4()), str(uuid4())
    payload = {"id": uid, "workspaceId": workspace_id, **expected}
    client.request.side_effect = [
        MagicMock(json=lambda: {"id": uid}),
        MagicMock(json=lambda: {"data": payload.copy()}),
    ]

    created = service_class(client).create(*args, **kwargs, workspace=workspace_id, uid=uid)

    sent = json.loads(client.request.call_args_list[0].kwargs["data"])
    assert {key: sent[key] for key in expected} == expected
    assert sent["workspaceId"] == workspace_id
    assert sent["id"] == uid
    assert created.name == expected["name"]
    assert created.description == expected["description"]
    assert created.code == expected["code"]


@pytest.mark.parametrize("service_class,args,kwargs,error", [
    (ProcessingLevelService, ("0", "Raw", "Unprocessed"), {}, "positional"),
    (ProcessingLevelService, ("0",), {"name": "Raw", "description": "Unprocessed"}, "name"),
    (ResultQualifierService, ("ICE",), {}, "description"),
    (ResultQualifierService, ("ICE", "Ice affected", str(uuid4())), {}, "positional"),
    (ResultQualifierService, (), {"code": "ICE", "description": "Ice affected"}, "name"),
])
def test_invalid_metadata_create_calls_fail_before_sending_data(service_class, args, kwargs, error):
    client = MagicMock(base_route="api/data")
    with pytest.raises(TypeError, match=error):
        service_class(client).create(*args, **kwargs)
    client.request.assert_not_called()


@pytest.mark.parametrize("service_class,args,kwargs,expected", [
    (ResultQualifierService, ("ICE", "Ice affected"), {},
     {"name": "ICE", "description": "Ice affected"}),
    (ResultQualifierService, ("ICE", "Ice affected", "EXT"), {},
     {"name": "ICE", "description": "Ice affected", "code": "EXT"}),
    (ResultQualifierService, (), {"name": "ICE", "description": "Ice affected", "code": None},
     {"name": "ICE", "description": "Ice affected", "code": None}),
    (ProcessingLevelService, ("0", "Raw", "Unprocessed", "https://example.com/raw"), {},
     {"code": "0", "name": "Raw", "description": "Unprocessed", "definition": "https://example.com/raw"}),
])
def test_metadata_update_preserves_positional_argument_mapping(service_class, args, kwargs, expected):
    client = MagicMock(base_route="api/data")
    uid = str(uuid4())
    payload = {"id": uid, **expected}
    client.request.side_effect = [
        MagicMock(),
        MagicMock(json=lambda: {"data": payload.copy()}),
    ]

    service_class(client).update(uid, *args, **kwargs)

    patch = client.request.call_args_list[0]
    assert patch.args[0] == "patch"
    assert patch.args[1].endswith(f"/{uid}")
    assert json.loads(patch.kwargs["data"]) == expected
