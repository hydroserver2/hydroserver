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
from interfaces.api.schemas.sta.vocabulary import (
    VocabularyFields,
    VocabularySortByFields,
)

User = get_user_model()


class VocabularyAPIService(APIService):
    model: Type[Model]
    resource_type_name: str
    response_schema: type

    def get_term_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
    ):
        queryset = principal.annotate_permissions(self.model.objects.filter(pk=uid))

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
    ):
        filtering = filtering or {}
        queryset = self.model.objects

        queryset, has_search = self.apply_search(queryset, filtering.get("q"))
        queryset = self.apply_sorting(
            queryset,
            sortby,
            list(get_args(VocabularySortByFields)),
            rank=has_search,
        )

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()
        queryset, meta = self.apply_pagination(queryset, offset, limit)
        terms = list(queryset.all())

        return {
            "data": [self.response_schema.model_validate(term) for term in terms],
            "meta": meta,
        }

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
    ):
        term = self.get_term_for_action(principal=principal, uid=uid, action="view")

        return {"data": self.response_schema.model_validate(term)}

    def create(self, principal: User | ServiceAccount | AnonymousPrincipal, data):
        if not principal.can_create(self.resource_type_name):
            raise PermissionDeniedError(
                f"You do not have permission to create this {self.resource_type_name.lower()}"
            )

        term = self.model(
            pk=data.id,
            **data.dict(include=set(VocabularyFields.model_fields.keys())),
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
            include=set(VocabularyFields.model_fields.keys()),
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
