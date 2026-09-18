import uuid

from typing import Optional, Literal, Type, get_args
from django.db.models import Model
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from psycopg.errors import UniqueViolation

from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from interfaces.api.service import APIService
from interfaces.api.http.errors import ConflictError, NotFoundError, PermissionDeniedError
from interfaces.api.schemas.sta.controlled_vocabulary import (
    ControlledVocabularyFields,
    ControlledVocabularySortByFields,
    CONTROLLED_VOCABULARY_INCLUDE_RELATIONS,
)

User = get_user_model()


class ControlledVocabularyAPIService(APIService):
    model: Type[Model]
    resource_type_name: str
    response_schema: type
    INCLUDE_RELATIONS = CONTROLLED_VOCABULARY_INCLUDE_RELATIONS

    def get_term_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        select_related: Optional[list[str]] = None,
    ):
        queryset = self.model.objects.filter(pk=uid)
        if select_related:
            queryset = queryset.select_related(*select_related)
        queryset = principal.annotate_permissions(queryset)

        try:
            term = queryset.get()
        except self.model.DoesNotExist:
            raise NotFoundError(f"{self.resource_type_name} does not exist")

        if not principal.can_view(term):
            raise NotFoundError(f"{self.resource_type_name} does not exist")

        if action != "view" and not getattr(principal, f"can_{action}")(term):
            raise PermissionDeniedError(
                f"You do not have permission to {action} this {self.resource_type_name.lower()}"
            )

        return term

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        sortby: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        include: Optional[list[str]] = None,
    ):
        filtering = filtering or {}
        requested_includes = self.resolve_include_set(include)
        queryset = self.model.objects

        for field in ["workspace_id", "is_active"]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        queryset, has_search = self.apply_search(queryset, filtering.get("q"))
        queryset = self.apply_sorting(
            queryset,
            sortby,
            list(get_args(ControlledVocabularySortByFields)),
            rank=has_search,
        )

        if requested_includes:
            select_paths = [
                self.INCLUDE_RELATIONS[name]["path"] for name in requested_includes
            ]
            queryset = queryset.select_related(*select_paths)

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()
        queryset, meta = self.apply_pagination(queryset, offset, limit)
        terms = list(queryset.all())

        return {
            "data": [self.response_schema.model_validate(term) for term in terms],
            "meta": meta,
            "included": self.resolve_includes(
                terms, requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        select_paths = [
            self.INCLUDE_RELATIONS[name]["path"] for name in requested_includes
        ]
        term = self.get_term_for_action(
            principal=principal, uid=uid, action="view", select_related=select_paths
        )

        return {
            "data": self.response_schema.model_validate(term),
            "included": self.resolve_includes(
                [term], requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    def create(self, principal: User | ServiceAccount | AnonymousPrincipal, data):
        workspace, _ = (
            self.get_workspace(principal=principal, workspace_id=data.workspace_id)
            if data.workspace_id
            else (None, None)
        )

        if not principal.can_create(self.resource_type_name, workspace=workspace):
            raise PermissionDeniedError(
                f"You do not have permission to create this {self.resource_type_name.lower()}"
            )

        term = self.model(
            pk=data.id,
            workspace=workspace,
            **data.dict(include=set(ControlledVocabularyFields.model_fields.keys())),
        )
        term.full_clean()

        try:
            term.save()
        except (IntegrityError, UniqueViolation):
            raise ConflictError(
                f"A {self.resource_type_name.lower()} with this ID or name already exists"
            )

        return {"id": term.pk}

    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data,
    ):
        term = self.get_term_for_action(principal=principal, uid=uid, action="edit")
        term_data = data.dict(
            include=set(ControlledVocabularyFields.model_fields.keys()),
            exclude_unset=True,
        )

        for field, value in term_data.items():
            setattr(term, field, value)

        term.full_clean()

        try:
            term.save()
        except (IntegrityError, UniqueViolation):
            raise ConflictError(
                f"A {self.resource_type_name.lower()} with this name already exists"
            )

    def delete(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID):
        term = self.get_term_for_action(principal=principal, uid=uid, action="delete")
        term.delete()

        return f"{self.resource_type_name} deleted"
