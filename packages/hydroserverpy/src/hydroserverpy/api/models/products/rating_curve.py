import uuid
from typing import ClassVar, List, Literal, Optional, Tuple, TYPE_CHECKING
from ..base import HydroServerBaseModel

if TYPE_CHECKING:
    from hydroserverpy import HydroServer
    from hydroserverpy.api.models import MonitoringSite


class RatingCurve(HydroServerBaseModel):
    name: str
    description: Optional[str] = None
    fitting_method: Literal["linear", "power_law"]
    monitoring_site_id: uuid.UUID
    points: List[Tuple[float, float]] = []

    _editable_fields: ClassVar[set[str]] = set()

    def __init__(self, client: "HydroServer", **data):
        super().__init__(client=client, service=client.ratingcurves, **data)

        self._monitoring_site = None

    @property
    def monitoring_site(self) -> "MonitoringSite":
        """The monitoring site this rating curve belongs to."""

        if self._monitoring_site is None:
            self._monitoring_site = self.client.monitoring_sites.get(uid=self.monitoring_site_id)

        return self._monitoring_site

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
        return "collections/data-product-rating-curves/items"
