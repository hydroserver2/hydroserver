import uuid
from datetime import datetime
from functools import cached_property
from typing import ClassVar, List, Optional, Union, TYPE_CHECKING
from pydantic import Field, AliasPath
from ..base import HydroServerBaseModel
from ..orchestration.run import TaskRun
from .transformation import (
    RatingCurveTransformation,
    DerivationTransformation,
    AggregationTransformation,
    Period,
)

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class DataProductTask(HydroServerBaseModel):
    name: str
    description: Optional[str] = None
    monitoring_site_id: uuid.UUID
    enabled: Optional[bool] = Field(None, validation_alias=AliasPath("schedule", "enabled"))
    start_time: Optional[datetime] = Field(None, validation_alias=AliasPath("schedule", "startTime"))
    crontab: Optional[str] = Field(None, validation_alias=AliasPath("schedule", "crontab"))
    interval: Optional[int] = Field(None, validation_alias=AliasPath("schedule", "interval"))
    interval_period: Optional[Period] = Field(
        None, validation_alias=AliasPath("schedule", "intervalPeriod")
    )
    next_run_at: Optional[datetime] = Field(None, validation_alias=AliasPath("schedule", "nextRunAt"))
    latest_run: Optional[TaskRun] = None
    transformation_types: List[str] = []

    _editable_fields: ClassVar[set[str]] = {"name", "description"}

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.dataproducttasks, **data)

    @classmethod
    def get_route(cls):
        return "data-product-tasks"

    @cached_property
    def rating_curve_transformations(self) -> List["RatingCurveTransformation"]:
        """All rating curve transformations for this data product task."""

        return self.client.dataproducttransformations.list_rating_curve(task_id=self.uid)

    @cached_property
    def derivation_transformations(self) -> List["DerivationTransformation"]:
        """All derivation transformations for this data product task."""

        return self.client.dataproducttransformations.list_derivation(task_id=self.uid)

    @cached_property
    def aggregation_transformations(self) -> List["AggregationTransformation"]:
        """All aggregation transformations for this data product task."""

        return self.client.dataproducttransformations.list_aggregation(task_id=self.uid)

    def trigger(self) -> TaskRun:
        """Trigger an immediate run of this data product task."""

        return self.client.dataproducttasks.trigger(uid=self.uid)

    def list_runs(
        self,
        offset: int = ...,
        limit: int = ...,
        sortby: List[str] = ...,
        status: str = ...,
        started_at_min: datetime = ...,
        started_at_max: datetime = ...,
        finished_at_min: datetime = ...,
        finished_at_max: datetime = ...,
    ) -> List[TaskRun]:
        """Get a collection of task runs for this data product task."""

        return self.client.dataproducttasks.list_runs(
            uid=self.uid,
            offset=offset,
            limit=limit,
            sortby=sortby,
            status=status,
            started_at_min=started_at_min,
            started_at_max=started_at_max,
            finished_at_min=finished_at_min,
            finished_at_max=finished_at_max,
        )

    def get_run(self, run_id: Union[uuid.UUID, str]) -> TaskRun:
        """Get a single task run for this data product task."""

        return self.client.dataproducttasks.get_run(uid=self.uid, run_id=run_id)
