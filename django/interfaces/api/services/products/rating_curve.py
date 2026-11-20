import uuid

from typing import Literal, Optional, get_args
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from core.iam.models import ServiceAccount
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.sta.models import MonitoringSite
from core.types import Unset
from processing.products.models import RatingCurve, RatingCurvePoint
from interfaces.api.http.errors import ConflictError, NotFoundError, PermissionDeniedError
from interfaces.api.service import APIService
from interfaces.api.schemas.products.rating_curve import (
    RatingCurveFields,
    RatingCurveSortByFields,
    RatingCurvePatchBody,
    RatingCurvePostBody,
    RatingCurveResponse,
    RATING_CURVE_INCLUDE_RELATIONS,
)

User = get_user_model()

RATING_CURVE_SORTBY_ALIASES = {
    "monitoringSiteName": "monitoring_site__name",
    "workspaceId": "monitoring_site__workspace_id",
    "workspaceName": "monitoring_site__workspace__name",
}


class RatingCurveAPIService(APIService):
    INCLUDE_RELATIONS = RATING_CURVE_INCLUDE_RELATIONS

    def get_rating_curve_for_action(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        action: Literal["view", "edit", "delete"],
        select_related: Optional[list[str]] = None,
        prefetch_related: Optional[list[str]] = None,
    ):
        queryset = RatingCurve.objects.filter(pk=uid)
        if select_related:
            queryset = queryset.select_related(*select_related)
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)

        queryset = principal.annotate_permissions(queryset)

        try:
            rating_curve = queryset.get()
        except RatingCurve.DoesNotExist:
            raise NotFoundError(f"Rating curve with ID {uid} does not exist.")

        if not principal.can_view(rating_curve):
            raise NotFoundError(f"Rating curve with ID {uid} does not exist.")

        if action != "view" and not getattr(principal, f"can_{action}")(rating_curve):
            raise PermissionDeniedError(
                f"You do not have permission to {action} this rating curve."
            )

        return rating_curve

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
        queryset = RatingCurve.objects

        for field in ["monitoring_site_id", "monitoring_site__workspace_id"]:
            if field in filtering:
                queryset = self.apply_filters(queryset, field, filtering[field])

        queryset, has_search = self.apply_search(queryset, filtering.get("q"))
        queryset = self.apply_sorting(
            queryset,
            sortby,
            list(get_args(RatingCurveSortByFields)),
            field_aliases=RATING_CURVE_SORTBY_ALIASES,
            rank=has_search,
        )

        queryset = queryset.prefetch_related("points")

        if requested_includes:
            select_paths = [
                self.INCLUDE_RELATIONS[name]["path"] for name in requested_includes
            ]
            queryset = queryset.select_related(*select_paths)
            if "monitoringSite" in requested_includes:
                queryset = queryset.prefetch_related(
                    "monitoring_site__monitoring_site_linked_resources"
                )

        queryset = principal.filter_by_permission(queryset, "can_view").distinct()
        queryset, meta = self.apply_pagination(queryset, offset, limit)
        rating_curves = list(queryset.all())

        return {
            "data": [
                RatingCurveResponse.model_validate(rc) for rc in rating_curves
            ],
            "meta": meta,
            "included": self.resolve_includes(
                rating_curves, requested_includes, self.INCLUDE_RELATIONS
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
        prefetch_paths = ["points"]

        if "monitoringSite" in requested_includes:
            prefetch_paths.append("monitoring_site__monitoring_site_linked_resources")

        rating_curve = self.get_rating_curve_for_action(
            principal=principal,
            uid=uid,
            action="view",
            select_related=select_paths,
            prefetch_related=prefetch_paths,
        )

        return {
            "data": RatingCurveResponse.model_validate(rating_curve),
            "included": self.resolve_includes(
                [rating_curve], requested_includes, self.INCLUDE_RELATIONS
            ),
        }

    @transaction.atomic
    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        data: RatingCurvePostBody,
    ):
        try:
            monitoring_site = MonitoringSite.objects.select_related("workspace").get(
                pk=data.monitoring_site_id
            )
        except MonitoringSite.DoesNotExist:
            raise NotFoundError("MonitoringSite does not exist.")

        if not principal.can_create("RatingCurve", workspace=monitoring_site.workspace):
            raise PermissionDeniedError(
                "You do not have permission to create this rating curve."
            )

        rating_curve = RatingCurve(
            pk=data.id,
            monitoring_site=monitoring_site,
            **data.dict(include=set(RatingCurveFields.model_fields.keys()) - {"points"}),
        )
        rating_curve.full_clean()

        try:
            rating_curve.save()
        except IntegrityError:
            raise ConflictError(
                "The operation could not be completed due to a resource conflict."
            )

        if data.points:
            self.apply_points(rating_curve=rating_curve, points=data.points)

        return {"id": rating_curve.pk}

    @transaction.atomic
    def update(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
        data: RatingCurvePatchBody,
    ):
        rating_curve = self.get_rating_curve_for_action(
            principal=principal, uid=uid, action="edit"
        )

        rating_curve_data = data.dict(
            include=set(RatingCurveFields.model_fields.keys()) - {"points"},
            exclude_unset=True,
        )
        for field, value in rating_curve_data.items():
            setattr(rating_curve, field, value)

        rating_curve.full_clean()
        rating_curve.save()

        if data.points is not Unset:
            self.apply_points(rating_curve=rating_curve, points=data.points)

    def delete(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        uid: uuid.UUID,
    ):
        rating_curve = self.get_rating_curve_for_action(
            principal=principal, uid=uid, action="delete"
        )
        rating_curve.delete()

    @staticmethod
    def apply_points(rating_curve: RatingCurve, points: list[tuple]) -> None:
        rating_curve.points.all().delete()

        try:
            RatingCurvePoint.objects.bulk_create([
                RatingCurvePoint(
                    rating_curve=rating_curve,
                    input_value=pt[0],
                    output_value=pt[1],
                )
                for pt in points
            ])
        except IntegrityError:
            raise ConflictError("A point with this input_value already exists on this rating curve.")
