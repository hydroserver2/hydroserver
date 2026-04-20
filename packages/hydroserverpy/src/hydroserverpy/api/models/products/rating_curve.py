import uuid
from typing import ClassVar, List, Literal, Optional, Tuple, TYPE_CHECKING
from pydantic import Field, AliasPath
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer


class RatingCurve(HydroServerBaseModel):
    name: str
    description: Optional[str] = None
    fitting_method: Literal["linear", "power_law"]
    thing_id: uuid.UUID = Field(..., validation_alias=AliasPath("thing", "id"))
    thing_name: str = Field(..., validation_alias=AliasPath("thing", "name"))
    points: List[Tuple[float, float]] = []

    _editable_fields: ClassVar[set[str]] = set()

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.rating_curves, **data)

    def save(self):
        """Saves changes to this resource to HydroServer."""

        if not self.service:
            raise NotImplementedError("Saving not enabled for this object.")

        if not self.uid:
            raise AttributeError("Data cannot be saved: UID is not set.")

        saved_resource = self.service.update(
            self.uid,
            name=self.name,
            fitting_method=self.fitting_method,
            points=self.points,
            description=self.description,
        )
        self._server_data = saved_resource.dict(by_alias=False).copy()
        self.__dict__.update(saved_resource.__dict__)

    @classmethod
    def get_route(cls):
        return "products/rating-curves"
