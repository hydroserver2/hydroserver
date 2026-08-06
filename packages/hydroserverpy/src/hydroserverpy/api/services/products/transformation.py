import json
from datetime import datetime
from typing import List, Literal, Optional, Union, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models.products.transformation import (
    RatingCurveTransformation,
    ExpressionTransformation,
    AggregationTransformation,
    AggregationMethod,
    Period,
)
from hydroserverpy.api.utils import normalize_uuid

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class DataProductTransformationService:
    def __init__(self, client: "HydroServer"):
        self.client = client

    @staticmethod
    def default_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    def _route(self, task_id: Union[UUID, str], type_slug: str) -> str:
        return f"/{self.client.base_route}/products/tasks/{normalize_uuid(task_id)}/transformations/{type_slug}"

    def _post(self, task_id, type_slug, body) -> dict:
        return self.client.request(
            "post",
            self._route(task_id, type_slug),
            headers={"Content-type": "application/json"},
            data=json.dumps(body, default=self.default_serializer),
        ).json()

    def _patch(self, task_id, type_slug, uid, body) -> dict:
        return self.client.request(
            "patch",
            f"{self._route(task_id, type_slug)}/{str(uid)}",
            headers={"Content-type": "application/json"},
            data=json.dumps(body, default=self.default_serializer),
        ).json()

    # ---------------------------------------------------------------------------
    # Rating Curve Transformations
    # ---------------------------------------------------------------------------

    def list_rating_curve(
        self,
        task_id: Union[UUID, str],
        output_datastream: Optional[Union[UUID, str]] = None,
        input_datastream: Optional[Union[UUID, str]] = None,
    ) -> List[RatingCurveTransformation]:
        """List rating curve transformations for a data product task."""

        params = {}
        if output_datastream is not None:
            params["output_datastream_id"] = normalize_uuid(output_datastream)
        if input_datastream is not None:
            params["input_datastream_id"] = normalize_uuid(input_datastream)

        response = self.client.request("get", self._route(task_id, "rating-curve"), params=params)

        return [RatingCurveTransformation(**t) for t in response.json()]

    def get_rating_curve(
        self, task_id: Union[UUID, str], uid: Union[UUID, str]
    ) -> RatingCurveTransformation:
        """Get a rating curve transformation."""

        response = self.client.request(
            "get", f"{self._route(task_id, 'rating-curve')}/{str(uid)}"
        ).json()

        return RatingCurveTransformation(**response)

    def create_rating_curve(
        self,
        task_id: Union[UUID, str],
        output_datastream: Union[UUID, str],
        input_datastream: Union[UUID, str],
        rating_curve: Union[UUID, str],
        uid: Optional[UUID] = None,
    ) -> RatingCurveTransformation:
        """Create a rating curve transformation on a data product task."""

        body = {
            "outputDatastreamId": normalize_uuid(output_datastream),
            "inputDatastreamId": normalize_uuid(input_datastream),
            "ratingCurveId": normalize_uuid(rating_curve),
        }
        if uid is not None:
            body["id"] = normalize_uuid(uid)

        return RatingCurveTransformation(**self._post(task_id, "rating-curve", body))

    def update_rating_curve(
        self,
        task_id: Union[UUID, str],
        uid: Union[UUID, str],
        input_datastream: Union[UUID, str],
        rating_curve: Union[UUID, str],
    ) -> RatingCurveTransformation:
        """Update a rating curve transformation."""

        body = {
            "inputDatastreamId": normalize_uuid(input_datastream),
            "ratingCurveId": normalize_uuid(rating_curve),
        }

        return RatingCurveTransformation(**self._patch(task_id, "rating-curve", uid, body))

    def delete_rating_curve(self, task_id: Union[UUID, str], uid: Union[UUID, str]) -> None:
        """Delete a rating curve transformation."""

        self.client.request("delete", f"{self._route(task_id, 'rating-curve')}/{str(uid)}")

    # ---------------------------------------------------------------------------
    # Expression Transformations
    # ---------------------------------------------------------------------------

    def list_expression(
        self,
        task_id: Union[UUID, str],
        output_datastream: Optional[Union[UUID, str]] = None,
        input_datastream: Optional[Union[UUID, str]] = None,
    ) -> List[ExpressionTransformation]:
        """List expression transformations for a data product task."""

        params = {}
        if output_datastream is not None:
            params["output_datastream_id"] = normalize_uuid(output_datastream)
        if input_datastream is not None:
            params["input_datastream_id"] = normalize_uuid(input_datastream)

        response = self.client.request("get", self._route(task_id, "expression"), params=params)

        return [ExpressionTransformation(**t) for t in response.json()]

    def get_expression(
        self, task_id: Union[UUID, str], uid: Union[UUID, str]
    ) -> ExpressionTransformation:
        """Get an expression transformation."""

        response = self.client.request(
            "get", f"{self._route(task_id, 'expression')}/{str(uid)}"
        ).json()

        return ExpressionTransformation(**response)

    def create_expression(
        self,
        task_id: Union[UUID, str],
        output_datastream: Union[UUID, str],
        input_datastreams: List[dict],
        formula: str,
        stop_on_no_data: bool = True,
        stop_on_error: bool = True,
        uid: Optional[UUID] = None,
    ) -> ExpressionTransformation:
        """
        Create an expression transformation on a data product task.

        Each item in input_datastreams should have 'datastream_id' and 'variable_name'.
        """

        body = {
            "outputDatastreamId": normalize_uuid(output_datastream),
            "inputDatastreams": [
                {
                    "datastreamId": normalize_uuid(inp.get("datastream_id") or inp.get("datastreamId")),
                    "variableName": inp.get("variable_name") or inp.get("variableName"),
                }
                for inp in input_datastreams
            ],
            "formula": formula,
            "stopOnNoData": stop_on_no_data,
            "stopOnError": stop_on_error,
        }
        if uid is not None:
            body["id"] = normalize_uuid(uid)

        return ExpressionTransformation(**self._post(task_id, "expression", body))

    def update_expression(
        self,
        task_id: Union[UUID, str],
        uid: Union[UUID, str],
        input_datastreams: List[dict] = ...,
        formula: str = ...,
        stop_on_no_data: bool = ...,
        stop_on_error: bool = ...,
    ) -> ExpressionTransformation:
        """
        Update an expression transformation.

        Each item in input_datastreams should have 'datastream_id' and 'variable_name'.
        """

        body = {
            "inputDatastreams": [
                {
                    "datastreamId": normalize_uuid(inp.get("datastream_id") or inp.get("datastreamId")),
                    "variableName": inp.get("variable_name") or inp.get("variableName"),
                }
                for inp in input_datastreams
            ] if input_datastreams is not ... else ...,
            "formula": formula,
            "stopOnNoData": stop_on_no_data,
            "stopOnError": stop_on_error,
        }
        body = {k: v for k, v in body.items() if v is not ...}

        return ExpressionTransformation(**self._patch(task_id, "expression", uid, body))

    def delete_expression(self, task_id: Union[UUID, str], uid: Union[UUID, str]) -> None:
        """Delete an expression transformation."""

        self.client.request("delete", f"{self._route(task_id, 'expression')}/{str(uid)}")

    # ---------------------------------------------------------------------------
    # Aggregation Transformations
    # ---------------------------------------------------------------------------

    def list_aggregation(
        self,
        task_id: Union[UUID, str],
        output_datastream: Optional[Union[UUID, str]] = None,
        input_datastream: Optional[Union[UUID, str]] = None,
    ) -> List[AggregationTransformation]:
        """List aggregation transformations for a data product task."""

        params = {}
        if output_datastream is not None:
            params["output_datastream_id"] = normalize_uuid(output_datastream)
        if input_datastream is not None:
            params["input_datastream_id"] = normalize_uuid(input_datastream)

        response = self.client.request("get", self._route(task_id, "aggregation"), params=params)

        return [AggregationTransformation(**t) for t in response.json()]

    def get_aggregation(
        self, task_id: Union[UUID, str], uid: Union[UUID, str]
    ) -> AggregationTransformation:
        """Get an aggregation transformation."""

        response = self.client.request(
            "get", f"{self._route(task_id, 'aggregation')}/{str(uid)}"
        ).json()

        return AggregationTransformation(**response)

    def create_aggregation(
        self,
        task_id: Union[UUID, str],
        output_datastream: Union[UUID, str],
        input_datastream: Union[UUID, str],
        aggregation_method: AggregationMethod,
        output_interval: int,
        output_interval_units: Period,
        timezone_type: Optional[Literal["utc", "offset", "iana"]] = None,
        timezone: Optional[str] = None,
        min_values: Optional[int] = None,
        uid: Optional[UUID] = None,
    ) -> AggregationTransformation:
        """Create an aggregation transformation on a data product task."""

        body = {
            "outputDatastreamId": normalize_uuid(output_datastream),
            "inputDatastreamId": normalize_uuid(input_datastream),
            "aggregationMethod": aggregation_method,
            "outputInterval": output_interval,
            "outputIntervalUnits": output_interval_units,
            "timezoneType": timezone_type,
            "timezone": timezone,
            "minValues": min_values,
        }
        if uid is not None:
            body["id"] = normalize_uuid(uid)

        return AggregationTransformation(**self._post(task_id, "aggregation", body))

    def update_aggregation(
        self,
        task_id: Union[UUID, str],
        uid: Union[UUID, str],
        input_datastream: Union[UUID, str],
        aggregation_method: AggregationMethod,
        output_interval: int,
        output_interval_units: Period,
        timezone_type: Optional[Literal["utc", "offset", "iana"]] = None,
        timezone: Optional[str] = None,
        min_values: Optional[int] = None,
    ) -> AggregationTransformation:
        """Update an aggregation transformation."""

        body = {
            "inputDatastreamId": normalize_uuid(input_datastream),
            "aggregationMethod": aggregation_method,
            "outputInterval": output_interval,
            "outputIntervalUnits": output_interval_units,
            "timezoneType": timezone_type,
            "timezone": timezone,
            "minValues": min_values,
        }

        return AggregationTransformation(**self._patch(task_id, "aggregation", uid, body))

    def delete_aggregation(self, task_id: Union[UUID, str], uid: Union[UUID, str]) -> None:
        """Delete an aggregation transformation."""

        self.client.request("delete", f"{self._route(task_id, 'aggregation')}/{str(uid)}")