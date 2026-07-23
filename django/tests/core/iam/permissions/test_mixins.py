import types

import pytest

from core.iam.models import Workspace
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.iam.permissions.mixins import ResourcePermissionMixin
from core.sta.models import Sensor, Thing
from tests.core.iam.factories import (
    CollaboratorFactory,
    PermissionFactory,
    RoleFactory,
    ServiceAccountFactory,
    UserFactory,
    WorkspaceFactory,
)
from tests.core.sta.factories import SensorFactory, ThingFactory


# --- is_superuser_principal --------------------------------------------------


def test_is_superuser_principal_true_for_superuser():
    principal = UserFactory.build(is_superuser=True)
    assert principal.is_superuser_principal() is True


def test_is_superuser_principal_false_for_non_superuser():
    principal = UserFactory.build(is_superuser=False)
    assert principal.is_superuser_principal() is False


def test_is_superuser_principal_false_for_service_account():
    principal = ServiceAccountFactory.build()
    assert principal.is_superuser_principal() is False


def test_is_superuser_principal_false_for_anonymous():
    assert AnonymousPrincipal().is_superuser_principal() is False


# --- _resolve_workspace -------------------------------------------------------


def test_resolve_workspace_returns_resource_itself_when_field_is_none():
    workspace = Workspace()
    assert ResourcePermissionMixin._resolve_workspace(workspace, None) is workspace


def test_resolve_workspace_returns_none_when_field_is_none_and_not_a_workspace():
    resource = types.SimpleNamespace()
    assert ResourcePermissionMixin._resolve_workspace(resource, None) is None


def test_resolve_workspace_single_hop():
    workspace = Workspace()
    resource = types.SimpleNamespace(workspace=workspace)
    assert ResourcePermissionMixin._resolve_workspace(resource, "workspace") is workspace


def test_resolve_workspace_multi_hop():
    workspace = Workspace()
    resource = types.SimpleNamespace(thing=types.SimpleNamespace(workspace=workspace))

    assert ResourcePermissionMixin._resolve_workspace(resource, "thing__workspace") is workspace


def test_resolve_workspace_returns_none_when_final_hop_is_unset_and_nullable():
    sensor = Sensor()
    assert ResourcePermissionMixin._resolve_workspace(sensor, "workspace") is None


def test_resolve_workspace_short_circuits_on_none_intermediate():
    resource = types.SimpleNamespace(thing=types.SimpleNamespace(workspace=None))
    assert ResourcePermissionMixin._resolve_workspace(resource, "thing__workspace") is None


# --- can_view / can_edit / can_delete: annotated-queryset shortcut -----------


def test_can_view_returns_annotated_value_directly():
    resource = types.SimpleNamespace(can_view=False)
    principal = UserFactory.build(is_superuser=True)

    assert principal.can_view(resource) is False


def test_can_edit_returns_annotated_value_directly():
    resource = types.SimpleNamespace(can_edit=True)
    principal = AnonymousPrincipal()

    assert principal.can_edit(resource) is True


def test_can_delete_returns_annotated_value_directly():
    resource = types.SimpleNamespace(can_delete=True)
    principal = AnonymousPrincipal()

    assert principal.can_delete(resource) is True


# --- can_view / can_edit / can_delete: superuser short-circuit ---------------


def test_can_view_true_for_superuser_without_resolving_workspace():
    resource = Thing()
    principal = UserFactory.build(is_superuser=True)

    assert principal.can_view(resource) is True


def test_can_edit_true_for_superuser_without_resolving_workspace():
    resource = Thing()
    principal = UserFactory.build(is_superuser=True)

    assert principal.can_edit(resource) is True


def test_can_delete_true_for_superuser_without_resolving_workspace():
    resource = Thing()
    principal = UserFactory.build(is_superuser=True)

    assert principal.can_delete(resource) is True


# --- can_view: public resource via privacy_chain -----------------------------


def test_can_view_true_for_public_resource_via_privacy_chain():
    workspace = Workspace(is_private=False)
    principal = AnonymousPrincipal()

    assert principal.can_view(workspace) is True


# --- can_view / can_edit / can_delete: workspace-less (global) resources -----


def test_can_view_true_for_workspace_less_resource():
    sensor = Sensor()
    principal = AnonymousPrincipal()

    assert principal.can_view(sensor) is True


def test_can_edit_false_for_workspace_less_resource():
    sensor = Sensor()
    principal = AnonymousPrincipal()

    assert principal.can_edit(sensor) is False


def test_can_delete_false_for_workspace_less_resource():
    sensor = Sensor()
    principal = AnonymousPrincipal()

    assert principal.can_delete(sensor) is False


# --- can_create ---------------------------------------------------------------


def test_can_create_true_for_superuser():
    principal = UserFactory.build(is_superuser=True)
    assert principal.can_create("Thing", workspace=None) is True


def test_can_create_false_without_workspace_for_non_superuser():
    principal = AnonymousPrincipal()
    assert principal.can_create("Thing", workspace=None) is False


# --- has_permission: early-exit branches --------------------------------------


def test_has_permission_true_for_superuser():
    principal = UserFactory.build(is_superuser=True)
    assert (
        principal.has_permission(None, resource_type="Thing", permission_field="can_view")
        is True
    )


def test_has_permission_false_when_workspace_is_none():
    principal = AnonymousPrincipal()
    assert (
        principal.has_permission(None, resource_type="Thing", permission_field="can_view")
        is False
    )


def test_has_permission_true_for_workspace_owner():
    owner = UserFactory.build(id=42)
    workspace = Workspace(owner_id=42)

    assert (
        owner.has_permission(workspace, resource_type="Thing", permission_field="can_edit")
        is True
    )


# --- has_permission: Collaborator-backed branch ------------------------------


@pytest.mark.django_db
def test_has_permission_true_for_collaborator_with_matching_grant():
    workspace = WorkspaceFactory()
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="Thing", can_view=True)
    collaborator = CollaboratorFactory(workspace=workspace, role=role)

    assert (
        collaborator.user.has_permission(
            workspace, resource_type="Thing", permission_field="can_view"
        )
        is True
    )


@pytest.mark.django_db
def test_has_permission_true_for_collaborator_with_wildcard_resource_type():
    workspace = WorkspaceFactory()
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="*", can_view=True)
    collaborator = CollaboratorFactory(workspace=workspace, role=role)

    assert (
        collaborator.user.has_permission(
            workspace, resource_type="Thing", permission_field="can_view"
        )
        is True
    )


@pytest.mark.django_db
def test_has_permission_false_when_permission_field_not_granted():
    workspace = WorkspaceFactory()
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="Thing", can_view=True, can_edit=False)
    collaborator = CollaboratorFactory(workspace=workspace, role=role)

    assert (
        collaborator.user.has_permission(
            workspace, resource_type="Thing", permission_field="can_edit"
        )
        is False
    )


@pytest.mark.django_db
def test_has_permission_false_for_collaborator_in_different_workspace():
    other_workspace = WorkspaceFactory()
    role = RoleFactory(workspace=other_workspace)
    PermissionFactory(role=role, resource_type="Thing", can_view=True)
    CollaboratorFactory(workspace=other_workspace, role=role)

    workspace = WorkspaceFactory()  # the workspace actually being checked
    outsider = UserFactory()

    assert (
        outsider.has_permission(workspace, resource_type="Thing", permission_field="can_view")
        is False
    )


@pytest.mark.django_db
def test_has_permission_false_for_non_collaborator():
    workspace = WorkspaceFactory()
    principal = UserFactory()

    assert (
        principal.has_permission(workspace, resource_type="Thing", permission_field="can_view")
        is False
    )


@pytest.mark.django_db
def test_has_permission_true_for_service_account_collaborator():
    workspace = WorkspaceFactory()
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="Thing", can_view=True)
    collaborator = CollaboratorFactory(
        workspace=workspace, role=role, service_account_collaborator=True
    )

    assert (
        collaborator.service_account.has_permission(
            workspace, resource_type="Thing", permission_field="can_view"
        )
        is True
    )


@pytest.mark.django_db
def test_has_permission_false_for_service_account_non_collaborator():
    workspace = WorkspaceFactory()
    principal = ServiceAccountFactory()

    assert (
        principal.has_permission(workspace, resource_type="Thing", permission_field="can_view")
        is False
    )


@pytest.mark.django_db
def test_has_permission_false_for_anonymous_despite_existing_grant():
    workspace = WorkspaceFactory()
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="*", can_view=True, can_edit=True, can_delete=True)
    # A real grant exists and would apply to any user/service_account
    # collaborator on this role — anonymous still can't match a Collaborator row.
    CollaboratorFactory(workspace=workspace, role=role)

    assert (
        AnonymousPrincipal().has_permission(
            workspace, resource_type="Thing", permission_field="can_view"
        )
        is False
    )


# --- filter_by_permission -----------------------------------------------------


@pytest.mark.django_db
def test_filter_by_permission_includes_owned_resources():
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner, is_private=True)
    thing = ThingFactory(workspace=workspace, is_private=True)
    ThingFactory(is_private=True)  # unrelated thing, different owner/workspace

    visible = owner.filter_by_permission(Thing.objects.all(), "can_view")

    assert list(visible) == [thing]


@pytest.mark.django_db
def test_filter_by_permission_includes_collaborator_granted_resources():
    workspace = WorkspaceFactory(is_private=True)
    thing = ThingFactory(workspace=workspace, is_private=True)
    role = RoleFactory(workspace=workspace)
    PermissionFactory(role=role, resource_type="Thing", can_view=True)
    collaborator = CollaboratorFactory(workspace=workspace, role=role)

    visible = collaborator.user.filter_by_permission(Thing.objects.all(), "can_view")

    assert list(visible) == [thing]


@pytest.mark.django_db
def test_filter_by_permission_excludes_resources_without_grant():
    workspace = WorkspaceFactory(is_private=True)
    ThingFactory(workspace=workspace, is_private=True)
    outsider = UserFactory()

    visible = outsider.filter_by_permission(Thing.objects.all(), "can_view")

    assert list(visible) == []


@pytest.mark.django_db
def test_filter_by_permission_includes_public_resources_for_view_but_not_private():
    public_workspace = WorkspaceFactory(is_private=False)
    public_thing = ThingFactory(workspace=public_workspace, is_private=False)

    private_workspace = WorkspaceFactory(is_private=True)
    ThingFactory(workspace=private_workspace, is_private=True)

    outsider = UserFactory()
    visible = outsider.filter_by_permission(Thing.objects.all(), "can_view")

    assert list(visible) == [public_thing]


@pytest.mark.django_db
def test_filter_by_permission_excludes_public_resources_for_edit():
    workspace = WorkspaceFactory(is_private=False)
    ThingFactory(workspace=workspace, is_private=False)
    outsider = UserFactory()

    visible = outsider.filter_by_permission(Thing.objects.all(), "can_edit")

    assert list(visible) == []


@pytest.mark.django_db
def test_filter_by_permission_includes_global_vocabulary_for_view():
    global_sensor = SensorFactory(global_=True)
    SensorFactory(workspace=WorkspaceFactory(is_private=True))  # scoped elsewhere
    outsider = UserFactory()

    visible = outsider.filter_by_permission(Sensor.objects.all(), "can_view")

    assert list(visible) == [global_sensor]


@pytest.mark.django_db
def test_filter_by_permission_excludes_global_vocabulary_for_edit():
    SensorFactory(global_=True)
    outsider = UserFactory()

    visible = outsider.filter_by_permission(Sensor.objects.all(), "can_edit")

    assert list(visible) == []


@pytest.mark.django_db
def test_filter_by_permission_returns_everything_for_superuser():
    ThingFactory(is_private=True, workspace=WorkspaceFactory(is_private=True))
    ThingFactory(is_private=True, workspace=WorkspaceFactory(is_private=True))
    superuser = UserFactory(is_superuser=True)

    visible = superuser.filter_by_permission(Thing.objects.all(), "can_view")

    assert visible.count() == 2


# --- annotate_permissions: consistency with can_view/can_edit/can_delete -----


@pytest.mark.django_db
def test_annotate_permissions_matches_per_object_checks_for_owner():
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner, is_private=True)
    thing = ThingFactory(workspace=workspace, is_private=True)

    annotated = owner.annotate_permissions(Thing.objects.all()).get(pk=thing.pk)

    assert annotated.can_view == owner.can_view(thing)
    assert annotated.can_edit == owner.can_edit(thing)
    assert annotated.can_delete == owner.can_delete(thing)
    assert (annotated.can_view, annotated.can_edit, annotated.can_delete) == (True, True, True)


@pytest.mark.django_db
def test_annotate_permissions_matches_per_object_checks_for_partial_grant():
    workspace = WorkspaceFactory(is_private=True)
    thing = ThingFactory(workspace=workspace, is_private=True)
    role = RoleFactory(workspace=workspace)
    PermissionFactory(
        role=role, resource_type="Thing", can_view=True, can_edit=False, can_delete=False
    )
    collaborator = CollaboratorFactory(workspace=workspace, role=role)
    principal = collaborator.user

    annotated = principal.annotate_permissions(Thing.objects.all()).get(pk=thing.pk)

    assert annotated.can_view == principal.can_view(thing) is True
    assert annotated.can_edit == principal.can_edit(thing) is False
    assert annotated.can_delete == principal.can_delete(thing) is False


@pytest.mark.django_db
def test_annotate_permissions_matches_per_object_checks_for_outsider():
    workspace = WorkspaceFactory(is_private=True)
    thing = ThingFactory(workspace=workspace, is_private=True)
    outsider = UserFactory()

    annotated = outsider.annotate_permissions(Thing.objects.all()).get(pk=thing.pk)

    assert annotated.can_view == outsider.can_view(thing) is False
    assert annotated.can_edit == outsider.can_edit(thing) is False
    assert annotated.can_delete == outsider.can_delete(thing) is False


@pytest.mark.django_db
def test_annotate_permissions_true_for_all_fields_for_superuser():
    thing = ThingFactory(is_private=True, workspace=WorkspaceFactory(is_private=True))
    superuser = UserFactory(is_superuser=True)

    annotated = superuser.annotate_permissions(Thing.objects.all()).get(pk=thing.pk)

    assert (annotated.can_view, annotated.can_edit, annotated.can_delete) == (True, True, True)
