import json
from datetime import datetime
from typing import List, Literal, Optional, Union, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models.products.transformation import (
    RatingCurveTransformation,
    DerivationTransformation,
    AggregationTransformation,
    AggregationMethod,
    Period,
)
from hydroserverpy.api.utils import normalize_uuid

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class DataProductTransformationService:
    """
    Rating curve, derivation, and aggregation transformations are all managed
    through a single `/data-product-transformations` resource, discriminated
    by a `transformationType` field rather than separate routes.
    """

    def __init__(self, client: "HydroServer"):
        self.client = client

    @staticmethod
    def default_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    def _route(self) -> str:
        return f"/{self.client.base_route}/data-product-transformations"

    def _list(
        self,
        transformation_type: str,
        task_id: Optional[Union[UUID, str]] = None,
        workspace_id: Optional[Union[UUID, str]] = None,
        output_datastream: Optional[Union[UUID, str]] = None,
        input_datastream: Optional[Union[UUID, str]] = None,
    ) -> List[dict]:
        params = {"transformation_type": transformation_type}
        if task_id is not None:
            params["task_id"] = normalize_uuid(task_id)
        if workspace_id is not None:
            params["workspace_id"] = normalize_uuid(workspace_id)
        if output_datastream is not None:
            params["output_datastream_id"] = normalize_uuid(output_datastream)
        if input_datastream is not None:
            params["input_datastream_id"] = normalize_uuid(input_datastream)

        response = self.client.request("get", self._route(), params=params)

        return response.json()["data"]

    def _get(self, uid) -> dict:
        payload = self.client.request(
            "get", f"{self._route()}/{str(uid)}"
        ).json()

        return payload.get("data", payload)

    def _post(self, task_id, body) -> dict:
        body = {**body, "taskId": normalize_uuid(task_id)}
        response = self.client.request(
            "post",
            self._route(),
            headers={"Content-type": "application/json"},
            data=json.dumps(body, default=self.default_serializer),
        ).json()

        return self._get(response["id"])

    def _patch(self, uid, body) -> dict:
        self.client.request(
            "patch",
            f"{self._route()}/{str(uid)}",
            headers={"Content-type": "application/json"},
            data=json.dumps(body, default=self.default_serializer),
        )

        return self._get(uid)

    def _delete(self, uid) -> None:
        self.client.request("delete", f"{self._route()}/{str(uid)}")

    @staticmethod
    def _single_input(datastream: Union[UUID, str]) -> List[dict]:
        return [{"datastreamId": normalize_uuid(datastream)}]

    # ---------------------------------------------------------------------------
    # Rating Curve Transformations
    # ---------------------------------------------------------------------------

    def list_rating_curve(
        self,
        task_id: Optional[Union[UUID, str]] = None,
        workspace_id: Optional[Union[UUID, str]] = None,
        output_datastream: Optional[Union[UUID, str]] = None,
        input_datastream: Optional[Union[UUID, str]] = None,
    ) -> List[RatingCurveTransformation]:
        """List rating curve transformations."""

        return [
            RatingCurveTransformation(**t)
            for t in self._list(
                "rating_curve", task_id, workspace_id, output_datastream, input_datastream
            )
        ]

    def get_rating_curve(self, uid: Union[UUID, str]) -> RatingCurveTransformation:
        """Get a rating curve transformation."""

        return RatingCurveTransformation(**self._get(uid))

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
            "transformationType": "rating_curve",
            "outputDatastreamId": normalize_uuid(output_datastream),
            "inputDatastreams": self._single_input(input_datastream),
            "ratingCurveId": normalize_uuid(rating_curve),
        }
        if uid is not None:
            body["id"] = normalize_uuid(uid)

        return RatingCurveTransformation(**self._post(task_id, body))

    def update_rating_curve(
        self,
        uid: Union[UUID, str],
        input_datastream: Union[UUID, str],
        rating_curve: Union[UUID, str],
    ) -> RatingCurveTransformation:
        """Update a rating curve transformation."""

        body = {
            "inputDatastreams": self._single_input(input_datastream),
            "ratingCurveId": normalize_uuid(rating_curve),
        }

        return RatingCurveTransformation(**self._patch(uid, body))

    def delete_rating_curve(self, uid: Union[UUID, str]) -> None:
        """Delete a rating curve transformation."""

        self._delete(uid)

    # ---------------------------------------------------------------------------
    # Derivation Transformations
    # ---------------------------------------------------------------------------

    def list_derivation(
        self,
        task_id: Optional[Union[UUID, str]] = None,
        workspace_id: Optional[Union[UUID, str]] = None,
        output_datastream: Optional[Union[UUID, str]] = None,
        input_datastream: Optional[Union[UUID, str]] = None,
    ) -> List[DerivationTransformation]:
        """List derivation transformations."""

        return [
            DerivationTransformation(**t)
            for t in self._list(
                "derivation", task_id, workspace_id, output_datastream, input_datastream
            )
        ]

    def get_derivation(self, uid: Union[UUID, str]) -> DerivationTransformation:
        """Get a derivation transformation."""

        return DerivationTransformation(**self._get(uid))

    def create_derivation(
        self,
        task_id: Union[UUID, str],
        output_datastream: Union[UUID, str],
        input_datastreams: List[dict],
        formula: str,
        stop_on_no_data: bool = True,
        stop_on_error: bool = True,
        uid: Optional[UUID] = None,
    ) -> DerivationTransformation:
        """
        Create a derivation transformation on a data product task.

        Each item in input_datastreams should have 'datastream_id' and 'variable_name'.
        """

        body = {
            "transformationType": "derivation",
            "outputDatastreamId": normalize_uuid(output_datastream),
            "inputDatastreams": [
                {"datastreamId": normalize_uuid(inp.get("datastream_id") or inp.get("datastreamId")),
                 "variableName": inp.get("variable_name") or inp.get("variableName")}
                for inp in input_datastreams
            ],
            "formula": formula,
            "stopOnNoData": stop_on_no_data,
            "stopOnError": stop_on_error,
        }
        if uid is not None:
            body["id"] = normalize_uuid(uid)

        return DerivationTransformation(**self._post(task_id, body))

    def update_derivation(
        self,
        uid: Union[UUID, str],
        input_datastreams: List[dict] = ...,
        formula: str = ...,
        stop_on_no_data: bool = ...,
        stop_on_error: bool = ...,
    ) -> DerivationTransformation:
        """
        Update a derivation transformation.

        Each item in input_datastreams should have 'datastream_id' and 'variable_name'.
        """

        body = {
            "inputDatastreams": [
                {"datastreamId": normalize_uuid(inp.get("datastream_id") or inp.get("datastreamId")),
                 "variableName": inp.get("variable_name") or inp.get("variableName")}
                for inp in input_datastreams
            ] if input_datastreams is not ... else ...,
            "formula": formula,
            "stopOnNoData": stop_on_no_data,
            "stopOnError": stop_on_error,
        }
        body = {k: v for k, v in body.items() if v is not ...}

        return DerivationTransformation(**self._patch(uid, body))

    def delete_derivation(self, uid: Union[UUID, str]) -> None:
        """Delete a derivation transformation."""

        self._delete(uid)

    # ---------------------------------------------------------------------------
    # Aggregation Transformations
    # ---------------------------------------------------------------------------

    def list_aggregation(
        self,
        task_id: Optional[Union[UUID, str]] = None,
        workspace_id: Optional[Union[UUID, str]] = None,
        output_datastream: Optional[Union[UUID, str]] = None,
        input_datastream: Optional[Union[UUID, str]] = None,
    ) -> List[AggregationTransformation]:
        """List aggregation transformations."""

        return [
            AggregationTransformation(**t)
            for t in self._list(
                "aggregation", task_id, workspace_id, output_datastream, input_datastream
            )
        ]

    def get_aggregation(self, uid: Union[UUID, str]) -> AggregationTransformation:
        """Get an aggregation transformation."""

        return AggregationTransformation(**self._get(uid))

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
            "transformationType": "aggregation",
            "outputDatastreamId": normalize_uuid(output_datastream),
            "inputDatastreams": self._single_input(input_datastream),
            "aggregationMethod": aggregation_method,
            "outputInterval": output_interval,
            "outputIntervalUnits": output_interval_units,
            "timezoneType": timezone_type,
            "timezone": timezone,
            "minValues": min_values,
        }
        if uid is not None:
            body["id"] = normalize_uuid(uid)

        return AggregationTransformation(**self._post(task_id, body))

    def update_aggregation(
        self,
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
            "inputDatastreams": self._single_input(input_datastream),
            "aggregationMethod": aggregation_method,
            "outputInterval": output_interval,
            "outputIntervalUnits": output_interval_units,
            "timezoneType": timezone_type,
            "timezone": timezone,
            "minValues": min_values,
        }

        return AggregationTransformation(**self._patch(uid, body))

    def delete_aggregation(self, uid: Union[UUID, str]) -> None:
        """Delete an aggregation transformation."""

        self._delete(uid)
