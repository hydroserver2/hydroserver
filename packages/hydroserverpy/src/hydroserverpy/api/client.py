import requests
import json
from typing import Callable, Optional, Tuple, Union
from hydroserverpy.api.services import (
    WorkspaceService,
    RoleService,
    MonitoringSiteService,
    ObservedPropertyService,
    UnitService,
    ProcessingLevelService,
    ResultQualifierService,
    MethodService,
    DatastreamService,
    DataConnectionService,
    TaskService,
    EtlMappingService,
    MonitoringTaskService,
    MonitoringRuleService,
    RatingCurveService,
    DataProductTaskService,
    DataProductTransformationService,
)


class HydroServer:
    def __init__(
        self,
        host: str,
        base_route: str = "/api/ogc",
        email: Optional[str] = None,
        password: Optional[str] = None,
        apikey: Optional[str] = None,
        access_token: Optional[Union[str, Callable[[], Optional[str]]]] = None,
    ):
        self.host = host.strip("/")
        self.base_route = base_route
        if (email is None) ^ (password is None):
            raise ValueError("Both email and password must be provided together.")
        if access_token is not None and (apikey is not None or email is not None):
            raise ValueError(
                "Provide only one of access_token, apikey, or email and password."
            )

        self.auth: Optional[Tuple[str, str]] = None
        self.apikey = apikey
        if email and password:
            self.auth = (email, password)

        self._access_token = access_token

        self._session = None
        self._timeout = 60

        self._init_session()

    @staticmethod
    def _encode_query_value(value):
        """
        Encodes booleans as the lowercase 'true' and 'false' the API requires; requests would
        otherwise send str(value), i.e. 'True' and 'False'.
        """

        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (list, tuple)):
            return [HydroServer._encode_query_value(item) for item in value]

        return value

    def request(self, method, path, *args, **kwargs) -> requests.Response:
        """Sends a request to HydroServer's API."""

        if isinstance(kwargs.get("params"), dict):
            kwargs["params"] = {
                key: self._encode_query_value(value) for key, value in kwargs["params"].items()
            }

        caller_headers = kwargs.pop("headers", None) or {}

        for attempt in range(2):
            headers = dict(caller_headers)
            access_token = self._resolve_access_token()
            if access_token and not any(
                key.lower() == "authorization" for key in headers
            ):
                headers["Authorization"] = f"Bearer {access_token}"

            try:
                response = getattr(self._session, method)(
                    f"{self.host}/{path.strip('/')}",
                    timeout=self._timeout,
                    headers=headers,
                    *args,
                    **kwargs,
                )
                self._raise_for_hs_status(response)
            except requests.exceptions.ConnectionError as e:
                if attempt == 0:
                    self._init_session()
                    continue
                raise e
            except requests.exceptions.HTTPError as e:
                should_refresh_session = (
                    getattr(e.response, "status_code", None) in {401, 403}
                )
                if attempt == 0 and should_refresh_session:
                    self._init_session()
                    continue
                raise e

            return response

    def _resolve_access_token(self) -> Optional[str]:
        if callable(self._access_token):
            return self._access_token()
        return self._access_token

    def _init_session(self, auth: Optional[Tuple[str, str]] = None) -> None:
        if self._session is not None:
            self._session.close()

        self._session = requests.Session()

        auth = auth or self.auth

        if self.apikey:
            self._session.headers.update({"X-API-Key": self.apikey})
        elif auth:
            self._session.auth = auth

    @staticmethod
    def _raise_for_hs_status(response):
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            try:
                body = json.loads(response.content)
                error_detail = body.get("message") or body.get("detail") or response.text
                http_error_msg = f"{response.status_code} Client Error: {error_detail}"
            except (
                    ValueError,
                    TypeError,
                    AttributeError,
            ):
                http_error_msg = e
            if 400 <= response.status_code < 500:
                raise requests.HTTPError(http_error_msg, response=response)
            else:
                raise requests.HTTPError(str(e), response=response)

    @property
    def workspaces(self):
        """Utilities for managing HydroServer workspaces."""

        return WorkspaceService(self)

    @property
    def roles(self):
        """Utilities for managing HydroServer workspaces."""

        return RoleService(self)

    @property
    def monitoring_sites(self):
        """Utilities for managing HydroServer monitoring_sites."""

        return MonitoringSiteService(self)

    @property
    def observedproperties(self):
        """Utilities for managing HydroServer observed properties."""

        return ObservedPropertyService(self)

    @property
    def units(self):
        """Utilities for managing HydroServer units."""

        return UnitService(self)

    @property
    def processinglevels(self):
        """Utilities for managing HydroServer processing levels."""

        return ProcessingLevelService(self)

    @property
    def resultqualifiers(self):
        """Utilities for managing HydroServer result qualifiers."""

        return ResultQualifierService(self)

    @property
    def methods(self):
        """Utilities for managing HydroServer methods."""

        return MethodService(self)

    @property
    def datastreams(self):
        """Utilities for managing HydroServer datastreams."""

        return DatastreamService(self)

    @property
    def dataconnections(self):
        """Utilities for managing HydroServer ETL data connections."""

        return DataConnectionService(self)

    @property
    def etltasks(self):
        """Utilities for managing HydroServer ETL tasks."""

        return TaskService(self)

    @property
    def etlmappings(self):
        """Utilities for managing HydroServer ETL mappings."""

        return EtlMappingService(self)

    @property
    def monitoringtasks(self):
        """Utilities for managing HydroServer monitoring tasks."""

        return MonitoringTaskService(self)

    @property
    def monitoringrules(self):
        """Utilities for managing HydroServer monitoring rules."""

        return MonitoringRuleService(self)

    @property
    def ratingcurves(self):
        """Utilities for managing HydroServer rating curves."""

        return RatingCurveService(self)

    @property
    def dataproducttasks(self):
        """Utilities for managing HydroServer data product tasks."""

        return DataProductTaskService(self)

    @property
    def dataproducttransformations(self):
        """Utilities for managing HydroServer data product transformations."""

        return DataProductTransformationService(self)
