import pytest
import uuid
from collections import Counter
from ninja.errors import HttpError
from django.http import HttpResponse
from domains.sta.services import ThingService
from interfaces.api.schemas import (
    ThingPostBody,
    ThingPatchBody,
    LocationPostBody,
    LocationPatchBody,
    TagPostBody,
    TagDeleteBody,
    ThingSummaryResponse,
)

thing_service = ThingService()


@pytest.mark.parametrize(
    "principal, params, thing_names, max_queries",
    [
        # Test user access
        (
            "owner",
            {},
            [
                "Public Thing",
                "Private Thing",
                "Private Thing Public Workspace",
                "Public Thing Private Workspace",
            ],
            6,
        ),
        (
            "editor",
            {},
            [
                "Public Thing",
                "Private Thing",
                "Private Thing Public Workspace",
                "Public Thing Private Workspace",
            ],
            6,
        ),
        (
            "viewer",
            {},
            [
                "Public Thing",
                "Private Thing",
                "Private Thing Public Workspace",
                "Public Thing Private Workspace",
            ],
            6,
        ),
        ("apikey", {}, ["Public Thing", "Private Thing Public Workspace"], 7),
        (
            "admin",
            {},
            [
                "Public Thing",
                "Private Thing",
                "Private Thing Public Workspace",
                "Public Thing Private Workspace",
            ],
            6,
        ),
        ("unaffiliated", {}, ["Public Thing"], 6),
        ("unaffiliated", {}, ["Public Thing"], 6),
        # Test pagination and order_by
        (
            "owner",
            {"page": 2, "page_size": 2, "order_by": "-name"},
            ["Private Thing", "Private Thing Public Workspace"],
            6,
        ),
        # Test filtering
        (
            "owner",
            {"workspace_id": ["6e0deaf2-a92b-421b-9ece-86783265596f"]},
            ["Public Thing", "Private Thing Public Workspace"],
            6,
        ),
        ("owner", {"bbox": ["-111.794,41.739,-111.793,41.740"]}, ["Public Thing"], 6),
        ("owner", {"tag": ["Test Public Key:Test Public Value"]}, ["Public Thing"], 6),
        (
            "owner",
            {"site_type": ["Public"], "samplingFeatureType": ["Public"]},
            ["Public Thing"],
            6,
        ),
        (
            "owner",
            {"is_private": False},
            ["Public Thing"],
            6,
        ),
    ],
)
def test_list_thing(
    django_assert_max_num_queries,
    get_principal,
    principal,
    params,
    thing_names,
    max_queries,
):
    with django_assert_max_num_queries(max_queries):
        http_response = HttpResponse()
        result = thing_service.list(
            principal=get_principal(principal),
            response=http_response,
            page=params.pop("page", 1),
            page_size=params.pop("page_size", 100),
            order_by=[params.pop("order_by")] if "order_by" in params else [],
            filtering=params,
        )
        assert Counter(str(thing.name) for thing in result) == Counter(thing_names)
        assert (ThingSummaryResponse.from_orm(thing) for thing in result)


@pytest.mark.parametrize(
    "principal, thing, message, error_code",
    [
        # Test public access
        ("owner", "3b7818af-eff7-4149-8517-e5cad9dc22e1", "Public Thing", None),
        ("editor", "3b7818af-eff7-4149-8517-e5cad9dc22e1", "Public Thing", None),
        ("viewer", "3b7818af-eff7-4149-8517-e5cad9dc22e1", "Public Thing", None),
        ("admin", "3b7818af-eff7-4149-8517-e5cad9dc22e1", "Public Thing", None),
        ("apikey", "3b7818af-eff7-4149-8517-e5cad9dc22e1", "Public Thing", None),
        ("unaffiliated", "3b7818af-eff7-4149-8517-e5cad9dc22e1", "Public Thing", None),
        ("anonymous", "3b7818af-eff7-4149-8517-e5cad9dc22e1", "Public Thing", None),
        # Test private access
        ("owner", "76dadda5-224b-4e1f-8570-e385bd482b2d", "Private Thing", None),
        (
            "owner",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            "Private Thing Public Workspace",
            None,
        ),
        (
            "owner",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            "Public Thing Private Workspace",
            None,
        ),
        ("admin", "76dadda5-224b-4e1f-8570-e385bd482b2d", "Private Thing", None),
        (
            "admin",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            "Private Thing Public Workspace",
            None,
        ),
        (
            "admin",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            "Public Thing Private Workspace",
            None,
        ),
        # Test unauthorized access
        (
            "apikey",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            "Thing does not exist",
            404,
        ),
        (
            "unaffiliated",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            "Thing does not exist",
            404,
        ),
        (
            "unaffiliated",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            "Thing does not exist",
            404,
        ),
        (
            "unaffiliated",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            "Thing does not exist",
            404,
        ),
        (
            "anonymous",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            "Thing does not exist",
            404,
        ),
        (
            "anonymous",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            "Thing does not exist",
            404,
        ),
        (
            "anonymous",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            "Thing does not exist",
            404,
        ),
        # Test missing resource
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            "Thing does not exist",
            404,
        ),
    ],
)
def test_get_thing(get_principal, principal, thing, message, error_code):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            thing_service.get(principal=get_principal(principal), uid=uuid.UUID(thing))
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        thing_get = thing_service.get(
            principal=get_principal(principal), uid=uuid.UUID(thing)
        )
        assert thing_get.name == message
        assert ThingSummaryResponse.from_orm(thing_get)


@pytest.mark.parametrize(
    "principal, thing_fields, message, error_code",
    [
        # Test create valid Thing
        ("owner", {}, None, None),
        ("editor", {}, None, None),
        ("admin", {}, None, None),
        # Test create invalid Thing
        (
            "owner",
            {"workspace_id": "00000000-0000-0000-0000-000000000000"},
            "Workspace does not exist",
            404,
        ),
        # Test unauthorized attempts
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
        ("anonymous", {}, "You do not have permission", 403),
        (
            "anonymous",
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
    ],
)
def test_create_thing(get_principal, principal, thing_fields, message, error_code):
    thing_data = ThingPostBody(
        name=thing_fields.get("name", "New"),
        description=thing_fields.get("description", "New"),
        sampling_feature_type=thing_fields.get("sampling_feature_type", "Site"),
        sampling_feature_code=thing_fields.get("sampling_feature_code", "NEW"),
        site_type=thing_fields.get("site_type", "Site"),
        location=LocationPostBody(
            latitude=thing_fields.get("location", {}).get("latitude", 0),
            longitude=thing_fields.get("location", {}).get("longitude", 0),
        ),
        is_private=thing_fields.get("is_private", False),
        workspace_id=uuid.UUID(
            thing_fields.get("workspace_id", "6e0deaf2-a92b-421b-9ece-86783265596f")
        ),
    )
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            thing_service.create(principal=get_principal(principal), data=thing_data)
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        thing_create = thing_service.create(
            principal=get_principal(principal), data=thing_data
        )
        assert thing_create.name == thing_data.name
        assert thing_create.description == thing_data.description
        assert thing_create.sampling_feature_type == thing_data.sampling_feature_type
        assert thing_create.sampling_feature_code == thing_data.sampling_feature_code
        assert thing_create.site_type == thing_data.site_type
        assert thing_create.location.latitude == thing_data.location.latitude
        assert thing_create.location.longitude == thing_data.location.longitude
        assert thing_create.is_private == thing_data.is_private
        assert thing_create.workspace_id == thing_data.workspace_id
        assert ThingSummaryResponse.from_orm(thing_create)


@pytest.mark.parametrize(
    "principal, thing, thing_fields, message, error_code",
    [
        # Test edit Thing
        ("owner", "3b7818af-eff7-4149-8517-e5cad9dc22e1", {}, None, None),
        ("editor", "3b7818af-eff7-4149-8517-e5cad9dc22e1", {}, None, None),
        ("admin", "3b7818af-eff7-4149-8517-e5cad9dc22e1", {}, None, None),
        # Test unauthorized attempts
        (
            "viewer",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {},
            "Thing does not exist",
            404,
        ),
        (
            "anonymous",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {},
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {},
            "Thing does not exist",
            404,
        ),
        (
            "unaffiliated",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {},
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {},
            "Thing does not exist",
            404,
        ),
    ],
)
def test_edit_thing(get_principal, principal, thing, thing_fields, message, error_code):
    thing_data = ThingPatchBody(
        name=thing_fields.get("name", "New"),
        description=thing_fields.get("description", "New"),
        sampling_feature_type=thing_fields.get("sampling_feature_type", "Site"),
        sampling_feature_code=thing_fields.get("sampling_feature_code", "NEW"),
        site_type=thing_fields.get("site_type", "Site"),
        location=LocationPatchBody(
            latitude=thing_fields.get("location", {}).get("latitude", 0),
            longitude=thing_fields.get("location", {}).get("longitude", 0),
        ),
        is_private=thing_fields.get("is_private", False),
    )
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            thing_service.update(
                principal=get_principal(principal),
                uid=uuid.UUID(thing),
                data=thing_data,
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        thing_update = thing_service.update(
            principal=get_principal(principal), uid=uuid.UUID(thing), data=thing_data
        )
        assert thing_update.name == thing_data.name
        assert thing_update.description == thing_data.description
        assert thing_update.sampling_feature_type == thing_data.sampling_feature_type
        assert thing_update.sampling_feature_code == thing_data.sampling_feature_code
        assert thing_update.site_type == thing_data.site_type
        assert thing_update.location.latitude == thing_data.location.latitude
        assert thing_update.location.longitude == thing_data.location.longitude
        assert thing_update.is_private == thing_data.is_private
        assert ThingSummaryResponse.from_orm(thing_update)


@pytest.mark.parametrize(
    "principal, thing, message, error_code, max_queries",
    [
        # Test edit Thing
        ("owner", "3b7818af-eff7-4149-8517-e5cad9dc22e1", None, None, 20),
        ("editor", "3b7818af-eff7-4149-8517-e5cad9dc22e1", None, None, 20),
        ("admin", "3b7818af-eff7-4149-8517-e5cad9dc22e1", None, None, 20),
        # Test unauthorized attempts
        (
            "viewer",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "You do not have permission",
            403,
            8,
        ),
        (
            "viewer",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            "You do not have permission",
            403,
            8,
        ),
        (
            "apikey",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "You do not have permission",
            403,
            8,
        ),
        (
            "apikey",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            "Thing does not exist",
            404,
            8,
        ),
        (
            "anonymous",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "You do not have permission",
            403,
            8,
        ),
        (
            "anonymous",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            "Thing does not exist",
            404,
            8,
        ),
        (
            "unaffiliated",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            "You do not have permission",
            403,
            8,
        ),
        (
            "unaffiliated",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            "Thing does not exist",
            404,
            8,
        ),
    ],
)
def test_delete_thing(
    django_assert_max_num_queries,
    get_principal,
    principal,
    thing,
    message,
    error_code,
    max_queries,
):
    with django_assert_max_num_queries(max_queries):
        if error_code:
            with pytest.raises(HttpError) as exc_info:
                thing_service.delete(
                    principal=get_principal(principal), uid=uuid.UUID(thing)
                )
            assert exc_info.value.status_code == error_code
            assert exc_info.value.message.startswith(message)
        else:
            thing_delete = thing_service.delete(
                principal=get_principal(principal), uid=uuid.UUID(thing)
            )
            assert thing_delete == "Thing deleted"


@pytest.mark.parametrize(
    "principal, thing, message, error_code",
    [
        ("owner", "3b7818af-eff7-4149-8517-e5cad9dc22e1", None, None),
        ("owner", "76dadda5-224b-4e1f-8570-e385bd482b2d", None, None),
        ("owner", "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7", None, None),
        ("owner", "819260c8-2543-4046-b8c4-7431243ed7c5", None, None),
        ("admin", "3b7818af-eff7-4149-8517-e5cad9dc22e1", None, None),
        ("admin", "76dadda5-224b-4e1f-8570-e385bd482b2d", None, None),
        ("admin", "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7", None, None),
        ("admin", "819260c8-2543-4046-b8c4-7431243ed7c5", None, None),
        ("editor", "3b7818af-eff7-4149-8517-e5cad9dc22e1", None, None),
        ("editor", "76dadda5-224b-4e1f-8570-e385bd482b2d", None, None),
        ("editor", "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7", None, None),
        ("editor", "819260c8-2543-4046-b8c4-7431243ed7c5", None, None),
        ("viewer", "3b7818af-eff7-4149-8517-e5cad9dc22e1", None, None),
        ("viewer", "76dadda5-224b-4e1f-8570-e385bd482b2d", None, None),
        ("viewer", "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7", None, None),
        ("viewer", "819260c8-2543-4046-b8c4-7431243ed7c5", None, None),
        ("apikey", "3b7818af-eff7-4149-8517-e5cad9dc22e1", None, None),
        (
            "apikey",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            "Thing does not exist",
            404,
        ),
        (
            "apikey",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            None,
            None,
        ),
        (
            "apikey",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            "Thing does not exist",
            404,
        ),
        ("anonymous", "3b7818af-eff7-4149-8517-e5cad9dc22e1", None, None),
        (
            "unaffiliated",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            "Thing does not exist",
            404,
        ),
        (
            "unaffiliated",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            "Thing does not exist",
            404,
        ),
        (
            "unaffiliated",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            "Thing does not exist",
            404,
        ),
        ("anonymous", "3b7818af-eff7-4149-8517-e5cad9dc22e1", None, None),
        (
            "anonymous",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            "Thing does not exist",
            404,
        ),
        (
            "anonymous",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            "Thing does not exist",
            404,
        ),
        (
            "anonymous",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            "Thing does not exist",
            404,
        ),
    ],
)
def test_get_thing_tags(get_principal, principal, thing, message, error_code):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            thing_service.get_tags(
                principal=get_principal(principal), uid=uuid.UUID(thing)
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        thing_tags = thing_service.get_tags(
            principal=get_principal(principal), uid=uuid.UUID(thing)
        )
        assert set([tag.key for tag in thing_tags]).issubset(
            ["Test Public Key", "Test Private Key"]
        )
        assert set([tag.value for tag in thing_tags]).issubset(
            ["Test Public Value", "Test Private Value"]
        )


@pytest.mark.parametrize(
    "principal, workspace, thing, length, max_queries",
    [
        ("owner", None, None, 2, 2),
        ("owner", "b27c51a0-7374-462d-8a53-d97d47176c10", None, 1, 2),
        ("owner", None, "76dadda5-224b-4e1f-8570-e385bd482b2d", 1, 2),
        (
            "owner",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            0,
            2,
        ),
        ("admin", None, None, 2, 2),
        ("admin", "b27c51a0-7374-462d-8a53-d97d47176c10", None, 1, 2),
        ("admin", None, "76dadda5-224b-4e1f-8570-e385bd482b2d", 1, 2),
        (
            "admin",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            0,
            2,
        ),
        ("editor", None, None, 2, 2),
        ("editor", "b27c51a0-7374-462d-8a53-d97d47176c10", None, 1, 2),
        ("editor", None, "76dadda5-224b-4e1f-8570-e385bd482b2d", 1, 2),
        (
            "editor",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            0,
            2,
        ),
        ("viewer", None, None, 2, 2),
        ("viewer", "b27c51a0-7374-462d-8a53-d97d47176c10", None, 1, 2),
        ("viewer", None, "76dadda5-224b-4e1f-8570-e385bd482b2d", 1, 2),
        (
            "viewer",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            0,
            2,
        ),
        ("apikey", None, None, 2, 3),
        ("apikey", "b27c51a0-7374-462d-8a53-d97d47176c10", None, 0, 3),
        ("apikey", None, "76dadda5-224b-4e1f-8570-e385bd482b2d", 0, 3),
        (
            "apikey",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            0,
            3,
        ),
        ("anonymous", None, None, 1, 2),
        ("anonymous", "b27c51a0-7374-462d-8a53-d97d47176c10", None, 0, 2),
        ("anonymous", None, "76dadda5-224b-4e1f-8570-e385bd482b2d", 0, 2),
        (
            "anonymous",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            0,
            2,
        ),
        (None, None, None, 1, 2),
        (None, "b27c51a0-7374-462d-8a53-d97d47176c10", None, 0, 2),
        (None, None, "76dadda5-224b-4e1f-8570-e385bd482b2d", 0, 2),
        (
            None,
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            0,
            2,
        ),
    ],
)
def test_get_thing_tag_keys(
    django_assert_num_queries,
    get_principal,
    principal,
    workspace,
    thing,
    length,
    max_queries,
):
    with django_assert_num_queries(max_queries):
        tag_key_list = thing_service.get_tag_keys(
            principal=get_principal(principal),
            workspace_id=uuid.UUID(workspace) if workspace else None,
            thing_id=uuid.UUID(thing) if thing else None,
        )
        assert len(tag_key_list) == length
        assert (isinstance(str, tag_key) for tag_key in tag_key_list)


@pytest.mark.parametrize(
    "principal, thing, tag, message, error_code",
    [
        (
            "owner",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "owner",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "New Key", "value": "Test Value"},
            None,
            None,
        ),
        (
            "owner",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "Test Public Key", "value": "Test Public Value"},
            "Tag already exists",
            400,
        ),
        (
            "owner",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "owner",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "owner",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "admin",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "admin",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "admin",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "admin",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "editor",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "editor",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "editor",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "editor",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "New Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "viewer",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "New Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "New Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "New Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "New Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "New Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "New Key", "value": "New Value"},
            "Thing does not exist",
            404,
        ),
        (
            "apikey",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "New Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "New Key", "value": "New Value"},
            "Thing does not exist",
            404,
        ),
        (
            "anonymous",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "New Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "New Key", "value": "New Value"},
            "Thing does not exist",
            404,
        ),
        (
            "anonymous",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "New Key", "value": "New Value"},
            "Thing does not exist",
            404,
        ),
        (
            "anonymous",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "New Key", "value": "New Value"},
            "Thing does not exist",
            404,
        ),
        (
            None,
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "New Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            None,
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "New Key", "value": "New Value"},
            "Thing does not exist",
            404,
        ),
        (
            None,
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "New Key", "value": "New Value"},
            "Thing does not exist",
            404,
        ),
        (
            None,
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "New Key", "value": "New Value"},
            "Thing does not exist",
            404,
        ),
    ],
)
def test_add_thing_tag(get_principal, principal, thing, tag, message, error_code):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            thing_service.add_tag(
                principal=get_principal(principal),
                uid=uuid.UUID(thing),
                data=TagPostBody(key=tag["key"], value=tag["value"]),
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        thing_tag = thing_service.add_tag(
            principal=get_principal(principal),
            uid=uuid.UUID(thing),
            data=TagPostBody(key=tag["key"], value=tag["value"]),
        )

        assert thing_tag.key == tag["key"]
        assert thing_tag.value == tag["value"]


@pytest.mark.parametrize(
    "principal, thing, tag, message, error_code",
    [
        (
            "owner",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "Test Public Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "owner",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "Test Public Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "owner",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "New Key", "value": "New Value"},
            "Tag does not exist",
            404,
        ),
        (
            "owner",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "Test Private Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "owner",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "Test Private Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "owner",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "Test Private Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "admin",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "Test Public Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "admin",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "Test Private Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "admin",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "Test Private Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "admin",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "Test Private Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "editor",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "Test Public Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "editor",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "Test Private Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "editor",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "Test Private Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "editor",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "Test Private Key", "value": "New Value"},
            None,
            None,
        ),
        (
            "viewer",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "Test Public Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "Test Private Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "Test Private Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "Test Private Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "Test Public Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "Test Private Key", "value": "New Value"},
            "Thing does not exist",
            404,
        ),
        (
            "apikey",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "Test Private Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "Test Private Key", "value": "New Value"},
            "Thing does not exist",
            404,
        ),
        (
            "anonymous",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "Test Public Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "Test Private Key", "value": "New Value"},
            "Thing does not exist",
            404,
        ),
        (
            "anonymous",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "Test Private Key", "value": "New Value"},
            "Thing does not exist",
            404,
        ),
        (
            "anonymous",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "Test Private Key", "value": "New Value"},
            "Thing does not exist",
            404,
        ),
        (
            None,
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "Test Public Key", "value": "New Value"},
            "You do not have permission",
            403,
        ),
        (
            None,
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "Test Private Key", "value": "New Value"},
            "Thing does not exist",
            404,
        ),
        (
            None,
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "Test Private Key", "value": "New Value"},
            "Thing does not exist",
            404,
        ),
        (
            None,
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "Test Private Key", "value": "New Value"},
            "Thing does not exist",
            404,
        ),
    ],
)
def test_update_thing_tag(get_principal, principal, thing, tag, message, error_code):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            thing_service.update_tag(
                principal=get_principal(principal),
                uid=uuid.UUID(thing),
                data=TagPostBody(key=tag["key"], value=tag["value"]),
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        thing_tag = thing_service.update_tag(
            principal=get_principal(principal),
            uid=uuid.UUID(thing),
            data=TagPostBody(key=tag["key"], value=tag["value"]),
        )

        assert thing_tag.key == tag["key"]
        assert thing_tag.value == tag["value"]


@pytest.mark.parametrize(
    "principal, thing, tag, message, error_code",
    [
        (
            "owner",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "Test Public Key"},
            None,
            None,
        ),
        (
            "owner",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "Test Public Key"},
            None,
            None,
        ),
        (
            "owner",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "New Key"},
            "Tag does not exist",
            404,
        ),
        (
            "owner",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "Test Private Key"},
            None,
            None,
        ),
        (
            "owner",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "Test Private Key"},
            None,
            None,
        ),
        (
            "owner",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "Test Private Key"},
            None,
            None,
        ),
        (
            "admin",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "Test Public Key"},
            None,
            None,
        ),
        (
            "admin",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "Test Private Key"},
            None,
            None,
        ),
        (
            "admin",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "Test Private Key"},
            None,
            None,
        ),
        (
            "admin",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "Test Private Key"},
            None,
            None,
        ),
        (
            "editor",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "Test Public Key"},
            None,
            None,
        ),
        (
            "editor",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "Test Private Key"},
            None,
            None,
        ),
        (
            "editor",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "Test Private Key"},
            None,
            None,
        ),
        (
            "editor",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "Test Private Key"},
            None,
            None,
        ),
        (
            "viewer",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "Test Public Key"},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "Test Private Key"},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "Test Private Key"},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "Test Private Key"},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "Test Public Key"},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "Test Private Key"},
            "Thing does not exist",
            404,
        ),
        (
            "apikey",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "Test Private Key"},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "Test Private Key"},
            "Thing does not exist",
            404,
        ),
        (
            "anonymous",
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "Test Public Key"},
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "Test Private Key"},
            "Thing does not exist",
            404,
        ),
        (
            "anonymous",
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "Test Private Key"},
            "Thing does not exist",
            404,
        ),
        (
            "anonymous",
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "Test Private Key"},
            "Thing does not exist",
            404,
        ),
        (
            None,
            "3b7818af-eff7-4149-8517-e5cad9dc22e1",
            {"key": "Test Public Key"},
            "You do not have permission",
            403,
        ),
        (
            None,
            "76dadda5-224b-4e1f-8570-e385bd482b2d",
            {"key": "Test Private Key"},
            "Thing does not exist",
            404,
        ),
        (
            None,
            "92a3a099-f2d3-40ec-9b0e-d25ae8bf59b7",
            {"key": "Test Private Key"},
            "Thing does not exist",
            404,
        ),
        (
            None,
            "819260c8-2543-4046-b8c4-7431243ed7c5",
            {"key": "Test Private Key"},
            "Thing does not exist",
            404,
        ),
    ],
)
def test_remove_thing_tag(get_principal, principal, thing, tag, message, error_code):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            thing_service.remove_tag(
                principal=get_principal(principal),
                uid=uuid.UUID(thing),
                data=TagDeleteBody(key=tag["key"]),
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        thing_tag_delete = thing_service.remove_tag(
            principal=get_principal(principal),
            uid=uuid.UUID(thing),
            data=TagDeleteBody(key=tag["key"]),
        )

        assert thing_tag_delete.endswith("tag(s) deleted")
