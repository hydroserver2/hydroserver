import uuid
from datetime import datetime
from typing import ClassVar, List, Optional, Union, TYPE_CHECKING
from pydantic import Field, AliasPath
from ..base import HydroServerBaseModel
from ..orchestration.run import TaskRun
from .transformation import (
    RatingCurveTransformation,
    ExpressionTransformation,
    CompositeExpressionTransformation,
    AggregationTransformation,
    Period,
)

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class DataProductTask(HydroServerBaseModel):
    name: str
    description: Optional[str] = None
    thing_id: uuid.UUID = Field(..., validation_alias=AliasPath("thing", "id"))
    thing_name: str = Field(..., validation_alias=AliasPath("thing", "name"))
    enabled: Optional[bool] = Field(None, validation_alias=AliasPath("schedule", "enabled"))
    start_time: Optional[datetime] = Field(None, validation_alias=AliasPath("schedule", "startTime"))
    crontab: Optional[str] = Field(None, validation_alias=AliasPath("schedule", "crontab"))
    interval: Optional[int] = Field(None, validation_alias=AliasPath("schedule", "interval"))
    interval_period: Optional[Period] = Field(
        None, validation_alias=AliasPath("schedule", "intervalPeriod")
    )
    next_run_at: Optional[datetime] = Field(None, validation_alias=AliasPath("schedule", "nextRunAt"))
    latest_run: Optional[TaskRun] = None
    rating_curve_transformations: List[RatingCurveTransformation] = []
    expression_transformations: List[ExpressionTransformation] = []
    composite_expression_transformations: List[CompositeExpressionTransformation] = []
    aggregation_transformations: List[AggregationTransformation] = []

    _editable_fields: ClassVar[set[str]] = {"name", "description"}

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.data_product_tasks, **data)

    @classmethod
    def get_route(cls):
        return "products/tasks"

    def trigger(self) -> TaskRun:
        """Trigger an immediate run of this data product task."""

        return self.client.data_product_tasks.trigger(uid=self.uid)

    def list_runs(
        self,
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        status: str = ...,
        started_at_min: datetime = ...,
        started_at_max: datetime = ...,
        finished_at_min: datetime = ...,
        finished_at_max: datetime = ...,
    ) -> List[TaskRun]:
        """Get a collection of task runs for this data product task."""

        return self.client.data_product_tasks.list_runs(
            uid=self.uid,
            page=page,
            page_size=page_size,
            order_by=order_by,
            status=status,
            started_at_min=started_at_min,
            started_at_max=started_at_max,
            finished_at_min=finished_at_min,
            finished_at_max=finished_at_max,
        )

    def get_run(self, run_id: Union[uuid.UUID, str]) -> TaskRun:
        """Get a single task run for this data product task."""

        return self.client.data_product_tasks.get_run(uid=self.uid, run_id=run_id)
