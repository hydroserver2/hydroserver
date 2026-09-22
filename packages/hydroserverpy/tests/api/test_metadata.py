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
