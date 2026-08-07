import pytest

from core.sta.models import (
    FileAttachmentType,
    SiteType,
    MonitoringSiteTag,
)
from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import MonitoringSiteFactory

pytestmark = pytest.mark.django_db

MONITORING_SITES_URL = "/api/data/monitoring-sites"


def _detail_url(monitoring_site_id):
    return f"{MONITORING_SITES_URL}/{monitoring_site_id}"


def _tags_url(monitoring_site_id):
    return f"{_detail_url(monitoring_site_id)}/tags"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="MonitoringSite", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _monitoring_site_body(workspace_id, **overrides):
    body = {
        "name": "New Monitoring Site",
        "description": "A new site.",
        "code": "SITE-NEW",
        "type": "Stream",
        "latitude": 40.0,
        "longitude": -111.0,
        "isPrivate": False,
        "workspaceId": str(workspace_id),
    }
    body.update(overrides)
    return body


# --- get_monitoring_sites -----------------------------------------------------------------


def test_get_monitoring_sites_includes_public_monitoring_site_for_anonymous(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)

    response = client.get(MONITORING_SITES_URL)

    assert response.status_code == 200
    assert str(monitoring_site.id) in [t["id"] for t in response.json()]


def test_get_monitoring_sites_excludes_private_monitoring_site_for_outsider(client):
    workspace = WorkspaceFactory()
    MonitoringSiteFactory(workspace=workspace, private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(MONITORING_SITES_URL)

    assert response.json() == []


def test_get_monitoring_sites_includes_private_monitoring_site_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace, private=True)
    client.force_login(owner)

    response = client.get(MONITORING_SITES_URL)

    assert response.status_code == 200
    assert str(monitoring_site.id) in [t["id"] for t in response.json()]


# --- create_monitoring_site ------------------------------------------------------------------


def test_create_monitoring_site_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        MONITORING_SITES_URL,
        data=_monitoring_site_body(workspace.id),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["name"] == "New Monitoring Site"


def test_create_monitoring_site_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()

    response = client.post(
        MONITORING_SITES_URL,
        data=_monitoring_site_body(workspace.id),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_monitoring_site_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        MONITORING_SITES_URL,
        data=_monitoring_site_body(workspace.id),
        content_type="application/json",
    )

    assert response.status_code == 403


# --- vocabulary endpoints ----------------------------------------------------------


def test_get_site_types_returns_registered_type_names(client):
    SiteType.objects.create(name="Stream")
    SiteType.objects.create(name="Lake")

    response = client.get(f"{MONITORING_SITES_URL}/site-types")

    assert response.status_code == 200
    assert set(response.json()) == {"Stream", "Lake"}


def test_get_file_attachment_types_returns_registered_type_names(client):
    FileAttachmentType.objects.create(name="Photo")
    FileAttachmentType.objects.create(name="Report")

    response = client.get(f"{MONITORING_SITES_URL}/file-attachment-types")

    assert response.status_code == 200
    assert set(response.json()) == {"Photo", "Report"}


def test_get_site_type_icons_returns_configured_icon_mappings(client):
    response = client.get(f"{MONITORING_SITES_URL}/site-type-icons")

    assert response.status_code == 200
    icons = {entry["icon"] for entry in response.json()}
    assert "gauge" in icons


# --- get_monitoring_site -----------------------------------------------------------------------


def test_get_monitoring_site_returns_public_monitoring_site_for_anonymous(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)

    response = client.get(_detail_url(monitoring_site.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(monitoring_site.id)


def test_get_monitoring_site_preserves_elevation_m_wire_name(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(
        workspace=workspace,
        elevation_m=1380,
    )

    response = client.get(_detail_url(monitoring_site.id))

    assert response.status_code == 200
    assert response.json()["elevation_m"] == 1380
    assert "elevationM" not in response.json()


def test_get_monitoring_site_returns_404_for_private_monitoring_site_when_outsider(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace, private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(monitoring_site.id))

    assert response.status_code == 404


def test_get_monitoring_site_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(_detail_url(monitoring_site.id))

    assert response.status_code == 200


def test_get_monitoring_site_returns_404_for_nonexistent_monitoring_site(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


# --- update_monitoring_site --------------------------------------------------------------------


def test_update_monitoring_site_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace, name="Original Name")
    client.force_login(owner)

    response = client.patch(
        _detail_url(monitoring_site.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_update_monitoring_site_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(monitoring_site.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_monitoring_site --------------------------------------------------------------------


def test_delete_monitoring_site_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(monitoring_site.id))

    assert response.status_code == 204
    assert client.get(_detail_url(monitoring_site.id)).status_code == 404


def test_delete_monitoring_site_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(monitoring_site.id))

    assert response.status_code == 403


# --- get_monitoring_site_tags / add_monitoring_site_tag / edit_monitoring_site_tag / remove_monitoring_site_tag --------------


def test_get_monitoring_site_tags_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    MonitoringSiteTag.objects.create(monitoring_site=monitoring_site, key="season", value="summer")
    client.force_login(owner)

    response = client.get(_tags_url(monitoring_site.id))

    assert response.status_code == 200
    assert {"key": "season", "value": "summer"} in response.json()


def test_get_monitoring_site_tags_returns_404_for_private_monitoring_site_when_outsider(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace, private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_tags_url(monitoring_site.id))

    assert response.status_code == 404


def test_add_monitoring_site_tag_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.post(
        _tags_url(monitoring_site.id),
        data={"key": "season", "value": "summer"},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json() == {"key": "season", "value": "summer"}


def test_add_monitoring_site_tag_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        _tags_url(monitoring_site.id),
        data={"key": "season", "value": "summer"},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_add_monitoring_site_tag_returns_400_for_duplicate_key(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    MonitoringSiteTag.objects.create(monitoring_site=monitoring_site, key="season", value="summer")
    client.force_login(owner)

    response = client.post(
        _tags_url(monitoring_site.id),
        data={"key": "season", "value": "winter"},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_edit_monitoring_site_tag_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    MonitoringSiteTag.objects.create(monitoring_site=monitoring_site, key="season", value="summer")
    client.force_login(owner)

    response = client.put(
        _tags_url(monitoring_site.id),
        data={"key": "season", "value": "winter"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["value"] == "winter"


def test_edit_monitoring_site_tag_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    MonitoringSiteTag.objects.create(monitoring_site=monitoring_site, key="season", value="summer")
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.put(
        _tags_url(monitoring_site.id),
        data={"key": "season", "value": "winter"},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_remove_monitoring_site_tag_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    MonitoringSiteTag.objects.create(monitoring_site=monitoring_site, key="season", value="summer")
    client.force_login(owner)

    response = client.delete(
        _tags_url(monitoring_site.id),
        data={"key": "season"},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not MonitoringSiteTag.objects.filter(monitoring_site=monitoring_site, key="season").exists()


def test_remove_monitoring_site_tag_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    MonitoringSiteTag.objects.create(monitoring_site=monitoring_site, key="season", value="summer")
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(
        _tags_url(monitoring_site.id),
        data={"key": "season"},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_remove_monitoring_site_tag_returns_404_for_unknown_key(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.delete(
        _tags_url(monitoring_site.id),
        data={"key": "unknown"},
        content_type="application/json",
    )

    assert response.status_code == 404


# --- aggregate read endpoints (basic verification only) ------------------------------


def test_get_monitoring_site_markers_returns_marker_for_public_monitoring_site(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)

    response = client.get(f"{MONITORING_SITES_URL}/markers")

    assert response.status_code == 200
    assert str(monitoring_site.id) in [m["id"] for m in response.json()]


def test_get_monitoring_site_site_summaries_returns_summary_for_public_monitoring_site(client):
    workspace = WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)

    response = client.get(f"{MONITORING_SITES_URL}/site-summaries")

    assert response.status_code == 200
    assert str(monitoring_site.id) in [s["id"] for s in response.json()]


def test_get_monitoring_site_task_summaries_returns_summary_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(f"{MONITORING_SITES_URL}/task-summaries")

    assert response.status_code == 200
    summary = next(s for s in response.json() if s["id"] == str(monitoring_site.id))
    assert summary["productTaskCount"] == 0
    assert summary["monitoringTaskCount"] == 0


def test_get_monitoring_site_tag_keys_returns_keys_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    MonitoringSiteTag.objects.create(monitoring_site=monitoring_site, key="season", value="summer")
    client.force_login(owner)

    response = client.get(f"{MONITORING_SITES_URL}/tags/keys")

    assert response.status_code == 200
    assert response.json()["season"] == ["summer"]
