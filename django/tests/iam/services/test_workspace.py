import pytest
import uuid
from collections import Counter
from ninja.errors import HttpError
from django.http import HttpResponse
from domains.iam.services.workspace import WorkspaceService
from interfaces.api.schemas import (
    WorkspacePostBody,
    WorkspacePatchBody,
    WorkspaceTransferBody,
    WorkspaceDetailResponse,
)

workspace_service = WorkspaceService()


@pytest.mark.parametrize(
    "principal, params, workspace_names, max_queries",
    [
        # Test user access
        ("owner", {"expand_related": True}, ["Public", "Private", "Transfer"], 5),
        ("editor", {"expand_related": True}, ["Public", "Private"], 5),
        ("viewer", {"expand_related": True}, ["Public", "Private"], 5),
        ("admin", {"expand_related": True}, ["Public", "Private", "Transfer"], 5),
        ("apikey", {"expand_related": True}, ["Public"], 5),
        ("unaffiliated", {"expand_related": True}, ["Public", "Transfer"], 5),
        ("anonymous", {"expand_related": True}, ["Public"], 5),
        # Test pagination and order_by
        (
            "owner",
            {"page": 2, "page_size": 1, "order_by": "-name", "expand_related": True},
            ["Public"],
            5,
        ),
        # Test filtering
        (
            "owner",
            {"is_private": True, "expand_related": True},
            ["Private", "Transfer"],
            5,
        ),
        (
            "unaffiliated",
            {"is_associated": True, "expand_related": True},
            ["Transfer"],
            5,
        ),
    ],
)
def test_list_workspace(
    django_assert_max_num_queries,
    get_principal,
    principal,
    params,
    workspace_names,
    max_queries,
):
    with django_assert_max_num_queries(max_queries):
        http_response = HttpResponse()
        result = workspace_service.list(
            principal=get_principal(principal),
            response=http_response,
            page=params.pop("page", 1),
            page_size=params.pop("page_size", 100),
            order_by=[params.pop("order_by")] if "order_by" in params else [],
            filtering=params,
        )
        assert Counter(str(workspace.name) for workspace in result) == Counter(
            workspace_names
        )
        assert (WorkspaceDetailResponse.from_orm(workspace) for workspace in result)


@pytest.mark.parametrize(
    "principal, workspace, message, error_code",
    [
        ("owner", "b27c51a0-7374-462d-8a53-d97d47176c10", "Private", None),
        ("admin", "b27c51a0-7374-462d-8a53-d97d47176c10", "Private", None),
        ("apikey", "6e0deaf2-a92b-421b-9ece-86783265596f", "Public", None),
        ("unaffiliated", "6e0deaf2-a92b-421b-9ece-86783265596f", "Public", None),
        ("unaffiliated", "caf4b92e-6914-4449-8c8a-efa5a7fd1826", "Transfer", None),
        ("anonymous", "6e0deaf2-a92b-421b-9ece-86783265596f", "Public", None),
        (
            "owner",
            "00000000-0000-0000-0000-000000000000",
            "Workspace does not exist",
            404,
        ),
        (
            "apikey",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
        ),
        (
            "unaffiliated",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
        ),
        (
            "anonymous",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
        ),
    ],
)
def test_get_workspace(get_principal, principal, workspace, message, error_code):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            workspace_service.get(
                principal=get_principal(principal),
                uid=uuid.UUID(workspace),
                expand_related=True,
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        workspace_get = workspace_service.get(
            principal=get_principal(principal),
            uid=uuid.UUID(workspace),
            expand_related=True,
        )
        assert workspace_get.name == message
        assert WorkspaceDetailResponse.from_orm(workspace_get)


@pytest.mark.parametrize(
    "principal, name, message, error_code",
    [
        ("owner", "New", "New", None),
        ("owner", "Public", "Workspace name or ID conflicts with an owned workspace", 409),
        ("admin", "New", "New", None),
        ("limited", "New", "You do not have permission to create this workspace", 403),
        ("apikey", "New", "You do not have permission to create this workspace", 403),
    ],
)
def test_create_workspace(get_principal, principal, name, message, error_code):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            workspace_service.create(
                principal=get_principal(principal),
                data=WorkspacePostBody(name=name, is_private=False),
                expand_related=True,
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        workspace_create = workspace_service.create(
            principal=get_principal(principal),
            data=WorkspacePostBody(name="New", is_private=False),
            expand_related=True,
        )
        assert workspace_create.name == message
        assert WorkspaceDetailResponse.from_orm(workspace_create)


@pytest.mark.parametrize(
    "principal, workspace, name, message, error_code",
    [
        ("owner", "6e0deaf2-a92b-421b-9ece-86783265596f", "Updated", "Updated", None),
        ("admin", "6e0deaf2-a92b-421b-9ece-86783265596f", "Updated", "Updated", None),
        (
            "owner",
            "00000000-0000-0000-0000-000000000000",
            "Updated",
            "Workspace does not exist",
            404,
        ),
        (
            "owner",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "Private",
            "Workspace name conflicts with an owned workspace",
            409,
        ),
        (
            "apikey",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Updated",
            "Workspace does not exist",
            404,
        ),
        (
            "anonymous",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Updated",
            "Workspace does not exist",
            404,
        ),
        (
            "apikey",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "Updated",
            "You do not have permission to edit this workspace",
            403,
        ),
        (
            "anonymous",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "Updated",
            "You do not have permission to edit this workspace",
            403,
        ),
        (
            None,
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Updated",
            "Workspace does not exist",
            404,
        ),
        (
            None,
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "Updated",
            "You do not have permission to edit this workspace",
            403,
        ),
    ],
)
def test_update_workspace(
    get_principal, principal, workspace, name, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            workspace_service.update(
                principal=get_principal(principal),
                uid=uuid.UUID(workspace),
                data=WorkspacePatchBody(name=name, is_private=False),
                expand_related=True,
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        workspace_update = workspace_service.update(
            principal=get_principal(principal),
            uid=uuid.UUID(workspace),
            data=WorkspacePatchBody(name="Updated", is_private=False),
            expand_related=True,
        )
        assert workspace_update.name == message
        assert WorkspaceDetailResponse.from_orm(workspace_update)


@pytest.mark.parametrize(
    "principal, workspace, message, error_code, max_queries",
    [
        (
            "owner",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "Workspace deleted",
            None,
            42,
        ),
        (
            "admin",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "Workspace deleted",
            None,
            42,
        ),
        (
            "owner",
            "00000000-0000-0000-0000-000000000000",
            "Workspace does not exist",
            404,
            2,
        ),
        (
            "apikey",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
            5,
        ),
        (
            "anonymous",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
            5,
        ),
        (
            None,
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
            5,
        ),
        (
            "editor",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "You do not have permission to delete this workspace",
            403,
            3,
        ),
    ],
)
def test_delete_workspace(
    django_assert_max_num_queries,
    get_principal,
    principal,
    workspace,
    message,
    error_code,
    max_queries,
):
    with django_assert_max_num_queries(max_queries):
        if error_code:
            with pytest.raises(HttpError) as exc_info:
                workspace_service.delete(
                    principal=get_principal(principal), uid=uuid.UUID(workspace)
                )
            assert exc_info.value.status_code == error_code
            assert exc_info.value.message.startswith(message)
        else:
            workspace_delete = workspace_service.delete(
                principal=get_principal(principal), uid=uuid.UUID(workspace)
            )
            assert workspace_delete == message


@pytest.mark.parametrize(
    "from_user, to_user, workspace, message, error_code",
    [
        (
            "owner",
            "unaffiliated",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "Workspace transfer initiated",
            None,
        ),
        (
            "admin",
            "unaffiliated",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "Workspace transfer initiated",
            None,
        ),
        (
            "owner",
            "unaffiliated",
            "00000000-0000-0000-0000-000000000000",
            "Workspace does not exist",
            404,
        ),
        (
            "apikey",
            "viewer",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
        ),
        (
            "unaffiliated",
            "viewer",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
        ),
        (
            "anonymous",
            "viewer",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
        ),
        (
            "editor",
            "viewer",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "You do not have permission to transfer",
            403,
        ),
        (
            "owner",
            "fake",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "No account with email",
            400,
        ),
        (
            "owner",
            "limited",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "Workspace cannot be transferred to user",
            400,
        ),
        (
            "owner",
            "owner",
            "6e0deaf2-a92b-421b-9ece-86783265596f",
            "Workspace already owned by user",
            400,
        ),
        (
            "owner",
            "unaffiliated",
            "caf4b92e-6914-4449-8c8a-efa5a7fd1826",
            "Workspace transfer is already pending",
            400,
        ),
    ],
)
def test_transfer_workspace(
    get_principal, from_user, to_user, workspace, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            workspace_service.transfer(
                principal=get_principal(from_user),
                uid=uuid.UUID(workspace),
                data=WorkspaceTransferBody(
                    new_owner=getattr(
                        get_principal(to_user), "email", "fake@example.com"
                    )
                ),
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        workspace_transfer = workspace_service.transfer(
            principal=get_principal(from_user),
            uid=uuid.UUID(workspace),
            data=WorkspaceTransferBody(new_owner=get_principal(to_user).email),
        )
        assert workspace_transfer == message


@pytest.mark.parametrize(
    "principal, workspace, message, error_code",
    [
        (
            "unaffiliated",
            "caf4b92e-6914-4449-8c8a-efa5a7fd1826",
            "Workspace transfer accepted",
            None,
        ),
        (
            "apikey",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
        ),
        (
            "anonymous",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
        ),
        (
            None,
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
        ),
        (
            "owner",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "No workspace transfer is pending",
            400,
        ),
        (
            "owner",
            "caf4b92e-6914-4449-8c8a-efa5a7fd1826",
            "You do not have permission to accept",
            403,
        ),
    ],
)
def test_accept_workspace_transfer(
    get_principal, principal, workspace, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            workspace_service.accept_transfer(
                principal=get_principal(principal), uid=uuid.UUID(workspace)
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        workspace_transfer = workspace_service.accept_transfer(
            principal=get_principal(principal), uid=uuid.UUID(workspace)
        )
        workspace_get, _ = workspace_service.get_workspace(
            principal=get_principal(principal), workspace_id=uuid.UUID(workspace)
        )
        assert workspace_transfer == message
        assert workspace_get.owner == get_principal(principal)


@pytest.mark.parametrize(
    "principal, workspace, message, error_code",
    [
        (
            "unaffiliated",
            "caf4b92e-6914-4449-8c8a-efa5a7fd1826",
            "Workspace transfer rejected",
            None,
        ),
        (
            "owner",
            "caf4b92e-6914-4449-8c8a-efa5a7fd1826",
            "Workspace transfer rejected",
            None,
        ),
        (
            "apikey",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
        ),
        (
            "anonymous",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
        ),
        (
            None,
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "Workspace does not exist",
            404,
        ),
        (
            "owner",
            "b27c51a0-7374-462d-8a53-d97d47176c10",
            "No workspace transfer is pending",
            400,
        ),
    ],
)
def test_reject_workspace_transfer(
    get_principal, principal, workspace, message, error_code
):
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            workspace_service.reject_transfer(
                principal=get_principal(principal), uid=uuid.UUID(workspace)
            )
        assert exc_info.value.status_code == error_code
        assert exc_info.value.message.startswith(message)
    else:
        workspace_transfer = workspace_service.reject_transfer(
            principal=get_principal(principal), uid=uuid.UUID(workspace)
        )
        assert workspace_transfer == message
