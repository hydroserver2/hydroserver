import pytest
import uuid
from collections import Counter
from ninja.errors import HttpError
from django.http import HttpResponse
from domains.sta.services import ObservedPropertyService
from interfaces.api.schemas import (
    ObservedPropertyPostBody,
    ObservedPropertyPatchBody,
    ObservedPropertySummaryResponse,
)

observed_property_service = ObservedPropertyService()


@pytest.mark.parametrize(
    "principal, params, observed_property_names, max_queries",
    [
        # Test user access
        (
            "owner",
            {},
            [
                "System Observed Property",
                "System Assigned Observed Property",
                "Public Observed Property",
                "Public Assigned Observed Property",
                "Private Observed Property",
                "Private Assigned Observed Property",
            ],
            3,
        ),
        (
            "editor",
            {},
            [
                "System Observed Property",
                "System Assigned Observed Property",
                "Public Observed Property",
                "Public Assigned Observed Property",
                "Private Observed Property",
                "Private Assigned Observed Property",
            ],
            3,
        ),
        (
            "viewer",
            {},
            [
                "System Observed Property",
                "System Assigned Observed Property",
                "Public Observed Property",
                "Public Assigned Observed Property",
                "Private Observed Property",
                "Private Assigned Observed Property",
            ],
            3,
        ),
        (
            "admin",
            {},
            [
                "System Observed Property",
                "System Assigned Observed Property",
                "Public Observed Property",
                "Public Assigned Observed Property",
                "Private Observed Property",
                "Private Assigned Observed Property",
            ],
            3,
        ),
        (
            "apikey",
            {},
            [
                "System Observed Property",
                "System Assigned Observed Property",
                "Public Observed Property",
                "Public Assigned Observed Property",
            ],
            4,
        ),
        (
            "unaffiliated",
            {},
            [
                "System Observed Property",
                "System Assigned Observed Property",
                "Public Observed Property",
                "Public Assigned Observed Property",
            ],
            3,
        ),
        (
            "anonymous",
            {},
            [
                "System Observed Property",
                "System Assigned Observed Property",
                "Public Observed Property",
                "Public Assigned Observed Property",
            ],
            3,
        ),
        # Test pagination and order_by
        (
            "owner",
            {"page": 2, "page_size": 2, "order_by": "-name"},
            [
                "Public Observed Property",
                "Public Assigned Observed Property",
            ],
            3,
        ),
        # Test filtering
        (
            "owner",
            {"workspace_id": "6e0deaf2-a92b-421b-9ece-86783265596f"},
            ["Public Observed Property", "Public Assigned Observed Property"],
            3,
        ),
        (
            "owner",
            {"datastreams__thing_id": "3b7818af-eff7-4149-8517-e5cad9dc22e1"},
            ["System Assigned Observed Property", "Public Assigned Observed Property"],
            3,
        ),
        (
            "owner",
            {"datastreams__id": "27c70b41-e845-40ea-8cc7-d1b40f89816b"},
            ["Public Assigned Observed Property"],
            3,
        ),
    ],
)
def test_list_observed_property(
    django_assert_num_queries,
    get_principal,
    principal,
    params,
    observed_property_names,
    max_queries,
):
    with django_assert_num_queries(max_queries):
        http_response = HttpResponse()
        result = observed_property_service.list(
            principal=get_principal(principal),
            response=http_response,
            page=params.pop("page", 1),
            page_size=params.pop("page_size", 100),
            order_by=[params.pop("order_by")] if "order_by" in params else [],
            filtering=params,
        )
        assert Counter(
            str(observed_property.name) for observed_property in result
        ) == Counter(observed_property_names)
        assert (
            ObservedPropertySummaryResponse.from_orm(observed_property)
            for observed_property in result
        )


@pytest.mark.parametrize(
    "principal, observed_property, message, error_code",
    [
        # Test public access
        (
            "owner",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "System Observed Property",
            None,
        ),
        (
            "owner",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "Public Observed Property",
            None,
        ),
        (
            "admin",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "System Observed Property",
            None,
        ),
        (
            "admin",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "Public Observed Property",
            None,
        ),
        (
            "editor",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "System Observed Property",
            None,
        ),
        (
            "editor",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "Public Observed Property",
            None,
        ),
        (
            "viewer",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "System Observed Property",
            None,
        ),
        (
            "viewer",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "Public Observed Property",
            None,
        ),
        (
            "apikey",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "System Observed Property",
            None,
        ),
        (
            "apikey",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "Public Observed Property",
            None,
        ),
        (
            "unaffiliated",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "System Observed Property",
            None,
        ),
        (
            "unaffiliated",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "Public Observed Property",
            None,
        ),
        (
            "anonymous",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "System Observed Property",
            None,
        ),
        (
            "anonymous",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "Public Observed Property",
            None,
        ),
        # Test private access
        (
            "owner",
            "5dbfd184-ae79-4c05-a9ea-3f5e775ecbc1",
            "Private Observed Property",
            None,
        ),
        (
            "admin",
            "5dbfd184-ae79-4c05-a9ea-3f5e775ecbc1",
            "Private Observed Property",
            None,
        ),
        # Test unauthorized access
        (
            "apikey",
            "5dbfd184-ae79-4c05-a9ea-3f5e775ecbc1",
            "Observed property does not exist",
            404,
        ),
        (
            "unaffiliated",
            "5dbfd184-ae79-4c05-a9ea-3f5e775ecbc1",
            "Observed property does not exist",
            404,
        ),
        (
            "anonymous",
            "5dbfd184-ae79-4c05-a9ea-3f5e775ecbc1",
            "Observed property does not exist",
            404,
        ),
        # Test missing resource
        (
            "anonymous",
            "00000000-0000-0000-0000-000000000000",
            "Observed property does not exist",
            404,
        ),
    ],
)
def test_get_observed_property(
    get_principal, principal, observed_property, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            observed_property_service.get(
                principal=get_principal(principal), uid=uuid.UUID(observed_property)
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        observed_property_get = observed_property_service.get(
            principal=get_principal(principal), uid=uuid.UUID(observed_property)
        )
        assert observed_property_get.name == message
        assert ObservedPropertySummaryResponse.from_orm(observed_property_get)


@pytest.mark.parametrize(
    "principal, observed_property_fields, message, error_code",
    [
        # Test create valid ObservedProperty
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
        # Test create invalid ObservedProperty
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
def test_create_observed_property(
    get_principal, principal, observed_property_fields, message, error_code
):
    observed_property_data = ObservedPropertyPostBody(
        name=observed_property_fields.get("name", "New"),
        description=observed_property_fields.get("description", "New"),
        code=observed_property_fields.get("code", "New"),
        observed_property_type=observed_property_fields.get(
            "observed_property_type", "New"
        ),
        definition=observed_property_fields.get("definition", "New"),
        workspace_id=(
            (
                uuid.UUID(wid)
                if (wid := observed_property_fields["workspace_id"]) is not None
                else None
            )
            if "workspace_id" in observed_property_fields
            else uuid.UUID("6e0deaf2-a92b-421b-9ece-86783265596f")
        ),
    )
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            observed_property_service.create(
                principal=get_principal(principal), data=observed_property_data
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        observed_property_create = observed_property_service.create(
            principal=get_principal(principal), data=observed_property_data
        )
        assert observed_property_create.name == observed_property_data.name
        assert observed_property_create.definition == observed_property_data.definition
        assert ObservedPropertySummaryResponse.from_orm(observed_property_create)


@pytest.mark.parametrize(
    "principal, observed_property, observed_property_fields, message, error_code",
    [
        # Test edit ObservedProperty
        ("owner", "cac1262e-68ee-43a0-9222-f214f2161091", {}, None, None),
        ("editor", "cac1262e-68ee-43a0-9222-f214f2161091", {}, None, None),
        ("admin", "cac1262e-68ee-43a0-9222-f214f2161091", {}, None, None),
        # Test unauthorized attempts
        (
            "viewer",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            {},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            {},
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "5dbfd184-ae79-4c05-a9ea-3f5e775ecbc1",
            {},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            {},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            {},
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "5dbfd184-ae79-4c05-a9ea-3f5e775ecbc1",
            {},
            "Observed property does not exist",
            404,
        ),
        (
            "unaffiliated",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            {},
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            {},
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "5dbfd184-ae79-4c05-a9ea-3f5e775ecbc1",
            {},
            "Observed property does not exist",
            404,
        ),
        (
            "anonymous",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            {},
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            {},
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "5dbfd184-ae79-4c05-a9ea-3f5e775ecbc1",
            {},
            "Observed property does not exist",
            404,
        ),
    ],
)
def test_edit_observed_property(
    get_principal,
    principal,
    observed_property,
    observed_property_fields,
    message,
    error_code,
):
    observed_property_data = ObservedPropertyPatchBody(
        name=observed_property_fields.get("name", "New"),
        description=observed_property_fields.get("description", "New"),
        code=observed_property_fields.get("code", "New"),
        observed_property_type=observed_property_fields.get(
            "observed_property_type", "New"
        ),
        definition=observed_property_fields.get("definition", "New"),
    )
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            observed_property_service.update(
                principal=get_principal(principal),
                uid=uuid.UUID(observed_property),
                data=observed_property_data,
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        observed_property_update = observed_property_service.update(
            principal=get_principal(principal),
            uid=uuid.UUID(observed_property),
            data=observed_property_data,
        )
        assert observed_property_update.name == observed_property_data.name
        assert observed_property_update.definition == observed_property_data.definition
        assert ObservedPropertySummaryResponse.from_orm(observed_property_update)


@pytest.mark.parametrize(
    "principal, observed_property, message, error_code",
    [
        # Test delete ObservedProperty
        ("owner", "cac1262e-68ee-43a0-9222-f214f2161091", None, None),
        ("editor", "cac1262e-68ee-43a0-9222-f214f2161091", None, None),
        ("admin", "cac1262e-68ee-43a0-9222-f214f2161091", None, None),
        # Test unauthorized attempts
        (
            "viewer",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "You do not have permission",
            403,
        ),
        (
            "viewer",
            "5dbfd184-ae79-4c05-a9ea-3f5e775ecbc1",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "5dbfd184-ae79-4c05-a9ea-3f5e775ecbc1",
            "Observed property does not exist",
            404,
        ),
        (
            "unaffiliated",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "5dbfd184-ae79-4c05-a9ea-3f5e775ecbc1",
            "Observed property does not exist",
            404,
        ),
        (
            "anonymous",
            "cac1262e-68ee-43a0-9222-f214f2161091",
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "49a245bd-4517-4dea-b3ba-25c919bf2cf5",
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "5dbfd184-ae79-4c05-a9ea-3f5e775ecbc1",
            "Observed property does not exist",
            404,
        ),
    ],
)
def test_delete_observed_property(
    get_principal, principal, observed_property, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            observed_property_service.delete(
                principal=get_principal(principal), uid=uuid.UUID(observed_property)
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        observed_property_delete = observed_property_service.delete(
            principal=get_principal(principal), uid=uuid.UUID(observed_property)
        )
        assert observed_property_delete == "Observed property deleted"
