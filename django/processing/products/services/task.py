import ast
import uuid
import uuid6
from datetime import datetime
from typing import Optional, Union, Literal

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
from processing.orchestration.services import TaskService
from processing.products.models import (
    DataProductTask, DataProductOutputMapping, DataProductInputMapping,
    Expression
)


User = get_user_model()

CELERY_TASK_NAME = "processing.products.tasks.run_data_product_task"


class DataProductTaskService(TaskService[DataProductTask], ServiceUtils):

    task_model = DataProductTask

    order_by_fields = {
        "id", "name", "thing_id", "thing__name",
        "thing__workspace_id", "thing__workspace__name",
        "latest_run_status", "latest_run_started_at", "latest_run_finished_at",
    }

    def get(
        self,
        task: Union[uuid.UUID, DataProductTask],
        action: Literal["view", "edit", "delete"] = "view",
        principal: User | APIKey | None | Unset = Unset,
    ) -> DataProductTask:
        """
        Get a data product task.
        """

        task = super().get(task=task, action=action, principal=principal)

        if isinstance(task.pk, uuid.UUID):
            task = (
                self.annotate_latest_run(self.task_model.objects)
                .select_related("thing__workspace", "periodic_task__crontab", "periodic_task__interval")
                .prefetch_related(
                    "mappings__input_mappings__datastream",
                    "mappings__output_datastream",
                    "mappings__rating_curve",
                    "mappings__expression",
                )
                .get(pk=task.pk)
            )

        return task

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def get_collection(
        self,
        principal: Optional[User | APIKey] = None,
        page: int = Field(gt=0, default=1),
        page_size: int = Field(gt=0, default=100),
        order_by: list[str] = Field(default_factory=list),
        search_term: str | Unset = Unset,
        thing: list[uuid.UUID | Thing] | Unset = Unset,
        workspace: list[uuid.UUID | Workspace] | Unset = Unset,
        latest_run_status: list[str] | Unset = Unset,
        transformation_type: list[str] | Unset = Unset,
        output_datastream: list[uuid.UUID] | Unset = Unset,
        input_datastream: list[uuid.UUID] | Unset = Unset,
        rating_curve: list[uuid.UUID] | Unset = Unset,
        expression: list[uuid.UUID] | Unset = Unset,
    ) -> tuple[int, QuerySet[DataProductTask]]:
        """
        Return a collection of data product tasks.
        """

        queryset = self.task_model.objects
        queryset = self.annotate_latest_run(queryset)

        if search_term is not Unset:
            search_vector = SearchVector("name", "description", "thing__name")
            queryset = queryset.annotate(search=search_vector).filter(search=SearchQuery(search_term))

        if thing is not Unset:
            queryset = queryset.filter(thing__in=[getattr(t, "pk", t) for t in thing])

        if workspace is not Unset:
            queryset = queryset.filter(thing__workspace__in=[getattr(w, "pk", w) for w in workspace])

        if latest_run_status is not Unset:
            queryset = queryset.filter(latest_run_status__in=latest_run_status)

        if transformation_type is not Unset:
            queryset = queryset.filter(mappings__transformation_type__in=transformation_type)

        if output_datastream is not Unset:
            queryset = queryset.filter(mappings__output_datastream__in=output_datastream)

        if input_datastream is not Unset:
            queryset = queryset.filter(mappings__input_mappings__datastream__in=input_datastream)

        if rating_curve is not Unset:
            queryset = queryset.filter(mappings__rating_curve__in=rating_curve)

        if expression is not Unset:
            queryset = queryset.filter(mappings__expression__in=expression)

        if not all(term.lstrip("-") in self.order_by_fields for term in order_by):
            raise ValueError(f"Invalid order_by field(s): {order_by}")

        queryset = queryset.order_by(*order_by, "-id")
        queryset = queryset.select_related(
            "thing__workspace", "periodic_task__crontab", "periodic_task__interval"
        ).prefetch_related(
            "mappings__input_mappings__datastream",
            "mappings__output_datastream",
            "mappings__rating_curve",
            "mappings__expression",
        )
        queryset = queryset.visible(principal=principal).distinct()  # noqa

        count = queryset.count()
        offset = (page - 1) * page_size
        queryset = queryset[offset:offset + page_size]

        return count, queryset

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def create(
        self,
        principal: User | APIKey,
        thing: uuid.UUID | Thing,
        name: str,
        mappings: list[dict] = Field(default_factory=list),
        uid: uuid.UUID = Field(default_factory=uuid6.uuid7),
        description: str | None = None,
        crontab: str | None = None,
        interval: int | None = None,
        interval_period: Literal["minutes", "hours", "days"] | None = None,
        start_time: datetime | None = None,
        enabled: bool = True,
    ) -> DataProductTask:
        """
        Create a data product task.
        """

        if isinstance(thing, uuid.UUID):
            try:
                thing = Thing.objects.select_related("workspace").get(pk=thing)
            except Thing.DoesNotExist:
                raise HttpError(404, "Thing does not exist.")

        if not self.task_model.can_principal_create(principal=principal, workspace=thing.workspace):
            raise PermissionError("You do not have permission to create this task.")

        task = self.task_model.objects.create(
            pk=uid,
            name=name,
            description=description,
            thing=thing,
        )

        self.apply_schedule(
            task=task,
            crontab=crontab,
            interval=interval,
            interval_period=interval_period,
            start_time=start_time,
            enabled=enabled,
            celery_task_name=CELERY_TASK_NAME,
        )

        self.apply_mappings(task=task, mappings=mappings)

        return self.get(task.pk)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    @transaction.atomic
    def update(
        self,
        task: Union[uuid.UUID, DataProductTask],
        principal: User | APIKey,
        name: str | Unset = Unset,
        description: str | None | Unset = Unset,
        crontab: str | None | Unset = Unset,
        interval: int | None | Unset = Unset,
        interval_period: Literal["minutes", "hours", "days"] | None | Unset = Unset,
        start_time: datetime | None | Unset = Unset,
        enabled: bool | Unset = Unset,
        mappings: list[dict] | Unset = Unset,
    ) -> DataProductTask:
        """
        Update a data product task.
        """

        task = self.get(task=task, action="edit", principal=principal)

        editable_fields = {"name": name, "description": description}
        for field, value in editable_fields.items():
            if value is not Unset:
                setattr(task, field, value)

        task.save()

        if any(field is not Unset for field in [crontab, interval, interval_period, start_time, enabled]):
            self.apply_schedule(
                task=task,
                crontab=crontab,
                interval=interval,
                interval_period=interval_period,
                start_time=start_time,
                enabled=enabled,
                celery_task_name=CELERY_TASK_NAME,
            )

        if mappings is not Unset:
            self.apply_mappings(task=task, mappings=mappings)

        return self.get(task.pk)

    @validate_call(config=ConfigDict(arbitrary_types_allowed=True))
    def apply_mappings(
        self,
        task: Union[uuid.UUID, DataProductTask],
        mappings: list[dict],
    ) -> None:
        """
        Replace all output mappings (and their input mappings) on a task.
        """

        task = super().get(task)

        for mapping in mappings:
            self._validate_output_mapping(mapping)
            self._validate_input_mapping_variables(mapping)

        task.mappings.all().delete()

        for mapping in mappings:
            transformation_type = mapping["transformation_type"]
            input_mappings = mapping.pop("input_mappings", [])

            output_mapping = DataProductOutputMapping.objects.create(
                task=task,
                output_datastream_id=mapping["output_datastream_id"],
                transformation_type=transformation_type,
                rating_curve_id=mapping.get("rating_curve_id"),
                expression_id=mapping.get("expression_id"),
                alignment_tolerance=mapping.get("alignment_tolerance"),
                aggregation_method=mapping.get("aggregation_method"),
                aggregation_period=mapping.get("aggregation_period"),
                aggregation_timezone_type=mapping.get("aggregation_timezone_type"),
                aggregation_timezone=mapping.get("aggregation_timezone"),
                aggregation_min_coverage=mapping.get("aggregation_min_coverage"),
            )

            DataProductInputMapping.objects.bulk_create([
                DataProductInputMapping(
                    output_mapping=output_mapping,
                    datastream_id=im["datastream_id"],
                    variable_name=im.get("variable_name"),
                )
                for im in input_mappings
            ])

    @staticmethod
    def _validate_output_mapping(mapping: dict) -> None:
        transformation_type = mapping.get("transformation_type")
        has_rating_curve = mapping.get("rating_curve_id") is not None
        has_expression = mapping.get("expression_id") is not None
        has_aggregation_period = mapping.get("aggregation_period") is not None
        has_aggregation_method = mapping.get("aggregation_method") is not None
        has_alignment_tolerance = mapping.get("alignment_tolerance") is not None

        if transformation_type == "rating_curve":
            if not has_rating_curve:
                raise ValueError("rating_curve is required for transformation_type 'rating_curve'.")
            if has_expression:
                raise ValueError("expression must not be set for transformation_type 'rating_curve'.")

        elif transformation_type == "expression":
            if not has_expression:
                raise ValueError("expression is required for transformation_type 'expression'.")
            if has_rating_curve:
                raise ValueError("rating_curve must not be set for transformation_type 'expression'.")

        elif transformation_type == "temporal_aggregation":
            if not has_aggregation_period or not has_aggregation_method:
                raise ValueError(
                    "aggregation_period and aggregation_method are required for transformation_type "
                    "'temporal_aggregation'."
                )
            if has_rating_curve or has_expression:
                raise ValueError(
                    "rating_curve and expression must not be set for transformation_type 'temporal_aggregation'."
                )
            if has_alignment_tolerance:
                raise ValueError(
                    "alignment_tolerance is not applicable for transformation_type 'temporal_aggregation'."
                )

        else:
            raise ValueError(f"Invalid transformation_type '{transformation_type}'.")

        if has_aggregation_period and not has_aggregation_method:
            raise ValueError("aggregation_method is required when aggregation_period is set.")

        if has_aggregation_method and not has_aggregation_period:
            raise ValueError("aggregation_period is required when aggregation_method is set.")

    @staticmethod
    def _validate_input_mapping_variables(mapping: dict) -> None:
        input_mappings = mapping.get("input_mappings", [])

        variable_names = [im["variable_name"] for im in input_mappings if im.get("variable_name") is not None]
        if len(variable_names) != len(set(variable_names)):
            duplicates = {v for v in variable_names if variable_names.count(v) > 1}
            raise ValueError(f"Duplicate variable_name(s) in input_mappings: {', '.join(sorted(duplicates))}.")

        if mapping.get("transformation_type") != "expression":
            return

        expression_id = mapping.get("expression_id")
        if not expression_id:
            return

        expression = Expression.objects.get(pk=expression_id)

        required_vars: set[str] = set()
        if expression.formula:
            tree = ast.parse(expression.formula, mode="eval")
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    required_vars.add(node.id)

        provided_vars = set(variable_names)
        missing = required_vars - provided_vars
        if missing:
            raise ValueError(
                f"Input mappings are missing variables required by the expression: "
                f"{', '.join(sorted(missing))}."
            )
