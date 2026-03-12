import requests
import json
from typing import Optional, Tuple
from hydroserverpy.api.services import (
    WorkspaceService,
    RoleService,
    ThingService,
    ObservedPropertyService,
    UnitService,
    ProcessingLevelService,
    ResultQualifierService,
    SensorService,
    DatastreamService,
    OrchestrationSystemService,
    DataConnectionService,
    TaskService,
)


class HydroServer:
    def __init__(
        self,
        host: str,
        auth_route: str = "/api/auth",
        base_route: str = "/api/data",
        email: Optional[str] = None,
        password: Optional[str] = None,
        apikey: Optional[str] = None,
    ):
        self.host = host.strip("/")
        self.base_route = base_route
        self.auth = (
            (
                email or "__key__",
                password or apikey,
            )
            if (email and password) or apikey
            else None
        )

        self._auth_url = f"{self.host}{auth_route}/app/session"

        self._session = None
        self._timeout = 60
        self._auth_header = None

        self._init_session()

    def login(self, email: str, password: str) -> None:
        """Provide your HydroServer credentials to log in to your account."""

        self._init_session(auth=(email, password))

    def logout(self) -> None:
        """End your HydroServer session."""

        self._session.delete(self._auth_url, timeout=self._timeout)

    def request(self, method, path, *args, **kwargs) -> requests.Response:
        """Sends a request to HydroServer's API."""

        for attempt in range(2):
            try:
                response = getattr(self._session, method)(
                    f"{self.host}/{path.strip('/')}",
                    timeout=self._timeout,
                    *args,
                    **kwargs,
                )
                self._raise_for_hs_status(response)
            except (
                requests.exceptions.HTTPError,
                requests.exceptions.ConnectionError,
            ) as e:
                if attempt == 0:
                    self._init_session()
                    continue
                else:
                    raise e

            return response

    def _init_session(self, auth: Optional[Tuple[str, str]] = None) -> None:
        if self._session is not None:
            self.logout()
            self._session.close()

        self._session = requests.Session()

        auth = auth or self.auth

        if auth and auth[0] == "__key__":
            self._session.headers.update({"X-API-Key": auth[1]})
        elif auth:
            self._session.headers.update(
                {"Authorization": f"Bearer {self._authenticate(auth[0], auth[1])}"}
            )

    def _authenticate(self, email: str, password: str) -> None:
        response = self._session.post(
            self._auth_url,
            json={"email": email, "password": password},
            timeout=self._timeout,
        )
        response.raise_for_status()
        session_token = response.json().get("meta", {}).get("session_token")

        if not session_token:
            raise ValueError("Authentication failed: No access token returned.")

        return session_token

    @staticmethod
    def _raise_for_hs_status(response):
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            try:
                http_error_msg = (
                    f"{response.status_code} Client Error: "
                    f"{str(json.loads(response.content).get('detail'))}"
                )
            except (
                    ValueError,
                    TypeError,
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
    def things(self):
        """Utilities for managing HydroServer things."""

        return ThingService(self)

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
    def sensors(self):
        """Utilities for managing HydroServer sensors."""

        return SensorService(self)

    @property
    def datastreams(self):
        """Utilities for managing HydroServer datastreams."""

        return DatastreamService(self)

    @property
    def orchestrationsystems(self):
        """Utilities for managing HydroServer orchestration systems."""

        return OrchestrationSystemService(self)

    @property
    def dataconnections(self):
        """Utilities for managing HydroServer ETL data connections."""

        return DataConnectionService(self)

    @property
    def tasks(self):
        """Utilities for managing HydroServer ETL tasks."""

        return TaskService(self)
