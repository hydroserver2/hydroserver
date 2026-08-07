import uuid
from typing import Optional, Literal, get_args
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.db.utils import IntegrityError
from psycopg.errors import UniqueViolation
from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import ResultQualifier
from interfaces.api.schemas import (
    ResultQualifierSummaryResponse,
    ResultQualifierDetailResponse,
    ResultQualifierPostBody,
    ResultQualifierPatchBody,
)
from interfaces.api.schemas.sta.result_qualifier import (
    ResultQualifierFields,
    ResultQualifierOrderByFields,
)
from core.service import ServiceUtils

User = get_user_model()


class ResultQualifierService(ServiceUtils):
    def get_result_qualifier_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        expand_related: Optional[bool] = None,
    ):
        queryset = ResultQualifier.objects.filter(pk=uid)
        if expand_related:
            queryset = self.select_expanded_fields(queryset)
        queryset = principal.annotate_permissions(queryset)

        try:
            result_qualifier = queryset.get()
        except ResultQualifier.DoesNotExist:
            raise HttpError(404, "Result qualifier does not exist")

        if not principal.can_view(result_qualifier):
            raise HttpError(404, "Result qualifier does not exist")

        if action != "view" and not getattr(principal, f"can_{action}")(
            result_qualifier
        ):
            raise HttpError(
                403, f"You do not have permission to {action} this result qualifier"
            )

        return result_qualifier

    @staticmethod
    def select_expanded_fields(queryset: QuerySet) -> QuerySet:
        return queryset.select_related("workspace")

    def list(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_by: Optional[list[str]] = None,
        filtering: Optional[dict] = None,
        expand_related: Optional[bool] = None,
    ):
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

        if order_by:
            queryset = self.apply_ordering(
                queryset,
                order_by,
                list(get_args(ResultQualifierOrderByFields)),
            )
        else:
            queryset = queryset.order_by("id")

        if expand_related:
            queryset = self.select_expanded_fields(queryset)

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()

        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return [
            (
                ResultQualifierDetailResponse.model_validate(result_qualifier)
                if expand_related
                else ResultQualifierSummaryResponse.model_validate(result_qualifier)
            )
            for result_qualifier in queryset.all()
        ]

    def get(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        expand_related: Optional[bool] = None,
    ):
        result_qualifier = self.get_result_qualifier_for_action(
            principal=principal, uid=uid, action="view", expand_related=expand_related
        )

        return (
            ResultQualifierDetailResponse.model_validate(result_qualifier)
            if expand_related
            else ResultQualifierSummaryResponse.model_validate(result_qualifier)
        )

    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: ResultQualifierPostBody,
        expand_related: Optional[bool] = None,
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
            raise HttpError(
                403, "You do not have permission to create this result qualifier"
            )

        try:
            result_qualifier = ResultQualifier.objects.create(
                pk=data.id,
                workspace=workspace,
                **data.dict(include=set(ResultQualifierFields.model_fields.keys())),
            )
        except (
            IntegrityError,
            UniqueViolation,
        ):
            raise HttpError(409, "A result qualifier with this ID or code already exists")

        return self.get(
            principal=principal, uid=result_qualifier.id, expand_related=expand_related
        )

    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data: ResultQualifierPatchBody,
        expand_related: Optional[bool] = None,
    ):
        result_qualifier = self.get_result_qualifier_for_action(
            principal=principal, uid=uid, action="edit"
        )
        result_qualifier_data = data.dict(
            include=set(ResultQualifierFields.model_fields.keys()), exclude_unset=True
        )

        for field, value in result_qualifier_data.items():
            setattr(result_qualifier, field, value)

        try:
            result_qualifier.save()
        except (
            IntegrityError,
            UniqueViolation,
        ):
            raise HttpError(409, "A result qualifier with this code already exists")

        return self.get(
            principal=principal, uid=result_qualifier.id, expand_related=expand_related
        )

    def delete(self, principal: User | ServiceAccount | AnonymousPrincipal, uid: uuid.UUID):
        result_qualifier = self.get_result_qualifier_for_action(
            principal=principal, uid=uid, action="delete"
        )
        result_qualifier.delete()

        return "Result qualifier deleted"
