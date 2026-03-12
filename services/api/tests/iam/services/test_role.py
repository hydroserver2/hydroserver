import pytest
import uuid
from collections import Counter
from ninja.errors import HttpError
from django.http import HttpResponse
from domains.iam.services.role import RoleService
from interfaces.api.schemas import RoleSummaryResponse

role_service = RoleService()


@pytest.mark.parametrize(
    "principal, workspace, params, role_names, max_queries",
    [
        # Test user access
        (
            "owner",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            {},
            ["Editor", "Viewer", "Data Loader", "Private"],
            7,
        ),
        (
            "editor",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            {},
            ["Editor", "Viewer", "Data Loader", "Private"],
            7,
        ),
        (
            "viewer",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            {},
            ["Editor", "Viewer", "Data Loader", "Private"],
            7,
        ),
        (
            "admin",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            {},
            ["Editor", "Viewer", "Data Loader", "Private"],
            7,
        ),
        (
            "apikey",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            {},
            ["Editor", "Viewer", "Data Loader"],
            7,
        ),
        (
            "unaffiliated",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            {},
            ["Editor", "Viewer", "Data Loader"],
            7,
        ),
        (
            "anonymous",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            {},
            ["Editor", "Viewer", "Data Loader"],
            7,
        ),
        # Test pagination and order_by
        (
            "owner",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            {"page": 2, "page_size": 1, "order_by": "-name"},
            ["Private"],
            7,
        ),
        # Test filtering
        (
            "owner",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            {"is_apikey_role": True, "is_user_role": False},
            ["Data Loader"],
            7,
        ),
    ],
)
def test_list_role(
    django_assert_max_num_queries,
    get_principal,
    principal,
    workspace,
    params,
    role_names,
    max_queries,
):
    with django_assert_max_num_queries(max_queries):
        http_response = HttpResponse()
        result = role_service.list(
            principal=get_principal(principal),
            response=http_response,
            page=params.pop("page", 1),
            page_size=params.pop("page_size", 100),
            order_by=[params.pop("order_by")] if "order_by" in params else [],
            filtering=params,
        )
        assert Counter(str(role.name) for role in result) == Counter(role_names)
        assert (RoleSummaryResponse.from_orm(role) for role in result)


@pytest.mark.parametrize(
    "principal, role, message, error_code",
    [
        (
            "owner",
            "60b9d8b1-28d1-4d0d-9bee-4e47219d0118",
            "Private",
            None,
        ),
        (
            "admin",
            "60b9d8b1-28d1-4d0d-9bee-4e47219d0118",
            "Private",
            None,
        ),
        (
            "apikey",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "Editor",
            None,
        ),
        (
            "anonymous",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "Editor",
            None,
        ),
        (
            None,
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "Editor",
            None,
        ),
        (
            "owner",
            "00000000-0000-0000-0000-000000000000",
            "Role does not exist",
            404,
        ),
        (
            "apikey",
            "60b9d8b1-28d1-4d0d-9bee-4e47219d0118",
            "Role does not exist",
            404,
        ),
        (
            "anonymous",
            "60b9d8b1-28d1-4d0d-9bee-4e47219d0118",
            "Role does not exist",
            404,
        ),
        (
            None,
            "60b9d8b1-28d1-4d0d-9bee-4e47219d0118",
            "Role does not exist",
            404,
        ),
    ],
)
def test_get_role(get_principal, principal, role, message, error_code):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            role_service.get(
                principal=get_principal(principal),
                uid=uuid.UUID(role),
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        role_get = role_service.get(
            principal=get_principal(principal),
            uid=uuid.UUID(role),
        )
        assert role_get.name == message
        assert RoleSummaryResponse.from_orm(role_get)
