import uuid

from typing import Optional, Literal, get_args
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from psycopg.errors import UniqueViolation

from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import ResultQualifier
from interfaces.api.service import APIService
from interfaces.api.http.errors import ConflictError, NotFoundError, PermissionDeniedError
from interfaces.api.schemas import (
    ResultQualifierResponse,
    ResultQualifierPostBody,
    ResultQualifierPatchBody,
)
from interfaces.api.schemas.sta.result_qualifier import (
    ResultQualifierFields,
    ResultQualifierSortByFields,
    RESULT_QUALIFIER_INCLUDE_RELATIONS,
)

User = get_user_model()


class ResultQualifierAPIService(APIService):
    INCLUDE_RELATIONS = RESULT_QUALIFIER_INCLUDE_RELATIONS

    def get_result_qualifier_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        select_related: Optional[list[str]] = None,
    ):
        queryset = ResultQualifier.objects.filter(pk=uid)
        if select_related:
            queryset = queryset.select_related(*select_related)
        queryset = principal.annotate_permissions(queryset)

        try:
            result_qualifier = queryset.get()
        except ResultQualifier.DoesNotExist:
            raise NotFoundError("Result qualifier does not exist")

        if not principal.can_view(result_qualifier):
            raise NotFoundError("Result qualifier does not exist")

        if action != "view" and not getattr(principal, f"can_{action}")(
            result_qualifier
        ):
            raise PermissionDeniedError(
                f"You do not have permission to {action} this result qualifier"
            )

        return result_qualifier

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        sortby: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        include: Optional[list[str]] = None,
    ):
        requested_includes = self.resolve_include_set(include)
        queryset = ResultQualifier.objects

        for field in ["workspace_id"]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])
        for field in [
            "observations__datastream_id",
            "observations__datastream__monitoring_site_id",
        ]:
            if field in filtering and not all(
                value is None for value in filtering[field]
            ):
                queryset = ResultQualifier.objects.none()

        queryset, has_search = self.apply_search(queryset, filtering.get("q"))
        queryset = self.apply_sorting(
            queryset,
            sortby,
            list(get_args(ResultQualifierSortByFields)),
            rank=has_search,
        )

        if requested_includes:
            select_paths = [
                self.INCLUDE_RELATIONS[name]["path"] for name in requested_includes
            ]
            queryset = queryset.select_related(*select_paths)

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()
        queryset, meta = self.apply_pagination(queryset, offset, limit)
        result_qualifiers = list(queryset.all())

        return {
            "data": [
                ResultQualifierResponse.model_validate(result_qualifier)
                for result_qualifier in result_qualifiers
            ],
            "meta": meta,
            "included": self.resolve_includes(
                result_qualifiers, requested_includes, self.INCLUDE_RELATIONS
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
        result_qualifier = self.get_result_qualifier_for_action(
            principal=principal, uid=uid, action="view", select_related=select_paths
        )

        return {
            "data": ResultQualifierResponse.model_validate(result_qualifier),
            "included": self.resolve_includes(
                [result_qualifier], requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: ResultQualifierPostBody,
    ):
        workspace, _ = (
            self.get_workspace(principal=principal, workspace_id=data.workspace_id)
            if data.workspace_id
            else (
                None,
                None,
            )
        )

        if not principal.can_create("ResultQualifier", workspace=workspace):
            raise PermissionDeniedError(
                "You do not have permission to create this result qualifier"
            )

        result_qualifier = ResultQualifier(
            pk=data.id,
            workspace=workspace,
            **data.dict(include=set(ResultQualifierFields.model_fields.keys())),
        )
        result_qualifier.full_clean()

        try:
            result_qualifier.save()
        except (
            IntegrityError,
            UniqueViolation,
        ):
            raise ConflictError("A result qualifier with this ID or code already exists")

        return {"id": result_qualifier.pk}

    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data: ResultQualifierPatchBody,
    ):
        result_qualifier = self.get_result_qualifier_for_action(
            principal=principal, uid=uid, action="edit"
        )
        result_qualifier_data = data.dict(
            include=set(ResultQualifierFields.model_fields.keys()), exclude_unset=True
        )

        for field, value in result_qualifier_data.items():
            setattr(result_qualifier, field, value)

        result_qualifier.full_clean()

        try:
            result_qualifier.save()
        except (
            IntegrityError,
            UniqueViolation,
        ):
            raise ConflictError("A result qualifier with this code already exists")

    def delete(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID):
        result_qualifier = self.get_result_qualifier_for_action(
            principal=principal, uid=uid, action="delete"
        )
        result_qualifier.delete()

        return "Result qualifier deleted"
