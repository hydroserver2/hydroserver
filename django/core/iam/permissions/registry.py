from django.core.exceptions import ImproperlyConfigured

resource_types: dict[str, type] = {}


def register_resource_type(
    workspace_field: str | None = "workspace",
    privacy_chain: list[str] | None = None,
    resource_type_name: str | None = None,
):
    """
    Register a model as a gatekept permission resource type.

    workspace_field: None if the model itself is a Workspace, else a path to
    reach one (e.g. "monitoring_site__workspace"). resource_type_name: overrides the
    resource_type string (default: model_cls.__name__) — needed since
    resource_type is a flat namespace and two apps' models can share a name.

    No dependency on core.iam.models: models import this decorator at
    class-definition time, so importing core.iam.models here would be circular.
    """

    def decorator(model_cls):
        resource_type = resource_type_name or model_cls.__name__

        if resource_type in resource_types:
            raise ImproperlyConfigured(
                f"Resource type '{resource_type}' is already registered to "
                f"{resource_types[resource_type].__module__}.{resource_types[resource_type].__qualname__}; "
                f"cannot also register it to {model_cls.__module__}.{model_cls.__qualname__}. "
                "Pass resource_type_name= to give one of them a distinct name."
            )

        resource_types[resource_type] = model_cls

        model_cls.resource_type = resource_type
        model_cls.workspace_field = workspace_field
        model_cls.privacy_chain = privacy_chain or []

        return model_cls

    return decorator


def resolve_resource_type(resource_type: "str | type") -> str:
    """
    Normalize a resource_type argument to its string form.

    Accepts either the string already (e.g. "Datastream") or the registered model
    class itself (e.g., Datastream), so callers that don't have an instance on hand
    yet (can_create) can pass the class directly instead of repeating its name.
    """

    return resource_type if isinstance(resource_type, str) else resource_type.resource_type  # noqa
