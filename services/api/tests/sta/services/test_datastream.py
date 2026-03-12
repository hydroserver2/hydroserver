import pytest
import uuid
from collections import Counter
from ninja.errors import HttpError
from django.http import HttpResponse
from domains.sta.services import DatastreamService
from interfaces.api.schemas import (
    DatastreamPostBody,
    DatastreamPatchBody,
    DatastreamSummaryResponse,
    TagPostBody,
    TagDeleteBody,
)

datastream_service = DatastreamService()


@pytest.mark.parametrize(
    "principal, params, datastream_names, max_queries",
    [
        # Test user access
        (
            "owner",
            {},
            [
                "Public Datastream 1",
                "Private Datastream 1",
                "Private Datastream 2",
                "Private Datastream 3",
                "Private Datastream 4",
                "Private Datastream 5",
                "Private Datastream 6",
                "Private Datastream 7",
                "Public Datastream 2",
            ],
            5,
        ),
        (
            "editor",
            {},
            [
                "Public Datastream 1",
                "Private Datastream 1",
                "Private Datastream 2",
                "Private Datastream 3",
                "Private Datastream 4",
                "Private Datastream 5",
                "Private Datastream 6",
                "Private Datastream 7",
                "Public Datastream 2",
            ],
            5,
        ),
        (
            "viewer",
            {},
            [
                "Public Datastream 1",
                "Private Datastream 1",
                "Private Datastream 2",
                "Private Datastream 3",
                "Private Datastream 4",
                "Private Datastream 5",
                "Private Datastream 6",
                "Private Datastream 7",
                "Public Datastream 2",
            ],
            5,
        ),
        (
            "admin",
            {},
            [
                "Public Datastream 1",
                "Private Datastream 1",
                "Private Datastream 2",
                "Private Datastream 3",
                "Private Datastream 4",
                "Private Datastream 5",
                "Private Datastream 6",
                "Private Datastream 7",
                "Public Datastream 2",
            ],
            5,
        ),
        (
            "apikey",
            {},
            [
                "Public Datastream 1",
                "Public Datastream 2",
                "Private Datastream 1",
                "Private Datastream 2",
                "Private Datastream 3",
            ],
            6,
        ),
        ("unaffiliated", {}, ["Public Datastream 1", "Public Datastream 2"], 5),
        ("anonymous", {}, ["Public Datastream 1", "Public Datastream 2"], 5),
        # Test pagination and order_by
        (
            "owner",
            {"page": 2, "page_size": 2, "order_by": "-name"},
            ["Private Datastream 7", "Private Datastream 6"],
            6,
        ),
        # Test filtering
        (
            "owner",
            {"thing__workspace_id": "b27c51a0-7374-462d-8a53-d97d47176c10"},
            [
                "Private Datastream 4",
                "Private Datastream 5",
                "Private Datastream 6",
                "Private Datastream 7",
            ],
            5,
        ),
        (
            "owner",
            {"thing_id": "3b7818af-eff7-4149-8517-e5cad9dc22e1"},
            ["Public Datastream 1", "Private Datastream 1", "Public Datastream 2"],
            5,
        ),
        (
            "owner",
            {"sampled_medium": "Air"},
            ["Private Datastream 1", "Private Datastream 3"],
            5,
        ),
        (
            "owner",
            {"is_private": False},
            ["Public Datastream 1", "Public Datastream 2"],
            5,
        ),
        ("owner", {"value_count__gte": "3", "value_count__lte": "1"}, [], 3),
        (
            "owner",
            {
                "phenomenon_begin_time__gte": "2025-02-10 02:00:00.000 -0700",
                "phenomenon_begin_time__lte": "2025-02-10 00:00:00.000 -0700",
            },
            [],
            5,
        ),
    ],
)
def test_list_datastream(
    django_assert_max_num_queries,
    get_principal,
    principal,
    params,
    datastream_names,
    max_queries,
):
    with django_assert_max_num_queries(max_queries):
        http_response = HttpResponse()
        result = datastream_service.list(
            principal=get_principal(principal),
            response=http_response,
            page=params.pop("page", 1),
            page_size=params.pop("page_size", 100),
            order_by=[params.pop("order_by")] if "order_by" in params else [],
            filtering=params,
        )
        assert Counter(str(datastream.name) for datastream in result) == Counter(
            datastream_names
        )
        assert (DatastreamSummaryResponse.from_orm(thing) for thing in result)


@pytest.mark.parametrize(
    "principal, datastream, message, error_code",
    [
        # Test public access
        ("owner", "27c70b41-e845-40ea-8cc7-d1b40f89816b", "Public Datastream 1", None),
        ("editor", "27c70b41-e845-40ea-8cc7-d1b40f89816b", "Public Datastream 1", None),
        ("viewer", "27c70b41-e845-40ea-8cc7-d1b40f89816b", "Public Datastream 1", None),
        ("admin", "27c70b41-e845-40ea-8cc7-d1b40f89816b", "Public Datastream 1", None),
        ("apikey", "27c70b41-e845-40ea-8cc7-d1b40f89816b", "Public Datastream 1", None),
        (
            "unaffiliated",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            "Public Datastream 1",
            None,
        ),
        (
            "anonymous",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            "Public Datastream 1",
            None,
        ),
        # Test private access
        ("owner", "e0506cac-3e50-4d0a-814d-7ae0146705b2", "Private Datastream 1", None),
        ("owner", "cad40a75-99ca-4317-b534-0fc7880c905f", "Private Datastream 2", None),
        ("owner", "dd1f9293-ce29-4b6a-88e6-d65110d1be65", "Private Datastream 4", None),
        ("owner", "9f96957b-ee20-4c7b-bf2b-673a0cda3a04", "Private Datastream 7", None),
        ("admin", "e0506cac-3e50-4d0a-814d-7ae0146705b2", "Private Datastream 1", None),
        ("admin", "cad40a75-99ca-4317-b534-0fc7880c905f", "Private Datastream 2", None),
        ("admin", "dd1f9293-ce29-4b6a-88e6-d65110d1be65", "Private Datastream 4", None),
        ("admin", "9f96957b-ee20-4c7b-bf2b-673a0cda3a04", "Private Datastream 7", None),
        # Test unauthorized access
        (
            "unaffiliated",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            "Datastream does not exist",
            404,
        ),
        (
            "unaffiliated",
            "cad40a75-99ca-4317-b534-0fc7880c905f",
            "Datastream does not exist",
            404,
        ),
        (
            "unaffiliated",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            "Datastream does not exist",
            404,
        ),
        (
            "unaffiliated",
            "9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "cad40a75-99ca-4317-b534-0fc7880c905f",
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
            "Datastream does not exist",
            404,
        ),
        # Test missing resource
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            "Datastream does not exist",
            404,
        ),
    ],
)
def test_get_datastream(get_principal, principal, datastream, message, error_code):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            datastream_service.get(
                principal=get_principal(principal), uid=uuid.UUID(datastream)
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        datastream_get = datastream_service.get(
            principal=get_principal(principal), uid=uuid.UUID(datastream)
        )
        assert datastream_get.name == message
        assert DatastreamSummaryResponse.from_orm(datastream_get)


@pytest.mark.parametrize(
    "principal, thing, observed_property, processing_level, sensor, unit, message, error_code",
    [
        # Owner can create datastream with system metadata
        (
            "owner",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            None,
            None,
        ),
        # Owner can create datastream with workspace metadata
        (
            "owner",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            None,
            None,
        ),
        # Owner can't create datastream with metadata from another workspace
        (
            "owner",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "5dbfd184-ae79-4c05-a9ea-3f5e775ecbc1",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            "The given observed property cannot be associated",
            400,
        ),
        (
            "owner",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "fa3c97ce-41b8-4c12-b91a-9127ce0c083a",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            "The given processing level cannot be associated",
            400,
        ),
        (
            "owner",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "89a6ae16-9f85-4279-985e-83484db47107",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            "The given sensor cannot be associated",
            400,
        ),
        (
            "owner",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "98a74429-2be2-44c0-8f7f-2df2ca12893d",
            "The given unit cannot be associated",
            400,
        ),
        # Owner can't create datastream with non-existent metadata
        (
            "owner",
            "00000000-0000-0000-0000-000000000000",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            "Thing does not exist",
            400,
        ),
        (
            "owner",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "00000000-0000-0000-0000-000000000000",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            "Observed property does not exist",
            400,
        ),
        (
            "owner",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "00000000-0000-0000-0000-000000000000",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            "Processing level does not exist",
            400,
        ),
        (
            "owner",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "00000000-0000-0000-0000-000000000000",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            "Sensor does not exist",
            400,
        ),
        (
            "owner",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "00000000-0000-0000-0000-000000000000",
            "Unit does not exist",
            400,
        ),
        # Admin can create datastream with system metadata
        (
            "admin",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            None,
            None,
        ),
        # Admin can create datastream with workspace metadata
        (
            "admin",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            None,
            None,
        ),
        # Admin can't create datastream with metadata from another workspace
        (
            "admin",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "5dbfd184-ae79-4c05-a9ea-3f5e775ecbc1",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            "The given observed property cannot be associated",
            400,
        ),
        (
            "admin",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "fa3c97ce-41b8-4c12-b91a-9127ce0c083a",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            "The given processing level cannot be associated",
            400,
        ),
        (
            "admin",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "89a6ae16-9f85-4279-985e-83484db47107",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            "The given sensor cannot be associated",
            400,
        ),
        (
            "admin",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "98a74429-2be2-44c0-8f7f-2df2ca12893d",
            "The given unit cannot be associated",
            400,
        ),
        # Admin can't create datastream with non-existent metadata
        (
            "admin",
            "00000000-0000-0000-0000-000000000000",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            "Thing does not exist",
            400,
        ),
        (
            "admin",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "00000000-0000-0000-0000-000000000000",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            "Observed property does not exist",
            400,
        ),
        (
            "admin",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "00000000-0000-0000-0000-000000000000",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            "Processing level does not exist",
            400,
        ),
        (
            "admin",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "00000000-0000-0000-0000-000000000000",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            "Sensor does not exist",
            400,
        ),
        (
            "admin",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "00000000-0000-0000-0000-000000000000",
            "Unit does not exist",
            400,
        ),
        # Editor can create datastream with system metadata
        (
            "editor",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            None,
            None,
        ),
        # Editor can create datastream with workspace metadata
        (
            "editor",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "aa2d8fa4-461f-48a4-8bfe-13b6ae6fa575",
            "f87072e1-6ccb-46ec-ab34-befb453140de",
            "fe3799b7-f061-42f2-b012-b569303f8a41",
            None,
            None,
        ),
        # Viewer cannot create datastreams
        (
            "viewer",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "You do not have permission",
            403,
        ),
        # API keys cannot create datastreams
        (
            "apikey",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "Thing does not exist",
            400,
        ),
        (
            "apikey",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "Thing does not exist",
            400,
        ),
        (
            "apikey",
            "00000000-0000-0000-0000-000000000000",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "Thing does not exist",
            400,
        ),
        # Anonymous cannot create datastreams
        (
            "anonymous",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "Thing does not exist",
            400,
        ),
        (
            "anonymous",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "Thing does not exist",
            400,
        ),
        (
            "anonymous",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "Thing does not exist",
            400,
        ),
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "Thing does not exist",
            400,
        ),
        # Unauthenticated principals cannot create datastreams
        (
            None,
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "You do not have permission",
            403,
        ),
        (
            None,
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "Thing does not exist",
            400,
        ),
        (
            None,
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "Thing does not exist",
            400,
        ),
        (
            None,
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "Thing does not exist",
            400,
        ),
        (
            None,
            "00000000-0000-0000-0000-000000000000",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "1cb782af-6097-4a3f-9988-5fcbfcb5a327",
            "a947c551-8e21-4848-a89b-3048aec69574",
            "2ca850fa-ce19-4d8a-9dfd-8d54a261778d",
            "Thing does not exist",
            400,
        ),
    ],
)
def test_create_datastream(
    get_principal,
    principal,
    thing,
    observed_property,
    processing_level,
    sensor,
    unit,
    message,
    error_code,
):
    datastream_data = DatastreamPostBody(
        thing_id=uuid.UUID(thing),
        observed_property_id=uuid.UUID(observed_property),
        processing_level_id=uuid.UUID(processing_level),
        sensor_id=uuid.UUID(sensor),
        unit_id=uuid.UUID(unit),
        name="New Datastream",
        description="New Datastream",
        observation_type="Observation",
        sampled_medium="Air",
        no_data_value=-9999,
        aggregation_statistic="Average",
        time_aggregation_interval=15,
        time_aggregation_interval_unit="minutes",
        result_type="Time Series",
    )
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            datastream_service.create(
                principal=get_principal(principal), data=datastream_data
            )
        assert exc_info.value.status_code == error_code
        if isinstance(message, str):
            assert exc_info.value.message.startswith(message)
    else:
        datastream_create = datastream_service.create(
            principal=get_principal(principal), data=datastream_data
        )
        assert datastream_create.name == datastream_data.name
        assert datastream_create.description == datastream_data.description
        assert (
            datastream_create.observed_property_id
            == datastream_data.observed_property_id
        )
        assert (
            datastream_create.processing_level_id == datastream_data.processing_level_id
        )
        assert datastream_create.sensor_id == datastream_data.sensor_id
        assert datastream_create.unit_id == datastream_data.unit_id
        assert datastream_create.observation_type == datastream_data.observation_type
        assert (
            datastream_create.time_aggregation_interval
            == datastream_data.time_aggregation_interval
        )
        assert datastream_create.sampled_medium == datastream_data.sampled_medium
        assert datastream_create.no_data_value == datastream_data.no_data_value
        assert (
            datastream_create.aggregation_statistic
            == datastream_data.aggregation_statistic
        )
        assert (
            datastream_create.time_aggregation_interval
            == datastream_data.time_aggregation_interval
        )
        assert (
            datastream_create.time_aggregation_interval_unit
            == datastream_data.time_aggregation_interval_unit
        )
        assert datastream_create.result_type == datastream_data.result_type
        assert DatastreamSummaryResponse.from_orm(datastream_create)


@pytest.mark.parametrize(
    "principal, datastream, thing, observed_property, processing_level, sensor, unit, message, error_code",
    [
        # Owners, editors, and admins can assign system and workspace metadata to public and private datastreams
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "owner",
            "9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "owner",
            "9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "admin",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "admin",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "admin",
            "9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "admin",
            "9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "editor",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "editor",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "editor",
            "9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "editor",
            "9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        # Owners, editors, and admins cannot assign metadata from other workspaces to datastreams
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            None,
            None,
            None,
            None,
            "You cannot associate this datastream with a thing in another workspace",
            400,
        ),
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            "5dbfd184-ae79-4c05-a9ea-3f5e775ecbc1",
            None,
            None,
            None,
            "The given observed property cannot be associated",
            400,
        ),
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            "fa3c97ce-41b8-4c12-b91a-9127ce0c083a",
            None,
            None,
            "The given processing level cannot be associated",
            400,
        ),
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            "89a6ae16-9f85-4279-985e-83484db47107",
            None,
            "The given sensor cannot be associated",
            400,
        ),
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            None,
            "98a74429-2be2-44c0-8f7f-2df2ca12893d",
            "The given unit cannot be associated",
            400,
        ),
        (
            "admin",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            None,
            None,
            None,
            None,
            "You cannot associate this datastream with a thing in another workspace",
            400,
        ),
        (
            "admin",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            "5dbfd184-ae79-4c05-a9ea-3f5e775ecbc1",
            None,
            None,
            None,
            "The given observed property cannot be associated",
            400,
        ),
        (
            "admin",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            "fa3c97ce-41b8-4c12-b91a-9127ce0c083a",
            None,
            None,
            "The given processing level cannot be associated",
            400,
        ),
        (
            "admin",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            "89a6ae16-9f85-4279-985e-83484db47107",
            None,
            "The given sensor cannot be associated",
            400,
        ),
        (
            "admin",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            None,
            "98a74429-2be2-44c0-8f7f-2df2ca12893d",
            "The given unit cannot be associated",
            400,
        ),
        (
            "editor",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            None,
            None,
            None,
            None,
            "You cannot associate this datastream with a thing in another workspace",
            400,
        ),
        (
            "editor",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            "5dbfd184-ae79-4c05-a9ea-3f5e775ecbc1",
            None,
            None,
            None,
            "The given observed property cannot be associated",
            400,
        ),
        (
            "editor",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            "fa3c97ce-41b8-4c12-b91a-9127ce0c083a",
            None,
            None,
            "The given processing level cannot be associated",
            400,
        ),
        (
            "editor",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            "89a6ae16-9f85-4279-985e-83484db47107",
            None,
            "The given sensor cannot be associated",
            400,
        ),
        (
            "editor",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            None,
            "98a74429-2be2-44c0-8f7f-2df2ca12893d",
            "The given unit cannot be associated",
            400,
        ),
        # Owners, editors, and admins cannot assign non-existent metadata to datastreams
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            "00000000-0000-0000-0000-000000000000",
            None,
            None,
            None,
            None,
            "Thing does not exist",
            400,
        ),
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            "00000000-0000-0000-0000-000000000000",
            None,
            None,
            None,
            "Observed property does not exist",
            400,
        ),
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            "00000000-0000-0000-0000-000000000000",
            None,
            None,
            "Processing level does not exist",
            400,
        ),
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            "00000000-0000-0000-0000-000000000000",
            None,
            "Sensor does not exist",
            400,
        ),
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            None,
            "00000000-0000-0000-0000-000000000000",
            "Unit does not exist",
            400,
        ),
        (
            "admin",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            "00000000-0000-0000-0000-000000000000",
            None,
            None,
            None,
            None,
            "Thing does not exist",
            400,
        ),
        (
            "admin",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            "00000000-0000-0000-0000-000000000000",
            None,
            None,
            None,
            "Observed property does not exist",
            400,
        ),
        (
            "admin",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            "00000000-0000-0000-0000-000000000000",
            None,
            None,
            "Processing level does not exist",
            400,
        ),
        (
            "admin",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            "00000000-0000-0000-0000-000000000000",
            None,
            "Sensor does not exist",
            400,
        ),
        (
            "admin",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            None,
            "00000000-0000-0000-0000-000000000000",
            "Unit does not exist",
            400,
        ),
        (
            "editor",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            "00000000-0000-0000-0000-000000000000",
            None,
            None,
            None,
            None,
            "Thing does not exist",
            400,
        ),
        (
            "editor",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            "00000000-0000-0000-0000-000000000000",
            None,
            None,
            None,
            "Observed property does not exist",
            400,
        ),
        (
            "editor",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            "00000000-0000-0000-0000-000000000000",
            None,
            None,
            "Processing level does not exist",
            400,
        ),
        (
            "editor",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            "00000000-0000-0000-0000-000000000000",
            None,
            "Sensor does not exist",
            400,
        ),
        (
            "editor",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            None,
            "00000000-0000-0000-0000-000000000000",
            "Unit does not exist",
            400,
        ),
        # Viewers and anonymous cannot edit datastreams
        (
            "viewer",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            None,
            None,
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
            None,
            None,
            None,
            None,
            None,
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "apikey",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "apikey",
            "cad40a75-99ca-4317-b534-0fc7880c905f",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "apikey",
            "fcd47d93-4cae-411a-9e1e-26ef473840ed",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "apikey",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            "apikey",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            "apikey",
            "42e08eea-27bb-4ea3-8ced-63acff0f3334",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            "apikey",
            "9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            "apikey",
            "00000000-0000-0000-0000-000000000000",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            None,
            None,
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "cad40a75-99ca-4317-b534-0fc7880c905f",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "fcd47d93-4cae-411a-9e1e-26ef473840ed",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "42e08eea-27bb-4ea3-8ced-63acff0f3334",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            None,
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            None,
            None,
            None,
            None,
            None,
            "You do not have permission",
            403,
        ),
        (
            None,
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            None,
            "cad40a75-99ca-4317-b534-0fc7880c905f",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            None,
            "fcd47d93-4cae-411a-9e1e-26ef473840ed",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            None,
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            None,
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            None,
            "42e08eea-27bb-4ea3-8ced-63acff0f3334",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            None,
            "9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
        (
            None,
            "00000000-0000-0000-0000-000000000000",
            None,
            None,
            None,
            None,
            None,
            "Datastream does not exist",
            404,
        ),
    ],
)
def test_edit_datastream(
    get_principal,
    principal,
    datastream,
    thing,
    observed_property,
    processing_level,
    sensor,
    unit,
    message,
    error_code,
):
    datastream_dict = {}
    if thing:
        datastream_dict["thing_id"] = uuid.UUID(thing)
    if observed_property:
        datastream_dict["observed_property_id"] = uuid.UUID(observed_property)
    if processing_level:
        datastream_dict["processing_level_id"] = uuid.UUID(processing_level)
    if sensor:
        datastream_dict["sensor_id"] = uuid.UUID(sensor)
    if unit:
        datastream_dict["unit_id"] = uuid.UUID(unit)
    datastream_data = DatastreamPatchBody(**datastream_dict)
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            datastream_service.update(
                principal=get_principal(principal),
                uid=uuid.UUID(datastream),
                data=datastream_data,
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        datastream_update = datastream_service.update(
            principal=get_principal(principal),
            uid=uuid.UUID(datastream),
            data=datastream_data,
        )
        if thing:
            assert datastream_update.thing_id == datastream_data.thing_id
        if observed_property:
            assert (
                datastream_update.observed_property_id
                == datastream_data.observed_property_id
            )
        if processing_level:
            assert (
                datastream_update.processing_level_id
                == datastream_data.processing_level_id
            )
        if sensor:
            assert datastream_update.sensor_id == datastream_data.sensor_id
        if unit:
            assert datastream_update.unit_id == datastream_data.unit_id


@pytest.mark.parametrize(
    "principal, datastream, message, error_code, max_queries",
    [
        # Owners, admins, editors can delete public and private datastreams
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            "Public Datastream 1",
            None,
            14,
        ),
        (
            "owner",
            "9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
            "Private Datastream 7",
            None,
            14,
        ),
        (
            "admin",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            "Public Datastream 1",
            None,
            14,
        ),
        (
            "admin",
            "9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
            "Private Datastream 7",
            None,
            14,
        ),
        (
            "editor",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            "Public Datastream 1",
            None,
            14,
        ),
        (
            "editor",
            "9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
            "Private Datastream 7",
            None,
            14,
        ),
        # Anonymous and viewers cannot delete datastreams
        (
            "viewer",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            "You do not have permission",
            403,
            7,
        ),
        (
            "viewer",
            "9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
            "You do not have permission",
            403,
            7,
        ),
        (
            "apikey",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            "You do not have permission",
            403,
            8,
        ),
        (
            "apikey",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            "You do not have permission",
            403,
            8,
        ),
        (
            "apikey",
            "cad40a75-99ca-4317-b534-0fc7880c905f",
            "You do not have permission",
            403,
            8,
        ),
        (
            "apikey",
            "fcd47d93-4cae-411a-9e1e-26ef473840ed",
            "You do not have permission",
            403,
            8,
        ),
        (
            "apikey",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            "Datastream does not exist",
            404,
            8,
        ),
        (
            "apikey",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            "Datastream does not exist",
            404,
            8,
        ),
        (
            "apikey",
            "42e08eea-27bb-4ea3-8ced-63acff0f3334",
            "Datastream does not exist",
            404,
            8,
        ),
        (
            "apikey",
            "9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
            "Datastream does not exist",
            404,
            8,
        ),
        (
            "apikey",
            "00000000-0000-0000-0000-000000000000",
            "Datastream does not exist",
            404,
            8,
        ),
        (
            "anonymous",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            "You do not have permission",
            403,
            5,
        ),
        (
            "anonymous",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            "Datastream does not exist",
            404,
            5,
        ),
        (
            "anonymous",
            "cad40a75-99ca-4317-b534-0fc7880c905f",
            "Datastream does not exist",
            404,
            5,
        ),
        (
            "anonymous",
            "fcd47d93-4cae-411a-9e1e-26ef473840ed",
            "Datastream does not exist",
            404,
            5,
        ),
        (
            "anonymous",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            "Datastream does not exist",
            404,
            5,
        ),
        (
            "anonymous",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            "Datastream does not exist",
            404,
            5,
        ),
        (
            "anonymous",
            "42e08eea-27bb-4ea3-8ced-63acff0f3334",
            "Datastream does not exist",
            404,
            5,
        ),
        (
            "anonymous",
            "9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
            "Datastream does not exist",
            404,
            5,
        ),
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            "Datastream does not exist",
            404,
            5,
        ),
        (
            None,
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            "You do not have permission",
            403,
            5,
        ),
        (
            None,
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            "Datastream does not exist",
            404,
            5,
        ),
        (
            None,
            "cad40a75-99ca-4317-b534-0fc7880c905f",
            "Datastream does not exist",
            404,
            5,
        ),
        (
            None,
            "fcd47d93-4cae-411a-9e1e-26ef473840ed",
            "Datastream does not exist",
            404,
            5,
        ),
        (
            None,
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            "Datastream does not exist",
            404,
            5,
        ),
        (
            None,
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            "Datastream does not exist",
            404,
            5,
        ),
        (
            None,
            "42e08eea-27bb-4ea3-8ced-63acff0f3334",
            "Datastream does not exist",
            404,
            5,
        ),
        (
            None,
            "9f96957b-ee20-4c7b-bf2b-673a0cda3a04",
            "Datastream does not exist",
            404,
            5,
        ),
        (
            None,
            "00000000-0000-0000-0000-000000000000",
            "Datastream does not exist",
            404,
            5,
        ),
    ],
)
def test_delete_datastream(
    django_assert_max_num_queries,
    get_principal,
    principal,
    datastream,
    message,
    error_code,
    max_queries,
):
    with django_assert_max_num_queries(max_queries):
        if error_code:
            with pytest.raises(HttpError) as exc_info:
                datastream_service.delete(
                    principal=get_principal(principal), uid=uuid.UUID(datastream)
                )
            assert exc_info.value.status_code == error_code
            assert exc_info.value.message.startswith(message)
        else:
            datastream_delete = datastream_service.delete(
                principal=get_principal(principal), uid=uuid.UUID(datastream)
            )
            assert datastream_delete == "Datastream deleted"


@pytest.mark.parametrize(
    "principal, datastream, message, error_code",
    [
        ("owner", "27c70b41-e845-40ea-8cc7-d1b40f89816b", None, None),
        ("owner", "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2", None, None),
        ("owner", "e0506cac-3e50-4d0a-814d-7ae0146705b2", None, None),
        ("owner", "dd1f9293-ce29-4b6a-88e6-d65110d1be65", None, None),
        ("admin", "27c70b41-e845-40ea-8cc7-d1b40f89816b", None, None),
        ("admin", "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2", None, None),
        ("admin", "e0506cac-3e50-4d0a-814d-7ae0146705b2", None, None),
        ("admin", "dd1f9293-ce29-4b6a-88e6-d65110d1be65", None, None),
        ("editor", "27c70b41-e845-40ea-8cc7-d1b40f89816b", None, None),
        ("editor", "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2", None, None),
        ("editor", "e0506cac-3e50-4d0a-814d-7ae0146705b2", None, None),
        ("editor", "dd1f9293-ce29-4b6a-88e6-d65110d1be65", None, None),
        ("viewer", "27c70b41-e845-40ea-8cc7-d1b40f89816b", None, None),
        ("viewer", "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2", None, None),
        ("viewer", "e0506cac-3e50-4d0a-814d-7ae0146705b2", None, None),
        ("viewer", "dd1f9293-ce29-4b6a-88e6-d65110d1be65", None, None),
        ("apikey", "27c70b41-e845-40ea-8cc7-d1b40f89816b", None, None),
        (
            "apikey",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            "Datastream does not exist",
            404,
        ),
        (
            "apikey",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            None,
            None,
        ),
        (
            "apikey",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            "Datastream does not exist",
            404,
        ),
        ("anonymous", "27c70b41-e845-40ea-8cc7-d1b40f89816b", None, None),
        (
            "unaffiliated",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            "Datastream does not exist",
            404,
        ),
        (
            "unaffiliated",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            "Datastream does not exist",
            404,
        ),
        (
            "unaffiliated",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            "Datastream does not exist",
            404,
        ),
        ("anonymous", "27c70b41-e845-40ea-8cc7-d1b40f89816b", None, None),
        (
            "anonymous",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            "Datastream does not exist",
            404,
        ),
    ],
)
def test_get_datastream_tags(get_principal, principal, datastream, message, error_code):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            datastream_service.get_tags(
                principal=get_principal(principal), uid=uuid.UUID(datastream)
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        datastream_tags = datastream_service.get_tags(
            principal=get_principal(principal), uid=uuid.UUID(datastream)
        )
        assert set([tag.key for tag in datastream_tags]).issubset(
            ["Test Public Key", "Test Private Key"]
        )
        assert set([tag.value for tag in datastream_tags]).issubset(
            ["Test Public Value", "Test Private Value"]
        )


@pytest.mark.parametrize(
    "principal, workspace, datastream, length, max_queries",
    [
        ("owner", None, None, 2, 2),
        ("owner", "b27c51a0-7374-462d-8a53-d97d47176c10", None, 1, 2),
        ("owner", None, "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2", 1, 2),
        (
            "owner",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            0,
            2,
        ),
        ("admin", None, None, 2, 2),
        ("admin", "b27c51a0-7374-462d-8a53-d97d47176c10", None, 1, 2),
        ("admin", None, "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2", 1, 2),
        (
            "admin",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            0,
            2,
        ),
        ("editor", None, None, 2, 2),
        ("editor", "b27c51a0-7374-462d-8a53-d97d47176c10", None, 1, 2),
        ("editor", None, "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2", 1, 2),
        (
            "editor",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            0,
            2,
        ),
        ("viewer", None, None, 2, 2),
        ("viewer", "b27c51a0-7374-462d-8a53-d97d47176c10", None, 1, 2),
        ("viewer", None, "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2", 1, 2),
        (
            "viewer",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            0,
            2,
        ),
        ("apikey", None, None, 2, 3),
        ("apikey", "b27c51a0-7374-462d-8a53-d97d47176c10", None, 0, 3),
        ("apikey", None, "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2", 0, 3),
        (
            "apikey",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            0,
            3,
        ),
        ("anonymous", None, None, 2, 2),
        ("anonymous", "b27c51a0-7374-462d-8a53-d97d47176c10", None, 0, 2),
        ("anonymous", None, "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2", 0, 2),
        (
            "anonymous",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            0,
            2,
        ),
        (None, None, None, 2, 2),
        (None, "b27c51a0-7374-462d-8a53-d97d47176c10", None, 0, 2),
        (None, None, "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2", 0, 2),
        (
            None,
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            0,
            2,
        ),
    ],
)
def test_get_datastream_tag_keys(
    django_assert_num_queries,
    get_principal,
    principal,
    workspace,
    datastream,
    length,
    max_queries,
):
    with django_assert_num_queries(max_queries):
        tag_key_list = datastream_service.get_tag_keys(
            principal=get_principal(principal),
            workspace_id=uuid.UUID(workspace) if workspace else None,
            datastream_id=uuid.UUID(datastream) if datastream else None,
        )
        assert len(tag_key_list) == length
        assert (isinstance(str, tag_key) for tag_key in tag_key_list)


@pytest.mark.parametrize(
    "principal, datastream, tag, message, error_code",
    [
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "New Key", "value": "Test Value"},
            None,
            None,
        ),
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "Test Public Key", "value": "Test Public Value"},
            "Tag already exists",
            400,
        ),
        (
            "owner",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "owner",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "owner",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "admin",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "admin",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "admin",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "admin",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "editor",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "editor",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "editor",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "editor",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "viewer",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "New Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "New Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            {"key": "New Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "New Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "New Key", "value": "New Value"},
            "Datastream does not exist",
            404,
        ),
        (
            "apikey",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "New Key", "value": "New Value"},
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "New Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "New Key", "value": "New Value"},
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            {"key": "New Key", "value": "New Value"},
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "New Key", "value": "New Value"},
            "Datastream does not exist",
            404,
        ),
        (
            None,
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "New Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            None,
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "New Key", "value": "New Value"},
            "Datastream does not exist",
            404,
        ),
        (
            None,
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            {"key": "New Key", "value": "New Value"},
            "Datastream does not exist",
            404,
        ),
        (
            None,
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "New Key", "value": "New Value"},
            "Datastream does not exist",
            404,
        ),
    ],
)
def test_add_datastream_tag(
    get_principal, principal, datastream, tag, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            datastream_service.add_tag(
                principal=get_principal(principal),
                uid=uuid.UUID(datastream),
                data=TagPostBody(key=tag["key"], value=tag["value"]),
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        datastream_tag = datastream_service.add_tag(
            principal=get_principal(principal),
            uid=uuid.UUID(datastream),
            data=TagPostBody(key=tag["key"], value=tag["value"]),
        )

        assert datastream_tag.key == tag["key"]
        assert datastream_tag.value == tag["value"]


@pytest.mark.parametrize(
    "principal, datastream, tag, message, error_code",
    [
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "Test Public Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "Test Public Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "New Key", "value": "New Value"},
            "Tag does not exist",
            404,
        ),
        (
            "owner",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "Test Private Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "owner",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            {"key": "Test Private Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "owner",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "Test Private Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "admin",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "Test Public Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "admin",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "Test Private Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "admin",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            {"key": "Test Private Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "admin",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "Test Private Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "editor",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "Test Public Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "editor",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "Test Private Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "editor",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            {"key": "Test Private Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "editor",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "Test Private Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "viewer",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "Test Public Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "Test Private Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            {"key": "Test Private Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "Test Private Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "Test Private Key", "value": "New Value"},
            "Datastream does not exist",
            404,
        ),
        (
            "apikey",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "Test Private Key", "value": "New Value"},
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "Test Public Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "Test Private Key", "value": "New Value"},
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            {"key": "Test Private Key", "value": "New Value"},
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "Test Private Key", "value": "New Value"},
            "Datastream does not exist",
            404,
        ),
        (
            None,
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "Test Public Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            None,
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "Test Private Key", "value": "New Value"},
            "Datastream does not exist",
            404,
        ),
        (
            None,
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            {"key": "Test Private Key", "value": "New Value"},
            "Datastream does not exist",
            404,
        ),
        (
            None,
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "Test Private Key", "value": "New Value"},
            "Datastream does not exist",
            404,
        ),
    ],
)
def test_update_datastream_tag(
    get_principal, principal, datastream, tag, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            datastream_service.update_tag(
                principal=get_principal(principal),
                uid=uuid.UUID(datastream),
                data=TagPostBody(key=tag["key"], value=tag["value"]),
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        datastream_tag = datastream_service.update_tag(
            principal=get_principal(principal),
            uid=uuid.UUID(datastream),
            data=TagPostBody(key=tag["key"], value=tag["value"]),
        )

        assert datastream_tag.key == tag["key"]
        assert datastream_tag.value == tag["value"]


@pytest.mark.parametrize(
    "principal, datastream, tag, message, error_code",
    [
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "Test Public Key"},
            None,
            None,
        ),
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "Test Public Key"},
            None,
            None,
        ),
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "New Key"},
            "Tag does not exist",
            404,
        ),
        (
            "owner",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "Test Private Key"},
            None,
            None,
        ),
        (
            "owner",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            {"key": "Test Private Key"},
            None,
            None,
        ),
        (
            "owner",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "Test Private Key"},
            None,
            None,
        ),
        (
            "admin",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "Test Public Key"},
            None,
            None,
        ),
        (
            "admin",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "Test Private Key"},
            None,
            None,
        ),
        (
            "admin",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            {"key": "Test Private Key"},
            None,
            None,
        ),
        (
            "admin",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "Test Private Key"},
            None,
            None,
        ),
        (
            "editor",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "Test Public Key"},
            None,
            None,
        ),
        (
            "editor",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "Test Private Key"},
            None,
            None,
        ),
        (
            "editor",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            {"key": "Test Private Key"},
            None,
            None,
        ),
        (
            "editor",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "Test Private Key"},
            None,
            None,
        ),
        (
            "viewer",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "Test Public Key"},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "Test Private Key"},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            {"key": "Test Private Key"},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "Test Private Key"},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "Test Private Key"},
            "Datastream does not exist",
            404,
        ),
        (
            "apikey",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "Test Private Key"},
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "Test Public Key"},
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "Test Private Key"},
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            {"key": "Test Private Key"},
            "Datastream does not exist",
            404,
        ),
        (
            "anonymous",
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "Test Private Key"},
            "Datastream does not exist",
            404,
        ),
        (
            None,
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"key": "Test Public Key"},
            "You do not have permission",
            403,
        ),
        (
            None,
            "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2",
            {"key": "Test Private Key"},
            "Datastream does not exist",
            404,
        ),
        (
            None,
            "e0506cac-3e50-4d0a-814d-7ae0146705b2",
            {"key": "Test Private Key"},
            "Datastream does not exist",
            404,
        ),
        (
            None,
            "dd1f9293-ce29-4b6a-88e6-d65110d1be65",
            {"key": "Test Private Key"},
            "Datastream does not exist",
            404,
        ),
    ],
)
def test_remove_tag(get_principal, principal, datastream, tag, message, error_code):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            datastream_service.remove_tag(
                principal=get_principal(principal),
                uid=uuid.UUID(datastream),
                data=TagDeleteBody(key=tag["key"]),
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        datastream_tag_delete = datastream_service.remove_tag(
            principal=get_principal(principal),
            uid=uuid.UUID(datastream),
            data=TagDeleteBody(key=tag["key"]),
        )

        assert datastream_tag_delete.endswith("tag(s) deleted")
