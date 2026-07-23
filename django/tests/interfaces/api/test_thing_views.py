import pytest

from core.sta.models import (
    FileAttachmentType,
    SamplingFeatureType,
    SiteType,
    ThingTag,
)
from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import LocationFactory, ThingFactory

pytestmark = pytest.mark.django_db

THINGS_URL = "/api/data/things"


def _detail_url(thing_id):
    return f"{THINGS_URL}/{thing_id}"


def _tags_url(thing_id):
    return f"{_detail_url(thing_id)}/tags"


def _collaborator_with_permission(workspace, **permissions):
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="Thing", **permissions)
    return CollaboratorFactory(workspace=workspace, role=role)


def _make_thing(workspace, **kwargs):
    thing = ThingFactory(workspace=workspace, **kwargs)
    LocationFactory(thing=thing, latitude=40.0, longitude=-111.0)
    return thing


def _thing_body(workspace_id, **overrides):
    body = {
        "name": "New Thing",
        "description": "A new site.",
        "samplingFeatureType": "Site",
        "samplingFeatureCode": "SITE-NEW",
        "siteType": "Stream",
        "isPrivate": False,
        "workspaceId": str(workspace_id),
        "location": {"latitude": 40.0, "longitude": -111.0},
    }
    body.update(overrides)
    return body


# --- get_things -----------------------------------------------------------------


def test_get_things_includes_public_thing_for_anonymous(client):
    workspace = WorkspaceFactory()
    thing = _make_thing(workspace)

    response = client.get(THINGS_URL)

    assert response.status_code == 200
    assert str(thing.id) in [t["id"] for t in response.json()]


def test_get_things_excludes_private_thing_for_outsider(client):
    workspace = WorkspaceFactory()
    _make_thing(workspace, private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(THINGS_URL)

    assert response.json() == []


def test_get_things_includes_private_thing_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    thing = _make_thing(workspace, private=True)
    client.force_login(owner)

    response = client.get(THINGS_URL)

    assert response.status_code == 200
    assert str(thing.id) in [t["id"] for t in response.json()]


# --- create_thing ------------------------------------------------------------------


def test_create_thing_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    client.force_login(owner)

    response = client.post(
        THINGS_URL,
        data=_thing_body(workspace.id),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["name"] == "New Thing"


def test_create_thing_returns_401_when_unauthenticated(client):
    workspace = WorkspaceFactory()

    response = client.post(
        THINGS_URL,
        data=_thing_body(workspace.id),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_thing_returns_403_without_create_permission(client):
    workspace = WorkspaceFactory()
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        THINGS_URL,
        data=_thing_body(workspace.id),
        content_type="application/json",
    )

    assert response.status_code == 403


# --- vocabulary endpoints ----------------------------------------------------------


def test_get_site_types_returns_registered_type_names(client):
    SiteType.objects.create(name="Stream")
    SiteType.objects.create(name="Lake")

    response = client.get(f"{THINGS_URL}/site-types")

    assert response.status_code == 200
    assert set(response.json()) == {"Stream", "Lake"}


def test_get_sampling_feature_types_returns_registered_type_names(client):
    SamplingFeatureType.objects.create(name="Site")
    SamplingFeatureType.objects.create(name="Specimen")

    response = client.get(f"{THINGS_URL}/sampling-feature-types")

    assert response.status_code == 200
    assert set(response.json()) == {"Site", "Specimen"}


def test_get_file_attachment_types_returns_registered_type_names(client):
    FileAttachmentType.objects.create(name="Photo")
    FileAttachmentType.objects.create(name="Report")

    response = client.get(f"{THINGS_URL}/file-attachment-types")

    assert response.status_code == 200
    assert set(response.json()) == {"Photo", "Report"}


def test_get_site_type_icons_returns_configured_icon_mappings(client):
    response = client.get(f"{THINGS_URL}/site-type-icons")

    assert response.status_code == 200
    icons = {entry["icon"] for entry in response.json()}
    assert "gauge" in icons


# --- get_thing -----------------------------------------------------------------------


def test_get_thing_returns_public_thing_for_anonymous(client):
    workspace = WorkspaceFactory()
    thing = _make_thing(workspace)

    response = client.get(_detail_url(thing.id))

    assert response.status_code == 200
    assert response.json()["id"] == str(thing.id)


def test_get_thing_returns_404_for_private_thing_when_outsider(client):
    workspace = WorkspaceFactory()
    thing = _make_thing(workspace, private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_detail_url(thing.id))

    assert response.status_code == 404


def test_get_thing_returns_200_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    thing = _make_thing(workspace)
    client.force_login(owner)

    response = client.get(_detail_url(thing.id))

    assert response.status_code == 200


def test_get_thing_returns_404_for_nonexistent_thing(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


# --- update_thing --------------------------------------------------------------------


def test_update_thing_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    thing = _make_thing(workspace, name="Original Name")
    client.force_login(owner)

    response = client.patch(
        _detail_url(thing.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_update_thing_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    thing = _make_thing(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.patch(
        _detail_url(thing.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_thing --------------------------------------------------------------------


def test_delete_thing_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    thing = _make_thing(workspace)
    client.force_login(owner)

    response = client.delete(_detail_url(thing.id))

    assert response.status_code == 204
    assert client.get(_detail_url(thing.id)).status_code == 404


def test_delete_thing_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    thing = _make_thing(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(_detail_url(thing.id))

    assert response.status_code == 403


# --- get_thing_tags / add_thing_tag / edit_thing_tag / remove_thing_tag --------------


def test_get_thing_tags_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    thing = _make_thing(workspace)
    ThingTag.objects.create(thing=thing, key="season", value="summer")
    client.force_login(owner)

    response = client.get(_tags_url(thing.id))

    assert response.status_code == 200
    assert {"key": "season", "value": "summer"} in response.json()


def test_get_thing_tags_returns_404_for_private_thing_when_outsider(client):
    workspace = WorkspaceFactory()
    thing = _make_thing(workspace, private=True)
    outsider = UserFactory()
    client.force_login(outsider)

    response = client.get(_tags_url(thing.id))

    assert response.status_code == 404


def test_add_thing_tag_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    thing = _make_thing(workspace)
    client.force_login(owner)

    response = client.post(
        _tags_url(thing.id),
        data={"key": "season", "value": "summer"},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json() == {"key": "season", "value": "summer"}


def test_add_thing_tag_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    thing = _make_thing(workspace)
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.post(
        _tags_url(thing.id),
        data={"key": "season", "value": "summer"},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_add_thing_tag_returns_400_for_duplicate_key(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    thing = _make_thing(workspace)
    ThingTag.objects.create(thing=thing, key="season", value="summer")
    client.force_login(owner)

    response = client.post(
        _tags_url(thing.id),
        data={"key": "season", "value": "winter"},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_edit_thing_tag_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    thing = _make_thing(workspace)
    ThingTag.objects.create(thing=thing, key="season", value="summer")
    client.force_login(owner)

    response = client.put(
        _tags_url(thing.id),
        data={"key": "season", "value": "winter"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["value"] == "winter"


def test_edit_thing_tag_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    thing = _make_thing(workspace)
    ThingTag.objects.create(thing=thing, key="season", value="summer")
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.put(
        _tags_url(thing.id),
        data={"key": "season", "value": "winter"},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_remove_thing_tag_succeeds_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    thing = _make_thing(workspace)
    ThingTag.objects.create(thing=thing, key="season", value="summer")
    client.force_login(owner)

    response = client.delete(
        _tags_url(thing.id),
        data={"key": "season"},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not ThingTag.objects.filter(thing=thing, key="season").exists()


def test_remove_thing_tag_returns_403_for_viewer_collaborator(client):
    workspace = WorkspaceFactory()
    thing = _make_thing(workspace)
    ThingTag.objects.create(thing=thing, key="season", value="summer")
    collaborator = _collaborator_with_permission(workspace, can_view=True)
    client.force_login(collaborator.user)

    response = client.delete(
        _tags_url(thing.id),
        data={"key": "season"},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_remove_thing_tag_returns_404_for_unknown_key(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    thing = _make_thing(workspace)
    client.force_login(owner)

    response = client.delete(
        _tags_url(thing.id),
        data={"key": "unknown"},
        content_type="application/json",
    )

    assert response.status_code == 404


# --- aggregate read endpoints (basic verification only) ------------------------------


def test_get_thing_markers_returns_marker_for_public_thing(client):
    workspace = WorkspaceFactory()
    thing = _make_thing(workspace)

    response = client.get(f"{THINGS_URL}/markers")

    assert response.status_code == 200
    assert str(thing.id) in [m["id"] for m in response.json()]


def test_get_thing_site_summaries_returns_summary_for_public_thing(client):
    workspace = WorkspaceFactory()
    thing = _make_thing(workspace)

    response = client.get(f"{THINGS_URL}/site-summaries")

    assert response.status_code == 200
    assert str(thing.id) in [s["id"] for s in response.json()]


def test_get_thing_task_summaries_returns_summary_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    thing = ThingFactory(workspace=workspace)
    client.force_login(owner)

    response = client.get(f"{THINGS_URL}/task-summaries")

    assert response.status_code == 200
    summary = next(s for s in response.json() if s["id"] == str(thing.id))
    assert summary["productTaskCount"] == 0
    assert summary["monitoringTaskCount"] == 0


def test_get_thing_tag_keys_returns_keys_for_workspace_owner(client):
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    thing = _make_thing(workspace)
    ThingTag.objects.create(thing=thing, key="season", value="summer")
    client.force_login(owner)

    response = client.get(f"{THINGS_URL}/tags/keys")

    assert response.status_code == 200
    assert response.json()["season"] == ["summer"]
