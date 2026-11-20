from core.iam.permissions.anonymous import AnonymousPrincipal
from core.iam.permissions.mixins import ResourcePermissionMixin


def test_is_authenticated_false():
    assert AnonymousPrincipal().is_authenticated is False


def test_is_anonymous_true():
    assert AnonymousPrincipal().is_anonymous is True


def test_not_falsy():
    assert bool(AnonymousPrincipal()) is True


def test_is_a_resource_permission_mixin():
    assert isinstance(AnonymousPrincipal(), ResourcePermissionMixin)
