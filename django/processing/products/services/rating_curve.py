import uuid
import uuid6
from typing import Literal

from pydantic import Field, ConfigDict, validate_call
from ninja.errors import HttpError
from django.db import transaction
from django.db.models.query import QuerySet
from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchVector, SearchQuery

from core.types import Unset
from core.iam.models import APIKey, Workspace
from core.service import ServiceUtils
from core.sta.models import Thing
from processing.products.models import RatingCurve, RatingCurvePoint


User = get_user_model()


class RatingCurveService(ServiceUtils):

    order_by_fields = {"id", "name", "thing_id", "thing__name", "thing__workspace_id", "thing__workspace__name"}

    @staticmethod
    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get(
        rating_curve: uuid.UUID | RatingCurve,
        action: Literal["view", "edit", "delete"] = "view",
        principal: User | APIKey | None | Unset = Unset,
    ) -> RatingCurve:
        """Get a rating curve."""

        if isinstance(rating_curve, uuid.UUID):
            try:
                rating_curve = RatingCurve.objects.select_related(
                    "thing__workspace"
                ).prefetch_related(
                    "points",
                    "thing__locations", "thing__thing_tags", "thing__thing_file_attachments",
                ).get(pk=rating_curve)
            except RatingCurve.DoesNotExist:
                raise LookupError(f"Rating curve with ID {str(rating_curve)} does not exist.")

        if principal is not Unset:
            permissions = rating_curve.get_principal_permissions(principal=principal)

            if "view" not in permissions:
                raise LookupError(f"Rating curve with ID {str(rating_curve.id)} does not exist.")

            if action not in permissions:
                raise PermissionError(f"You do not have permission to {action} this rating curve.")

        return rating_curve

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get_collection(
        self,
        principal: User | APIKey | None = None,
        page: int = Field(gt=0, default=1),
        page_size: int = Field(gt=0, default=100),
        order_by: list[str] = Field(default_factory=list),
        search_term: str | Unset = Unset,
        thing: list[uuid.UUID | Thing] | Unset = Unset,
        workspace: list[uuid.UUID | Workspace] | Unset = Unset,
    ) -> tuple[int, QuerySet[RatingCurve]]:
        """Return a collection of rating curves."""

        queryset = RatingCurve.objects

        if search_term is not Unset:
            search_vector = SearchVector("name", "description", "thing__name")
            queryset = queryset.annotate(search=search_vector).filter(search=SearchQuery(search_term))

        if thing is not Unset:
            queryset = queryset.filter(thing__in=[getattr(t, "pk", t) for t in thing])

        if workspace is not Unset:
            queryset = queryset.filter(thing__workspace__in=workspace)

        if not all(term.lstrip("-") in self.order_by_fields for term in order_by):
            raise ValueError(f"Invalid order_by field(s): {order_by}")

        queryset = queryset.order_by(*order_by, "-id")
        queryset = queryset.select_related("thing__workspace").prefetch_related(
            "points",
            "thing__locations", "thing__thing_tags", "thing__thing_file_attachments",
        )
        queryset = queryset.visible(principal=principal).distinct()

        count = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset:offset + page_size]

        return count, queryset

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def create(
        self,
        principal: User | APIKey | None,
        thing: uuid.UUID | Thing,
        name: str,
        fitting_method: Literal["linear", "power_law", "polynomial", "spline"],
        points: list[tuple] = Field(default_factory=list),
        uid: uuid.UUID = Field(default_factory=uuid6.uuid7),
        description: str | None = None,
    ) -> RatingCurve:
        """Create a rating curve with its points."""

        if isinstance(thing, uuid.UUID):
            try:
                thing = Thing.objects.select_related("workspace").get(pk=thing)
            except Thing.DoesNotExist:
                raise HttpError(404, "Thing does not exist.")

        if not RatingCurve.can_principal_create(principal=principal, workspace=thing.workspace):
            raise PermissionError("You do not have permission to create this rating curve.")

        rating_curve = RatingCurve.objects.create(
            pk=uid,
            thing=thing,
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
        principal: User | APIKey | None,
        name: str | Unset = Unset,
        description: str | None | Unset = Unset,
        fitting_method: Literal["linear", "power_law", "polynomial", "spline"] | Unset = Unset,
        points: list[tuple] | Unset = Unset,
    ) -> RatingCurve:
        """Update a rating curve. Providing points replaces them entirely."""

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
        principal: User | APIKey | None,
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

        self._validate_points(points)
        rating_curve.points.all().delete()
        RatingCurvePoint.objects.bulk_create([
            RatingCurvePoint(
                rating_curve=rating_curve,
                input_value=pt[0],
                output_value=pt[1] if len(pt) > 1 else None,
            )
            for pt in points
        ])

    @staticmethod
    def _validate_points(points: list[tuple]) -> None:
        seen = set()
        for pt in points:
            v = pt[0]
            if v in seen:
                raise ValueError(f"Duplicate input_value {v} in points.")
            seen.add(v)
