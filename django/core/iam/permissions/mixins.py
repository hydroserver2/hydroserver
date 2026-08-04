import typing

from django.db.models import BooleanField, Case, Q, QuerySet, Value, When

from .registry import resolve_resource_type

if typing.TYPE_CHECKING:
    from ..models import Workspace


class ResourcePermissionMixin:
    """
    Adds the resource-permission API as methods on the principal, so callers
    write principal.can_view(resource) instead of can_view(resource, principal).

    Applied to User, ServiceAccount, and AnonymousPrincipal.
    """

    def can_create(
        self, resource_type: "str | type", workspace: "Workspace | None" = None
    ) -> bool:
        """
        Return True if this principal can create a resource of the given type in
        the workspace. The resource_type may be the resource_type string or the
        registered model class itself — there's no instance yet to derive it from.

        The workspace may be None for resource types that support creation outside
        any workspace (e.g., global vocabulary) — only superusers are granted
        permission in that case.
        """

        return self.has_permission(
            workspace,
            resource_type=resolve_resource_type(resource_type),
            permission_field="can_create",
        )

    def can_view(self, resource: object) -> bool:
        """
        Return True if this principal can view the given resource.

        Grants access to superusers unconditionally. For everyone else, checks
        whether the resource is publicly visible by traversing the model's
        privacy_chain — all nodes in the chain must have is_private=False. If not
        public, it falls back to checking workspace ownership and collaborator
        permissions.
        """

        if "can_view" in resource.__dict__:
            return getattr(resource, "can_view")

        if self.is_superuser_principal():
            return True

        chain = getattr(type(resource), "privacy_chain", [])
        if chain:
            for field_path in chain:
                obj = resource
                for part in field_path.split("__"):
                    obj = getattr(obj, part, None)
                    if obj is None:
                        break
                if obj is not False:
                    break
            else:
                return True

        workspace = self._resolve_workspace(
            resource, getattr(type(resource), "workspace_field", "workspace")
        )

        if workspace is None:
            return True

        return self.has_permission(
            workspace,
            resource_type=type(resource).resource_type,  # noqa
            permission_field="can_view",
        )

    def can_edit(self, resource: object) -> bool:
        """
        Return True if this principal can edit the given resource.

        Superusers are granted access without a workspace lookup. For all others,
        the resource's registered workspace_field is used to resolve the workspace
        before checking collaborator permissions.
        """

        if "can_edit" in resource.__dict__:
            return getattr(resource, "can_edit")

        if self.is_superuser_principal():
            return True

        workspace = self._resolve_workspace(
            resource, getattr(type(resource), "workspace_field", "workspace")
        )

        return workspace is not None and self.has_permission(
            workspace,
            resource_type=type(resource).resource_type,  # noqa
            permission_field="can_edit",
        )

    def can_delete(self, resource: object) -> bool:
        """
        Return True if this principal can delete the given resource.

        Superusers are granted access without a workspace lookup. For all others,
        the resource's registered workspace_field is used to resolve the workspace
        before checking collaborator permissions.
        """

        if "can_delete" in resource.__dict__:
            return getattr(resource, "can_delete")

        if self.is_superuser_principal():
            return True

        workspace = self._resolve_workspace(
            resource, getattr(type(resource), "workspace_field", "workspace")
        )

        return workspace is not None and self.has_permission(
            workspace,
            resource_type=type(resource).resource_type,  # noqa
            permission_field="can_delete",
        )

    def _permission_q(self, model: type, permission_field: str) -> Q:
        """
        Build the Q expression matching rows of the given model this principal
        holds permission_field on ("can_view"/"can_edit"/"can_delete"). Shared
        by filter_by_permission (used as a filter) and annotate_permissions
        (used as a Case/When condition), so the rule is defined once.

        Only "can_view" gets the public/privacy_chain and workspace-is-null
        bypasses — a global, workspace-less vocabulary item is viewable by
        everyone but not editable/deletable by anyone except a superuser,
        matching can_edit/can_delete's single-object behavior.
        """

        accessible_ids = self._accessible_workspace_ids(
            model.resource_type, permission_field  # noqa
        )

        workspace_field = getattr(model, "workspace_field", "workspace")

        if workspace_field is None:
            q = self._owner_q() | Q(pk__in=accessible_ids)
        else:
            q = self._owner_q(f"{workspace_field}__owner") | Q(
                **{f"{workspace_field}__in": accessible_ids}
            )
            if permission_field == "can_view":
                q |= Q(**{f"{workspace_field}__isnull": True})

        if permission_field == "can_view":
            chain = getattr(model, "privacy_chain", [])
            if chain:
                public_q = Q()
                for field in chain:
                    public_q &= Q(**{field: False})
                q |= public_q

        return q

    def filter_by_permission(self, queryset: QuerySet, permission_field: str) -> QuerySet:
        """Narrow queryset to rows this principal holds permission_field on."""

        if self.is_superuser_principal():
            return queryset

        return queryset.filter(self._permission_q(queryset.model, permission_field))

    def annotate_permissions(self, queryset: QuerySet) -> QuerySet:
        """Annotate queryset rows with can_view/can_edit/can_delete booleans for this principal."""

        if self.is_superuser_principal():
            return queryset.annotate(
                can_view=Value(True, output_field=BooleanField()),
                can_edit=Value(True, output_field=BooleanField()),
                can_delete=Value(True, output_field=BooleanField()),
            )

        def _case(permission_field: str) -> Case:
            return Case(
                When(
                    self._permission_q(queryset.model, permission_field),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            )

        return queryset.annotate(
            can_view=_case("can_view"),
            can_edit=_case("can_edit"),
            can_delete=_case("can_delete"),
        )

    def is_superuser_principal(self) -> bool:
        """Return True if this principal is a User with superuser status."""

        from ..models import User

        return isinstance(self, User) and self.is_superuser

    def has_permission(
        self,
        workspace: "Workspace | None",
        *,
        resource_type: str,
        permission_field: str,
    ) -> bool:
        """
        Return True if this principal has a specific permission on a workspace.

        Checks in order: superuser status, workspace ownership, then collaborator
        role permissions. The workspace may be None for resources that support
        being created outside any workspace (e.g., global vocabulary) — only
        superusers are granted permission in that case.
        """

        from ..models import User, Collaborator

        if self.is_superuser_principal():
            return True

        if workspace is None:
            return False

        if isinstance(self, User) and workspace.owner_id == self.id:
            return True

        collaborators = Collaborator.objects.filter(
            workspace=workspace,
            role__permissions__resource_type__in=(resource_type, "*"),
            **{f"role__permissions__{permission_field}": True},
        )

        return self._filter_by_principal(collaborators).exists()

    def _owner_q(self, field: str = "owner") -> Q:
        """
        Build a Q filter matching resources owned by this principal.

        Always returns an empty Q for ServiceAccount principals, since service
        accounts cannot own resources.
        """

        from ..models import User

        if isinstance(self, User):
            return Q(**{field: self})

        return Q(pk__in=[])

    def _filter_by_principal(self, queryset: QuerySet, *, field_prefix: str = "") -> QuerySet:
        """
        Narrow a queryset to rows belonging to this principal.

        The field_prefix is prepended to the user/service_account lookup, allowing
        this to be used on querysets where the principal is accessed through a
        related field (e.g., field_prefix="collaborator__" for a grant table).
        Returns no rows for an anonymous principal, rather than falling through to
        the service_account branch (service_account=None would otherwise match
        every user-owned row, since service_account is null there too).
        """

        from ..models import ServiceAccount, User

        if isinstance(self, User):
            return queryset.filter(**{f"{field_prefix}user": self})

        if isinstance(self, ServiceAccount):
            return queryset.filter(**{f"{field_prefix}service_account": self})

        return queryset.none()

    def _accessible_workspace_ids(self, resource_type: str, permission_field: str) -> QuerySet:
        """
        Return a flat queryset of workspace IDs where this principal holds a
        permission.

        Scopes to workspaces where the principal is a collaborator whose role
        grants the specified permission on the given resource type. Returned as a
        lazy values queryset suitable for use as a subquery.
        """

        from ..models import Collaborator

        collaborators = Collaborator.objects.filter(
            role__permissions__resource_type__in=(resource_type, "*"),
            **{f"role__permissions__{permission_field}": True},
        )

        return self._filter_by_principal(collaborators).values_list(
            "workspace_id", flat=True
        )

    @staticmethod
    def _resolve_workspace(
        resource: object, workspace_field: "str | None"
    ) -> "Workspace | None":
        """
        Traverse a `__`-delimited attribute path on a resource to find its
        workspace.

        Returns the resource itself when workspace_field is None, for the case
        where the resource being checked is the workspace. Returns None if any
        intermediate attribute in the chain is None.
        """

        from ..models import Workspace

        if workspace_field is None:
            return resource if isinstance(resource, Workspace) else None

        obj = resource
        for field in workspace_field.split("__"):
            obj = getattr(obj, field)
            if obj is None:
                return None

        return obj
