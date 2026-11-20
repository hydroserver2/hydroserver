import pytest
from django.core.exceptions import ImproperlyConfigured

from core.iam.permissions import registry
from core.iam.permissions.registry import register_resource_type, resolve_resource_type


@pytest.fixture(autouse=True)
def isolated_registry(monkeypatch):
    # register_resource_type writes into a module-level global dict that every
    # real model in the app also registers into at import time. Point it at a
    # copy for the duration of each test so dummy registrations here can't
    # collide with real resource types or leak into other tests.
    monkeypatch.setattr(registry, "resource_types", dict(registry.resource_types))


def test_register_resource_type_sets_default_resource_type_from_class_name():
    @register_resource_type()
    class Widget:
        pass

    assert Widget.resource_type == "Widget"


def test_register_resource_type_accepts_custom_resource_type_name():
    @register_resource_type(resource_type_name="CustomWidget")
    class Widget:
        pass

    assert Widget.resource_type == "CustomWidget"


def test_register_resource_type_defaults_workspace_field_to_workspace():
    @register_resource_type()
    class Widget:
        pass

    assert Widget.workspace_field == "workspace"


def test_register_resource_type_accepts_explicit_workspace_field():
    @register_resource_type(workspace_field="monitoring_site__workspace")
    class Widget:
        pass

    assert Widget.workspace_field == "monitoring_site__workspace"


def test_register_resource_type_accepts_workspace_field_none():
    @register_resource_type(workspace_field=None)
    class Widget:
        pass

    assert Widget.workspace_field is None


def test_register_resource_type_defaults_privacy_chain_to_empty_list():
    @register_resource_type()
    class Widget:
        pass

    assert Widget.privacy_chain == []


def test_register_resource_type_accepts_explicit_privacy_chain():
    @register_resource_type(privacy_chain=["is_private"])
    class Widget:
        pass

    assert Widget.privacy_chain == ["is_private"]


def test_register_resource_type_adds_to_registry():
    @register_resource_type()
    class Widget:
        pass

    assert registry.resource_types["Widget"] is Widget


def test_register_resource_type_raises_on_duplicate_resource_type():
    @register_resource_type()
    class Widget:
        pass

    with pytest.raises(ImproperlyConfigured):

        @register_resource_type(resource_type_name="Widget")
        class OtherWidget:
            pass


def test_register_resource_type_returns_the_class_unchanged():
    class Widget:
        pass

    assert register_resource_type()(Widget) is Widget


# --- resolve_resource_type ----------------------------------------------------


def test_resolve_resource_type_returns_string_unchanged():
    assert resolve_resource_type("MonitoringSite") == "MonitoringSite"


def test_resolve_resource_type_returns_class_resource_type():
    @register_resource_type()
    class Widget:
        pass

    assert resolve_resource_type(Widget) == "Widget"