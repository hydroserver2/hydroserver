import ast
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
from processing.products.models import Expression, ExpressionSegment


User = get_user_model()


class ExpressionService(ServiceUtils):

    order_by_fields = {"id", "name", "thing_id", "thing__name", "thing__workspace_id", "thing__workspace__name"}

    @staticmethod
    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get(
        expression: uuid.UUID | Expression,
        action: Literal["view", "edit", "delete"] = "view",
        principal: User | APIKey | None | Unset = Unset,
    ) -> Expression:
        """
        Get an expression.
        """

        if isinstance(expression, uuid.UUID):
            try:
                expression = Expression.objects.select_related(
                    "thing__workspace"
                ).prefetch_related(
                    "segments",
                    "thing__locations", "thing__thing_tags", "thing__thing_file_attachments",
                ).get(pk=expression)
            except Expression.DoesNotExist:
                raise LookupError(f"Expression with ID {str(expression)} does not exist.")

        if principal is not Unset:
            permissions = expression.get_principal_permissions(principal=principal)

            if "view" not in permissions:
                raise LookupError(f"Expression with ID {str(expression.id)} does not exist.")

            if action not in permissions:
                raise PermissionError(f"You do not have permission to {action} this expression.")

        return expression

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
    ) -> tuple[int, QuerySet[Expression]]:
        """
        Return a collection of expressions.
        """

        queryset = Expression.objects

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
            "segments",
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
        segments: list[dict] = Field(default_factory=list),
        uid: uuid.UUID = Field(default_factory=uuid6.uuid7),
        description: str | None = None,
        breakpoint_variable: str | None = None,
    ) -> Expression:
        """
        Create an expression with its segments.
        """

        if isinstance(thing, uuid.UUID):
            try:
                thing = Thing.objects.select_related("workspace").get(pk=thing)
            except Thing.DoesNotExist:
                raise HttpError(404, "Thing does not exist.")

        if not Expression.can_principal_create(principal=principal, workspace=thing.workspace):
            raise PermissionError("You do not have permission to create this expression.")

        expression = Expression.objects.create(
            pk=uid,
            thing=thing,
            name=name,
            description=description,
            breakpoint_variable=breakpoint_variable,
        )

        self.apply_expression(expression=expression, segments=segments)

        return self.get(expression.pk)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def update(
        self,
        expression: uuid.UUID | Expression,
        principal: User | APIKey | None,
        name: str | Unset = Unset,
        description: str | None | Unset = Unset,
        breakpoint_variable: str | None | Unset = Unset,
        segments: list[dict] | Unset = Unset,
    ) -> Expression:
        """
        Update an expression. Providing segments replaces them entirely.
        """

        expression = self.get(expression=expression, action="edit", principal=principal)

        if segments is not Unset:
            self.apply_expression(expression=expression, segments=segments)

        editable_fields = {"name": name, "description": description, "breakpoint_variable": breakpoint_variable}
        for field, value in editable_fields.items():
            if value is not Unset:
                setattr(expression, field, value)

        expression.save()

        return self.get(expression.pk)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def delete(
        self,
        expression: uuid.UUID | Expression,
        principal: User | APIKey | None,
    ) -> None:
        """
        Delete an expression and all its segments.
        """

        expression = self.get(expression=expression, action="delete", principal=principal)
        expression.delete()

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def apply_expression(
        self,
        expression: uuid.UUID | Expression,
        segments: list[dict] | Unset = Unset,
    ) -> None:
        """
        Replace segments on an expression.

        Providing segments deletes all existing segments and creates new ones.
        Omitting segments (Unset) leaves them unchanged.

        Expected segment dict keys: lower_bound, upper_bound, formula
        """

        expression = self.get(expression)

        if segments is not Unset:
            self._validate_segments(segments)
            expression.segments.all().delete()
            ExpressionSegment.objects.bulk_create([
                ExpressionSegment(
                    expression=expression,
                    lower_bound=seg.get("lower_bound"),
                    upper_bound=seg.get("upper_bound"),
                    formula=seg.get("formula"),
                )
                for seg in segments
            ])

    @staticmethod
    def _validate_formula(formula: str) -> None:
        _ALLOWED_AST = (
            ast.Expression,
            ast.BinOp,
            ast.UnaryOp,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.UAdd,
            ast.USub,
            ast.Name,
            ast.Load,
            ast.Constant,
        )
        try:
            tree = ast.parse(formula, mode="eval")
        except SyntaxError as e:
            raise ValueError(f"Invalid formula syntax: {e}")
        for node in ast.walk(tree):
            if not isinstance(node, _ALLOWED_AST):
                raise ValueError(
                    f"Formula contains unsupported operation: {type(node).__name__}."
                )

    @staticmethod
    def _validate_segments(segments: list[dict]) -> None:
        for seg in segments:
            lb = seg.get("lower_bound")
            ub = seg.get("upper_bound")
            if lb is not None and ub is not None and lb >= ub:
                raise ValueError(
                    f"Segment lower_bound ({lb}) must be less than upper_bound ({ub})."
                )
            if seg.get("formula") is not None:
                ExpressionService._validate_formula(seg["formula"])

        intervals = sorted(
            [(seg.get("lower_bound") or float("-inf"), seg.get("upper_bound") or float("inf")) for seg in segments],
            key=lambda s: s[0],
        )
        for i in range(len(intervals) - 1):
            if intervals[i][1] > intervals[i + 1][0]:
                raise ValueError(
                    f"Segments overlap: [{intervals[i][0]}, {intervals[i][1]}] "
                    f"and [{intervals[i + 1][0]}, {intervals[i + 1][1]}]."
                )
