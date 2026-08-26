import uuid
import uuid
from typing import Literal

from pydantic import Field, ConfigDict, validate_call
from django.db import transaction
from django.db.models.query import QuerySet
from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchVector, SearchQuery

from core.types import Unset
from core.iam.models import ServiceAccount, Workspace
from core.iam.permissions.anonymous import AnonymousPrincipal
from core.service import ServiceUtils
from core.sta.models import MonitoringSite
from processing.products.models import RatingCurve, RatingCurvePoint


User = get_user_model()


class RatingCurveService(ServiceUtils):

    order_by_fields = {"id", "name", "monitoring_site_id", "monitoring_site__name", "monitoring_site__workspace_id", "monitoring_site__workspace__name"}

    @staticmethod
    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get(
        rating_curve: uuid.UUID | RatingCurve,
        action: Literal["view", "edit", "delete"] = "view",
        principal: User | ServiceAccount | AnonymousPrincipal | Unset = Unset,
    ) -> RatingCurve:
        """Get a rating curve."""

        if isinstance(rating_curve, uuid.UUID):
            try:
                queryset = RatingCurve.objects.select_related(
                    "monitoring_site__workspace"
                ).prefetch_related(
                    "points",
                    "monitoring_site__monitoring_site_linked_resources",
                ).filter(pk=rating_curve)
                if principal is not Unset:
                    queryset = principal.annotate_permissions(queryset)
                rating_curve = queryset.get()
            except RatingCurve.DoesNotExist:
                raise LookupError(f"Rating curve with ID {str(rating_curve)} does not exist.")

        if principal is not Unset:
            if not principal.can_view(rating_curve):
                raise LookupError(f"Rating curve with ID {str(rating_curve.id)} does not exist.")

            if action != "view" and not getattr(principal, f"can_{action}")(rating_curve):
                raise PermissionError(f"You do not have permission to {action} this rating curve.")

        return rating_curve

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get_collection(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        page: int = Field(gt=0, default=1),
        page_size: int = Field(gt=0, default=100),
        order_by: list[str] = Field(default_factory=list),
        search_term: str | Unset = Unset,
        monitoring_site: list[uuid.UUID | MonitoringSite] | Unset = Unset,
        workspace: list[uuid.UUID | Workspace] | Unset = Unset,
    ) -> tuple[int, QuerySet[RatingCurve]]:
        """Return a collection of rating curves."""

        queryset = RatingCurve.objects

        if search_term is not Unset:
            search_vector = SearchVector("name", "description", "monitoring_site__name")
            queryset = queryset.annotate(search=search_vector).filter(search=SearchQuery(search_term))

        if monitoring_site is not Unset:
            queryset = queryset.filter(monitoring_site__in=[getattr(t, "pk", t) for t in monitoring_site])

        if workspace is not Unset:
            queryset = queryset.filter(monitoring_site__workspace__in=[getattr(ws, "pk", ws) for ws in workspace])

        if not all(term.lstrip("-") in self.order_by_fields for term in order_by):
            raise ValueError(f"Invalid order_by field(s): {order_by}")

        queryset = queryset.order_by(*order_by, "-id")
        queryset = queryset.select_related("monitoring_site__workspace").prefetch_related(
            "points",
            "monitoring_site__monitoring_site_linked_resources",
        )
        queryset = principal.filter_by_permission(queryset, "can_view").distinct()

        count = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset:offset + page_size]

        return count, queryset

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def create(
        self,
        principal: User | ServiceAccount | AnonymousPrincipal,
        monitoring_site: uuid.UUID | MonitoringSite,
        name: str,
        fitting_method: Literal["linear", "power_law", "polynomial"],
        points: list[tuple] = Field(default_factory=list),
        description: str | None = None,
        uid: uuid.UUID = Field(default_factory=uuid.uuid7),
    ) -> RatingCurve:
        """Create a rating curve."""

        if isinstance(monitoring_site, uuid.UUID):
            try:
                monitoring_site = MonitoringSite.objects.select_related("workspace").get(pk=monitoring_site)
            except MonitoringSite.DoesNotExist:
                raise LookupError("MonitoringSite does not exist.")

        if not principal.can_create("RatingCurve", workspace=monitoring_site.workspace):
            raise PermissionError("You do not have permission to create this rating curve.")

        rating_curve = RatingCurve.objects.create(
            pk=uid,
            monitoring_site=monitoring_site,
            name=name,
            description=description,
            fitting_method=fitting_method,
        )

        if points:
            self.apply_points(rating_curve=rating_curve, points=points)

        return self.get(rating_curve.pk)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def update(
        self,
        rating_curve: uuid.UUID | RatingCurve,
        principal: User | ServiceAccount | AnonymousPrincipal,
        name: str | Unset = Unset,
        description: str | None | Unset = Unset,
        fitting_method: Literal["linear", "power_law", "polynomial"] | Unset = Unset,
        points: list[tuple] | Unset = Unset,
    ) -> RatingCurve:
        """Update a rating curve."""

        rating_curve = self.get(rating_curve=rating_curve, action="edit", principal=principal)

        editable_fields = {"name": name, "description": description, "fitting_method": fitting_method}
        for field, value in editable_fields.items():
            if value is not Unset:
                setattr(rating_curve, field, value)

        rating_curve.save()

        if points is not Unset:
            self.apply_points(rating_curve=rating_curve, points=points)

        return self.get(rating_curve.pk)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def delete(
        self,
        rating_curve: uuid.UUID | RatingCurve,
        principal: User | ServiceAccount | AnonymousPrincipal,
    ) -> None:
        """Delete a rating curve."""

        rating_curve = self.get(rating_curve=rating_curve, action="delete", principal=principal)
        rating_curve.delete()

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def apply_points(
        self,
        rating_curve: uuid.UUID | RatingCurve,
        points: list[tuple],
    ) -> None:
        """Replace all points on a rating curve."""

        rating_curve = self.get(rating_curve)

        input_values = [pt[0] for pt in points]
        if len(set(input_values)) != len(input_values):
            raise ValueError("Duplicate input_value in points.")

        rating_curve.points.all().delete()

        RatingCurvePoint.objects.bulk_create([
            RatingCurvePoint(
                rating_curve=rating_curve,
                input_value=pt[0],
                output_value=pt[1],
            )
            for pt in points
        ])
