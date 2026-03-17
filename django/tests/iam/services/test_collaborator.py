import pytest
import uuid
from collections import Counter
from ninja.errors import HttpError
from django.http import HttpResponse
from domains.iam.services.collaborator import CollaboratorService
from interfaces.api.schemas import (
    CollaboratorPostBody,
    CollaboratorDeleteBody,
    CollaboratorDetailResponse,
)

collaborator_service = CollaboratorService()


@pytest.mark.parametrize(
    "principal, workspace, params, collaborator_ids, max_queries",
    [
        # Test user access
        (
            "owner",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            {},
            ["1000000012", "1000000013"],
            7,
        ),
        (
            "editor",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            {},
            ["1000000012", "1000000013"],
            7,
        ),
        (
            "viewer",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            {},
            ["1000000012", "1000000013"],
            7,
        ),
        (
            "admin",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            {},
            ["1000000012", "1000000013"],
            7,
        ),
        (
            "apikey",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            {},
            ["1000000010", "1000000011"],
            7,
        ),
        (
            "unaffiliated",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            {},
            ["1000000010", "1000000011"],
            7,
        ),
        (
            "anonymous",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            {},
            ["1000000010", "1000000011"],
            7,
        ),
        # Test pagination and order_by
        (
            "owner",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            {"page": 2, "page_size": 1},
            ["1000000013"],
            7,
        ),
        # Test filtering
        (
            "owner",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            {"role_id": "2f05f775-5d8a-4778-9942-3d13a64ec7a3"},
            ["1000000012"],
            7,
        ),
    ],
)
def test_list_collaborator(
    django_assert_max_num_queries,
    get_principal,
    principal,
    workspace,
    params,
    collaborator_ids,
    max_queries,
):
    with django_assert_max_num_queries(max_queries):
        http_response = HttpResponse()
        result = collaborator_service.list(
            principal=get_principal(principal),
            workspace_id=uuid.UUID(workspace),
            response=http_response,
            page=params.pop("page", 1),
            page_size=params.pop("page_size", 100),
            filtering=params,
        )
        assert Counter(str(collaborator.id) for collaborator in result) == Counter(
            collaborator_ids
        )
        assert (
            CollaboratorDetailResponse.from_orm(collaborator) for collaborator in result
        )


@pytest.mark.parametrize(
    "principal, collaborator, workspace, role, message, error_code",
    [
        (
            "owner",
            "unaffiliated",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            None,
            None,
        ),
        (
            "admin",
            "unaffiliated",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            None,
            None,
        ),
        (
            "owner",
            "unaffiliated",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "60b9d8b1-28d1-4d0d-9bee-4e47219d0118",
            None,
            None,
        ),
        (
            "owner",
            "limited",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            None,
            None,
        ),
        (
            "editor",
            "unaffiliated",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            None,
            None,
        ),
        (
            "viewer",
            "unaffiliated",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "unaffiliated",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "unaffiliated",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "You do not have permission",
            403,
        ),
        (
            None,
            "unaffiliated",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "unaffiliated",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "Workspace does not exist",
            404,
        ),
        (
            "anonymous",
            "unaffiliated",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "Workspace does not exist",
            404,
        ),
        (
            "owner",
            "fake",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "No account with email",
            400,
        ),
        (
            "owner",
            "owner",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "Account with email",
            400,
        ),
        (
            "owner",
            "viewer",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "Account with email",
            400,
        ),
        (
            "owner",
            "unaffiliated",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "00000000-0000-0000-0000-000000000000",
            "Role does not exist",
            404,
        ),
        (
            "owner",
            "unaffiliated",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "60b9d8b1-28d1-4d0d-9bee-4e47219d0118",
            "Role does not belong to the workspace",
            400,
        ),
    ],
)
def test_create_collaborator(
    get_principal, principal, collaborator, workspace, role, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            collaborator_service.create(
                principal=get_principal(principal),
                workspace_id=uuid.UUID(workspace),
                data=CollaboratorPostBody(
                    email=f"{collaborator}@example.com", role_id=uuid.UUID(role)
                ),
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        collaborator_create = collaborator_service.create(
            principal=get_principal(principal),
            workspace_id=uuid.UUID(workspace),
            data=CollaboratorPostBody(
                email=f"{collaborator}@example.com", role_id=uuid.UUID(role)
            ),
        )
        assert collaborator_create.user.email == f"{collaborator}@example.com"
        assert CollaboratorDetailResponse.from_orm(collaborator_create)


@pytest.mark.parametrize(
    "principal, collaborator, workspace, role, message, error_code",
    [
        (
            "owner",
            "editor",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            None,
            None,
        ),
        (
            "admin",
            "editor",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            None,
            None,
        ),
        (
            "owner",
            "editor",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "60b9d8b1-28d1-4d0d-9bee-4e47219d0118",
            None,
            None,
        ),
        (
            "editor",
            "viewer",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            None,
            None,
        ),
        (
            "viewer",
            "editor",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "editor",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "editor",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "editor",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "Workspace does not exist",
            404,
        ),
        (
            "anonymous",
            "editor",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "editor",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "Workspace does not exist",
            404,
        ),
        (
            "owner",
            "fake",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "No collaborator with email",
            400,
        ),
        (
            "owner",
            "unaffiliated",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "2f05f775-5d8a-4778-9942-3d13a64ec7a3",
            "No collaborator with email",
            400,
        ),
        (
            "owner",
            "editor",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "00000000-0000-0000-0000-000000000000",
            "Role does not exist",
            404,
        ),
        (
            "owner",
            "editor",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "60b9d8b1-28d1-4d0d-9bee-4e47219d0118",
            "Role does not belong to the workspace",
            400,
        ),
    ],
)
def test_update_collaborator(
    get_principal, principal, collaborator, workspace, role, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            collaborator_service.update(
                principal=get_principal(principal),
                workspace_id=uuid.UUID(workspace),
                data=CollaboratorPostBody(
                    email=f"{collaborator}@example.com", role_id=uuid.UUID(role)
                ),
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        collaborator_update = collaborator_service.update(
            principal=get_principal(principal),
            workspace_id=uuid.UUID(workspace),
            data=CollaboratorPostBody(
                email=f"{collaborator}@example.com", role_id=uuid.UUID(role)
            ),
        )
        assert collaborator_update.user.email == f"{collaborator}@example.com"
        assert CollaboratorDetailResponse.from_orm(collaborator_update)


@pytest.mark.parametrize(
    "principal, collaborator, workspace, message, error_code",
    [
        (
            "owner",
            "editor",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Collaborator removed from workspace",
            None,
        ),
        (
            "admin",
            "editor",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Collaborator removed from workspace",
            None,
        ),
        (
            "editor",
            "viewer",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Collaborator removed from workspace",
            None,
        ),
        (
            "viewer",
            "viewer",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Collaborator removed from workspace",
            None,
        ),
        (
            "viewer",
            "editor",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "You do not have permission",
            403,
        ),
        (
            "apikey",
            "editor",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "editor",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "You do not have permission",
            403,
        ),
        (
            "unaffiliated",
            "editor",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
        ),
        (
            "anonymous",
            "editor",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "You do not have permission",
            403,
        ),
        (
            "anonymous",
            "editor",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
        ),
        (
            "owner",
            "fake",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "No collaborator with email",
            400,
        ),
        (
            "owner",
            "unaffiliated",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "No collaborator with email",
            400,
        ),
    ],
)
def test_delete_collaborator(
    get_principal, principal, collaborator, workspace, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            collaborator_service.delete(
                principal=get_principal(principal),
                workspace_id=uuid.UUID(workspace),
                data=CollaboratorDeleteBody(email=f"{collaborator}@example.com"),
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        collaborator_delete = collaborator_service.delete(
            principal=get_principal(principal),
            workspace_id=uuid.UUID(workspace),
            data=CollaboratorDeleteBody(email=f"{collaborator}@example.com"),
        )
        assert collaborator_delete == message
