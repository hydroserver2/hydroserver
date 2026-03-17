import pytest
import uuid
from collections import Counter
from ninja.errors import HttpError
from django.http import HttpResponse
from domains.sta.services import SensorService
from interfaces.api.schemas import SensorPostBody, SensorPatchBody, SensorSummaryResponse

sensor_service = SensorService()


@pytest.mark.parametrize(
    "principal, params, sensor_names, max_queries",
    [
        # Test user access
        (
            "owner",
            {},
            [
                "System Sensor",
                "System Assigned Sensor",
                "Public Sensor",
                "Public Assigned Sensor",
                "Private Sensor",
                "Private Assigned Sensor",
            ],
            3,
        ),
        (
            "editor",
            {},
            [
                "System Sensor",
                "System Assigned Sensor",
                "Public Sensor",
                "Public Assigned Sensor",
                "Private Sensor",
                "Private Assigned Sensor",
            ],
            3,
        ),
        (
            "viewer",
            {},
            [
                "System Sensor",
                "System Assigned Sensor",
                "Public Sensor",
                "Public Assigned Sensor",
                "Private Sensor",
                "Private Assigned Sensor",
            ],
            3,
        ),
        (
            "admin",
            {},
            [
                "System Sensor",
                "System Assigned Sensor",
                "Public Sensor",
                "Public Assigned Sensor",
                "Private Sensor",
                "Private Assigned Sensor",
            ],
            3,
        ),
        (
            "apikey",
            {},
            [
                "System Sensor",
                "System Assigned Sensor",
                "Public Sensor",
                "Public Assigned Sensor",
            ],
            4,
        ),
        (
            "unaffiliated",
            {},
            [
                "System Sensor",
                "System Assigned Sensor",
                "Public Sensor",
                "Public Assigned Sensor",
            ],
            3,
        ),
        (
            "anonymous",
            {},
            [
                "System Sensor",
                "System Assigned Sensor",
                "Public Sensor",
                "Public Assigned Sensor",
            ],
            3,
        ),
        # Test pagination and order_by
        (
            "owner",
            {"page": 2, "page_size": 2, "order_by": "-name"},
            [
                "Public Sensor",
                "Public Assigned Sensor",
            ],
            3,
        ),
        # Test filtering
        (
            "owner",
            {"workspace_id": "6e0deaf2-a92b-421b-9ece-86783265596f"},
            ["Public Sensor", "Public Assigned Sensor"],
            3,
        ),
        (
            "owner",
            {"datastreams__thing_id": "3b7818af-eff7-4149-8517-e5cad9dc22e1"},
            ["System Assigned Sensor", "Public Assigned Sensor"],
            3,
        ),
        (
            "owner",
            {"datastreams__id": "27c70b41-e845-40ea-8cc7-d1b40f89816b"},
            ["Public Assigned Sensor"],
            3,
        ),
        ("owner", {"method_type": "System Method"}, ["System Sensor"], 3),
    ],
)
def test_list_sensor(
    django_assert_num_queries,
    get_principal,
    principal,
    params,
    sensor_names,
    max_queries,
):
    with django_assert_num_queries(max_queries):
        http_response = HttpResponse()
        result = sensor_service.list(
            principal=get_principal(principal),
            response=http_response,
            page=params.pop("page", 1),
            page_size=params.pop("page_size", 100),
            order_by=[params.pop("order_by")] if "order_by" in params else [],
            filtering=params,
        )
        assert Counter(str(sensor.name) for sensor in result) == Counter(sensor_names)
        assert (SensorSummaryResponse.from_orm(sensor) for sensor in result)


@pytest.mark.parametrize(
    "principal, sensor, message, error_code",
    [
        # Test public access
        ("owner", "a947c551-8e21-4848-a89b-3048aec69574", "System Sensor", None),
        ("owner", "f87072e1-6ccb-46ec-ab34-befb453140de", "Public Sensor", None),
        ("admin", "a947c551-8e21-4848-a89b-3048aec69574", "System Sensor", None),
        ("admin", "f87072e1-6ccb-46ec-ab34-befb453140de", "Public Sensor", None),
        ("editor", "a947c551-8e21-4848-a89b-3048aec69574", "System Sensor", None),
        ("editor", "f87072e1-6ccb-46ec-ab34-befb453140de", "Public Sensor", None),
        ("viewer", "a947c551-8e21-4848-a89b-3048aec69574", "System Sensor", None),
        ("viewer", "f87072e1-6ccb-46ec-ab34-befb453140de", "Public Sensor", None),
        ("apikey", "a947c551-8e21-4848-a89b-3048aec69574", "System Sensor", None),
        ("apikey", "f87072e1-6ccb-46ec-ab34-befb453140de", "Public Sensor", None),
        ("unaffiliated", "a947c551-8e21-4848-a89b-3048aec69574", "System Sensor", None),
        ("unaffiliated", "f87072e1-6ccb-46ec-ab34-befb453140de", "Public Sensor", None),
        ("anonymous", "a947c551-8e21-4848-a89b-3048aec69574", "System Sensor", None),
        ("anonymous", "f87072e1-6ccb-46ec-ab34-befb453140de", "Public Sensor", None),
        # Test private access
        ("owner", "89a6ae16-9f85-4279-985e-83484db47107", "Private Sensor", None),
        ("admin", "89a6ae16-9f85-4279-985e-83484db47107", "Private Sensor", None),
        # Test unauthorized access
        (
            "apikey",
            "89a6ae16-9f85-4279-985e-83484db47107",
            "Sensor does not exist",
            404,
        ),
        (
            "unaffiliated",
            "89a6ae16-9f85-4279-985e-83484db47107",
            "Sensor does not exist",
            404,
        ),
        (
            "anonymous",
            "89a6ae16-9f85-4279-985e-83484db47107",
            "Sensor does not exist",
            404,
        ),
        # Test missing resource
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            "Sensor does not exist",
            404,
        ),
    ],
)
def test_get_sensor(get_principal, principal, sensor, message, error_code):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            sensor_service.get(
                principal=get_principal(principal), uid=uuid.UUID(sensor)
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        sensor_get = sensor_service.get(
            principal=get_principal(principal), uid=uuid.UUID(sensor)
        )
        assert sensor_get.name == message
        assert SensorSummaryResponse.from_orm(sensor_get)


@pytest.mark.parametrize(
    "principal, sensor_fields, message, error_code",
    [
        # Test create valid Sensor
        ("owner", {}, None, None),
        ("owner", {"workspace_id": "b27c51a0-7374-462d-8a53-d97d47176c10"}, None, None),
        ("editor", {}, None, None),
        (
            "editor",
            {"workspace_id": "b27c51a0-7374-462d-8a53-d97d47176c10"},
            None,
            None,
        ),
        ("admin", {}, None, None),
        ("admin", {"workspace_id": "b27c51a0-7374-462d-8a53-d97d47176c10"}, None, None),
        ("admin", {"workspace_id": None}, None, None),
        # Test create invalid Sensor
        (
            "owner",
            {"workspace_id": "00000000-0000-0000-0000-000000000000"},
            "Workspace does not exist",
            404,
        ),
        # Test unauthorized attempts
        ("owner", {"workspace_id": None}, "You do not have permission", 403),
        ("viewer", {}, "You do not have permission", 403),
        (
            "viewer",
            {"workspace_id": "b27c51a0-7374-462d-8a53-d97d47176c10"},
            "You do not have permission",
            403,
        ),
        ("apikey", {}, "You do not have permission", 403),
        (
            "apikey",
            {"workspace_id": "b27c51a0-7374-462d-8a53-d97d47176c10"},
            "Workspace does not exist",
            404,
        ),
        ("unaffiliated", {}, "You do not have permission", 403),
        (
            "unaffiliated",
            {"workspace_id": "b27c51a0-7374-462d-8a53-d97d47176c10"},
            "Workspace does not exist",
            404,
        ),
        ("anonymous", {}, "You do not have permission", 403),
        (
            "anonymous",
            {"workspace_id": "b27c51a0-7374-462d-8a53-d97d47176c10"},
            "Workspace does not exist",
            404,
        ),
    ],
)
def test_create_sensor(get_principal, principal, sensor_fields, message, error_code):
    sensor_data = SensorPostBody(
        name=sensor_fields.get("name", "New"),
        description=sensor_fields.get("description", "New"),
        encoding_type="application/json",
        method_type=sensor_fields.get("method_type", "New"),
        workspace_id=(
            (
                uuid.UUID(wid)
                if (wid := sensor_fields["workspace_id"]) is not None
                else None
            )
            if "workspace_id" in sensor_fields
            else uuid.UUID("6e0deaf2-a92b-421b-9ece-86783265596f")
        ),
    )
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            sensor_service.create(principal=get_principal(principal), data=sensor_data)
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        sensor_create = sensor_service.create(
            principal=get_principal(principal), data=sensor_data
        )
        assert sensor_create.name == sensor_data.name
        assert sensor_create.description == sensor_data.description
        assert sensor_create.method_type == sensor_data.method_type
        assert SensorSummaryResponse.from_orm(sensor_create)


@pytest.mark.parametrize(
    "principal, sensor, sensor_fields, message, error_code",
    [
        # Test edit Sensor
        ("owner", "f87072e1-6ccb-46ec-ab34-befb453140de", {}, None, None),
        ("editor", "f87072e1-6ccb-46ec-ab34-befb453140de", {}, None, None),
        ("admin", "f87072e1-6ccb-46ec-ab34-befb453140de", {}, None, None),
        # Test unauthorized attempts
        (
            "viewer",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            {},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "a947c551-8e21-4848-a89b-3048aec69574",
            {},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "89a6ae16-9f85-4279-985e-83484db47107",
            {},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            {},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "a947c551-8e21-4848-a89b-3048aec69574",
            {},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "89a6ae16-9f85-4279-985e-83484db47107",
            {},
            "Sensor does not exist",
            404,
        ),
        (
            "unaffiliated",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            {},
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "a947c551-8e21-4848-a89b-3048aec69574",
            {},
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "89a6ae16-9f85-4279-985e-83484db47107",
            {},
            "Sensor does not exist",
            404,
        ),
        (
            "anonymous",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            {},
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "a947c551-8e21-4848-a89b-3048aec69574",
            {},
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "89a6ae16-9f85-4279-985e-83484db47107",
            {},
            "Sensor does not exist",
            404,
        ),
    ],
)
def test_edit_sensor(
    get_principal, principal, sensor, sensor_fields, message, error_code
):
    sensor_data = SensorPatchBody(
        name=sensor_fields.get("name", "New"),
        description=sensor_fields.get("description", "New"),
        encoding_type="application/json",
        method_type=sensor_fields.get("method_type", "New"),
    )
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            sensor_service.update(
                principal=get_principal(principal),
                uid=uuid.UUID(sensor),
                data=sensor_data,
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        sensor_update = sensor_service.update(
            principal=get_principal(principal), uid=uuid.UUID(sensor), data=sensor_data
        )
        assert sensor_update.name == sensor_data.name
        assert sensor_update.description == sensor_data.description
        assert sensor_update.method_type == sensor_data.method_type
        assert SensorSummaryResponse.from_orm(sensor_update)


@pytest.mark.parametrize(
    "principal, sensor, message, error_code",
    [
        # Test delete Sensor
        ("owner", "f87072e1-6ccb-46ec-ab34-befb453140de", None, None),
        ("editor", "f87072e1-6ccb-46ec-ab34-befb453140de", None, None),
        ("admin", "f87072e1-6ccb-46ec-ab34-befb453140de", None, None),
        # Test unauthorized attempts
        (
            "viewer",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "89a6ae16-9f85-4279-985e-83484db47107",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "89a6ae16-9f85-4279-985e-83484db47107",
            "Sensor does not exist",
            404,
        ),
        (
            "unaffiliated",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "89a6ae16-9f85-4279-985e-83484db47107",
            "Sensor does not exist",
            404,
        ),
        (
            "anonymous",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "89a6ae16-9f85-4279-985e-83484db47107",
            "Sensor does not exist",
            404,
        ),
    ],
)
def test_delete_sensor(get_principal, principal, sensor, message, error_code):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            sensor_service.delete(
                principal=get_principal(principal), uid=uuid.UUID(sensor)
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        sensor_delete = sensor_service.delete(
            principal=get_principal(principal), uid=uuid.UUID(sensor)
        )
        assert sensor_delete == "Sensor deleted"
