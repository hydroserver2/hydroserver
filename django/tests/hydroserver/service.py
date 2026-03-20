# import pytest
# import uuid
# from ninja.errors import HttpError
# from hydroserver.service import ServiceUtils
#
# service_utils = ServiceUtils()
#
#
# def raise_404():
#     raise HttpError(404, "Not found")
#
#
# def raise_500():
#     raise HttpError(500, "Server error")
#
#
# def test_handle_http_404_error_raises_400():
#     with pytest.raises(HttpError) as exc_info:
#         ServiceUtils.handle_http_404_error(raise_404)
#     assert exc_info.value.status_code == 400
#     assert "Not found" in exc_info.value.message
#
#
# def test_handle_http_404_error_rethrows_non_404():
#     with pytest.raises(HttpError) as exc_info:
#         ServiceUtils.handle_http_404_error(raise_500)
#     assert exc_info.value.status_code == 500
#
#
# @pytest.mark.parametrize(
#     "principal, workspace, message, permissions, error_code",
#     [
#         (
#             "owner",
#             "b27c51a0-7374-462d-8a53-d97d47176c10",
#             "Private",
#             {"view", "edit", "delete"},
#             None,
#         ),
#         (
#             "admin",
#             "b27c51a0-7374-462d-8a53-d97d47176c10",
#             "Private",
#             {"view", "edit", "delete"},
#             None,
#         ),
#         ("editor", "b27c51a0-7374-462d-8a53-d97d47176c10", "Private", {"view"}, None),
#         ("viewer", "b27c51a0-7374-462d-8a53-d97d47176c10", "Private", {"view"}, None),
#         ("apikey", "6e0deaf2-a92b-421b-9ece-86783265596f", "Public", {"view"}, None),
#         ("anonymous", "6e0deaf2-a92b-421b-9ece-86783265596f", "Public", {"view"}, None),
#         (None, "6e0deaf2-a92b-421b-9ece-86783265596f", "Public", {"view"}, None),
#         (
#             "anonymous",
#             "caf4b92e-6914-4449-8c8a-efa5a7fd1826",
#             "Transfer",
#             {"view"},
#             None,
#         ),
#         (
#             "owner",
#             "00000000-0000-0000-0000-000000000000",
#             "Workspace does not exist",
#             {},
#             404,
#         ),
#         (
#             "apikey",
#             "b27c51a0-7374-462d-8a53-d97d47176c10",
#             "Workspace does not exist",
#             {},
#             404,
#         ),
#         (
#             "anonymous",
#             "b27c51a0-7374-462d-8a53-d97d47176c10",
#             "Workspace does not exist",
#             {},
#             404,
#         ),
#         (
#             None,
#             "b27c51a0-7374-462d-8a53-d97d47176c10",
#             "Workspace does not exist",
#             {},
#             404,
#         ),
#     ],
# )
# def test_get_workspace(
#     get_principal, principal, workspace, message, permissions, error_code
# ):
#     if error_code:
#         with pytest.raises(HttpError) as exc_info:
#             service_utils.get_workspace(
#                 principal=get_principal(principal), workspace_id=uuid.UUID(workspace)
#             )
#         assert exc_info.value.status_code == error_code
#         assert exc_info.value.message.startswith(message)
#     else:
#         workspace_get, workspace_permissions = service_utils.get_workspace(
#             principal=get_principal(principal), workspace_id=uuid.UUID(workspace)
#         )
#         assert workspace_get.name == message
#         assert set(workspace_permissions) == permissions
#
#
# @pytest.mark.django_db
# @pytest.mark.parametrize("values,expected_ids", [
#     (None, [1, 2, 3]),
#     (1, [1]),
#     ([1], [1]),
#     ([1, 2], [1, 2]),
#     ([], [1, 2, 3]),
# ])
# def test_apply_filters(sample_model, values, expected_ids):
#     queryset = sample_model.objects.all()
#     filtered = ServiceUtils.apply_filters(queryset, "id", values)
#     assert list(filtered.values_list("id", flat=True)) == expected_ids
#
#
# def apply_ordering():
#     pass
#
#
# def test_apply_pagination():
#     pass
