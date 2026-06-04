from typing import List, Literal, Optional, Union, TYPE_CHECKING
from uuid import UUID
from hydroserverpy.api.models.products.rating_curve import RatingCurve
from hydroserverpy.api.utils import normalize_uuid
from ..base import HydroServerBaseService

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class RatingCurveService(HydroServerBaseService):
    def __init__(self, client: "HydroServer"):
        self.model = RatingCurve
        super().__init__(client)

    def list(
        self,
        page: int = ...,
        page_size: int = ...,
        order_by: List[str] = ...,
        thing: Optional[Union[UUID, str]] = ...,
        workspace: Optional[Union[UUID, str]] = ...,
        fetch_all: bool = False,
    ) -> List[RatingCurve]:
        """Fetch a collection of rating curves."""

        return super().list(
            page=page,
            page_size=page_size,
            order_by=order_by,
            fetch_all=fetch_all,
            thing_id=normalize_uuid(thing),
            workspace_id=normalize_uuid(workspace),
        )

    def create(
        self,
        name: str,
        thing: Union[UUID, str],
        fitting_method: Literal["linear", "power_law"],
        description: Optional[str] = None,
        points: Optional[List[tuple]] = None,
        uid: Optional[UUID] = None,
    ) -> RatingCurve:
        """Create a new rating curve."""

        body = {
            "name": name,
            "description": description,
            "fittingMethod": fitting_method,
            "thingId": normalize_uuid(thing),
            "points": points or [],
        }

        if uid is not None:
            body["id"] = normalize_uuid(uid)

        return super().create(**body)

    def update(
        self,
        uid: Union[UUID, str],
        name: str,
        fitting_method: Literal["linear", "power_law"],
        points: List[tuple],
        description: Optional[str] = None,
    ) -> RatingCurve:
        """Update a rating curve."""

        body = {
            "name": name,
            "description": description,
            "fittingMethod": fitting_method,
            "points": points,
        }

        return super().update(uid=str(uid), **body)