import re
import json

from datetime import datetime, timezone

from django_celery_beat.models import IntervalSchedule, PeriodicTask

from core.iam.models import (
    Collaborator,
    Organization,
    Role,
    ServiceAccount,
    User,
    WorkspaceTransferConfirmation,
)
from core.sta.models import (
    ObservedProperty,
    ProcessingLevel,
    ResultQualifier,
    Method,
    Unit,
)
from tests.core.iam.factories import UserFactory, WorkspaceFactory
from tests.core.sta.factories import (
    DatastreamFactory,
    ObservationFactory,
    ObservedPropertyFactory,
    ProcessingLevelFactory,
    ResultQualifierFactory,
    MethodFactory,
    MonitoringSiteFactory,
    UnitFactory,
)
from tests.processing.etl.factories import (
    DataConnectionFactory,
    EtlMappingFactory,
    EtlTaskFactory,
    PayloadFactory,
)


E2E_PASSWORD = "HydroServer123!"
SCENARIO_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9-]{1,80}$")


def _validated_key(scenario_key):
    if not isinstance(scenario_key, str) or not SCENARIO_KEY_PATTERN.fullmatch(
        scenario_key
    ):
        raise ValueError("Invalid E2E scenario key.")
    return scenario_key.lower()


def _name(base, marker):
    return f"{base} [{marker[-8:]}]"


def _user(kind, marker, **kwargs):
    email = f"{kind}+{marker}@example.com"
    return UserFactory(
        username=email,
        email=email,
        first_name=kwargs.pop("first_name", kind.title()),
        last_name=kwargs.pop("last_name", "Example"),
        owned_workspace_limit=kwargs.pop("owned_workspace_limit", None),
        password=E2E_PASSWORD,
        **kwargs,
    )


def _monitoring_site(workspace, marker, *, name, code, private, latitude, longitude):
    monitoring_site = MonitoringSiteFactory(
        workspace=workspace,
        name=_name(name, marker),
        description=f"E2E scenario site {marker}",
        code=code,
        type="Private" if private else "Public",
        latitude=latitude,
        longitude=longitude,
        elevation_m=1,
        elevation_datum="WGS84",
        country="US",
        is_private=private,
    )
    return monitoring_site


def _datastream(
    monitoring_site,
    marker,
    *,
    name,
    method,
    observed_property,
    processing_level,
    unit,
    private=False,
):
    begin = datetime(2025, 2, 10, 8, 0, tzinfo=timezone.utc)
    end = datetime(2025, 2, 10, 9, 0, tzinfo=timezone.utc)
    datastream = DatastreamFactory(
        monitoring_site=monitoring_site,
        name=_name(name, marker),
        description=f"E2E scenario datastream {marker}",
        method=method,
        observed_property=observed_property,
        processing_level=processing_level,
        unit=unit,
        observation_type="Field Observation",
        result_type="Time Series",
        status="Ongoing",
        sampled_medium="Surface Water",
        value_count=2,
        intended_time_spacing=1,
        intended_time_spacing_unit="hours",
        aggregation_statistic="Continuous",
        time_aggregation_interval=1,
        time_aggregation_interval_unit="hours",
        phenomenon_begin_time=begin,
        phenomenon_end_time=end,
        is_private=private,
        is_visible=True,
        tags={f"E2E {marker}": "Scenario"},
    )
    return datastream


def _metadata(workspace, marker, scope):
    return {
        "method": MethodFactory(
            workspace=workspace,
            name=_name(f"{scope} Assigned Method", marker),
            description=f"E2E scenario method {marker}",
            type=f"{scope} Assigned Method",
            code=marker,
        ),
        "observed_property": ObservedPropertyFactory(
            workspace=workspace,
            name=_name(f"{scope} Assigned Observed Property", marker),
            definition=f"https://example.com/e2e/{marker}",
            description=f"E2E scenario observed property {marker}",
            observed_property_type=scope,
            code=f"{scope}-{marker}",
        ),
        "processing_level": ProcessingLevelFactory(
            workspace=workspace,
            code=f"{scope}Assigned-{marker}",
            definition=f"E2E scenario processing level {marker}",
            explanation=f"E2E scenario processing level {marker}",
        ),
        "unit": UnitFactory(
            workspace=workspace,
            name=_name(f"{scope} Assigned Unit", marker),
            symbol=f"{scope[:1]}{marker[-4:]}",
            definition=f"E2E scenario unit {marker}",
            unit_type=f"{scope} Unit",
        ),
    }


def _additional_workspace_metadata(workspace, marker, scope):
    MethodFactory(
        workspace=workspace,
        name=_name(f"{scope} Method", marker),
        description=f"E2E scenario method {marker}",
        type=f"{scope} Method",
    )
    ObservedPropertyFactory(
        workspace=workspace,
        name=_name(f"{scope} Observed Property", marker),
        definition=f"https://example.com/e2e/{marker}/additional",
        description=f"E2E scenario observed property {marker}",
        observed_property_type=scope,
        code=f"{scope}-additional-{marker}",
    )
    ProcessingLevelFactory(
        workspace=workspace,
        code=f"{scope}Additional-{marker}",
        definition=f"E2E scenario processing level {marker}",
        explanation=f"E2E scenario processing level {marker}",
    )
    UnitFactory(
        workspace=workspace,
        name=_name(f"{scope} Unit", marker),
        symbol=f"{scope[:1]}A{marker[-3:]}",
        definition=f"E2E scenario unit {marker}",
        unit_type=f"{scope} Unit",
    )
    ResultQualifierFactory(
        workspace=workspace,
        code=f"{scope}ResultQualifier-{marker}",
        description=f"E2E scenario result qualifier {marker}",
    )


def cleanup_scenario(scenario_key):
    marker = _validated_key(scenario_key)

    # Deleting scenario users removes their owned workspaces and all
    # workspace-scoped objects through normal model cascades. This remains
    # idempotent when a test already deleted a user or transferred ownership.
    User.objects.filter(email__contains=f"+{marker}@example.com").delete()

    Method.objects.filter(code=marker, workspace__isnull=True).delete()
    ObservedProperty.objects.filter(
        code=f"System-{marker}", workspace__isnull=True
    ).delete()
    ProcessingLevel.objects.filter(
        code=f"SystemAssigned-{marker}", workspace__isnull=True
    ).delete()
    Unit.objects.filter(
        symbol=f"S{marker[-4:]}", workspace__isnull=True
    ).delete()
    ResultQualifier.objects.filter(
        code=f"SystemResultQualifier-{marker}", workspace__isnull=True
    ).delete()
    Organization.objects.filter(code=f"E2E-{marker}").delete()


def create_scenario(scenario_key):
    marker = _validated_key(scenario_key)

    owner = _user("owner", marker, first_name="Owner", last_name="Johnson")
    editor = _user("editor", marker, first_name="Editor", last_name="Smith")
    viewer = _user("viewer", marker, first_name="Viewer", last_name="Davis")
    unaffiliated = _user(
        "unaffiliated", marker, first_name="Unaffiliated", last_name="Anderson"
    )
    limited = _user(
        "limited",
        marker,
        first_name="Limited",
        last_name="Taylor",
        owned_workspace_limit=0,
    )
    delete_me = _user(
        "delete-me",
        marker,
        first_name="Delete",
        last_name="Me",
        owned_workspace_limit=0,
    )

    organization = Organization.objects.create(
        code=f"E2E-{marker}",
        name=_name("E2E Test Organization", marker),
        description="Deterministic organization for browser profile tests.",
        organization_type="Other",
        link="https://example.com/org/e2e-profile",
    )
    profile = _user(
        "profile",
        marker,
        first_name="Profile",
        last_name="Example",
        organization=organization,
    )

    public_workspace = WorkspaceFactory(
        owner=owner, name=_name("Public", marker), is_private=False
    )
    private_workspace = WorkspaceFactory(
        owner=owner, name=_name("Private", marker), is_private=True
    )
    transfer_workspace = WorkspaceFactory(
        owner=owner, name=_name("Transfer", marker), is_private=True
    )
    WorkspaceTransferConfirmation.objects.create(
        workspace=transfer_workspace, new_owner=unaffiliated
    )

    editor_role = Role.objects.get(name="Editor", workspace__isnull=True)
    viewer_role = Role.objects.get(name="Viewer", workspace__isnull=True)
    data_loader_role = Role.objects.get(name="Data Loader", workspace__isnull=True)
    for workspace in (public_workspace, private_workspace):
        Collaborator.objects.create(
            workspace=workspace, user=editor, role=editor_role
        )
        Collaborator.objects.create(
            workspace=workspace, user=viewer, role=viewer_role
        )

    service_account = ServiceAccount.objects.create(
        workspace=public_workspace,
        name="apikey",
        description=f"E2E scenario service account {marker}",
    )
    Collaborator.objects.create(
        workspace=public_workspace,
        service_account=service_account,
        role=data_loader_role,
    )

    public_monitoring_site = _monitoring_site(
        public_workspace,
        marker,
        name="Public MonitoringSite",
        code=f"UWRL-{marker[-4:]}",
        private=False,
        latitude=41.739742,
        longitude=-111.793766,
    )
    private_monitoring_site = _monitoring_site(
        private_workspace,
        marker,
        name="Private MonitoringSite",
        code=f"TSC-{marker[-4:]}",
        private=True,
        latitude=41.743042,
        longitude=-111.813250,
    )
    private_public_monitoring_site = _monitoring_site(
        public_workspace,
        marker,
        name="Private MonitoringSite Public Workspace",
        code=f"MAIN-{marker[-4:]}",
        private=True,
        latitude=41.740741,
        longitude=-111.813924,
    )
    private_workspace_public_monitoring_site = _monitoring_site(
        private_workspace,
        marker,
        name="Public MonitoringSite Private Workspace",
        code=f"LIB-{marker[-4:]}",
        private=False,
        latitude=41.742008,
        longitude=-111.809720,
    )
    mutable_public_monitoring_site = _monitoring_site(
        public_workspace,
        marker,
        name="E2E Mutable MonitoringSite",
        code=f"E2E-MUTABLE-{marker[-4:]}",
        private=False,
        latitude=41.741111,
        longitude=-111.805555,
    )
    mutable_public_monitoring_site.tags = {"E2E": "Mutable"}
    mutable_public_monitoring_site.save()

    public_metadata = _metadata(public_workspace, marker, "Public")
    private_metadata = _metadata(private_workspace, marker, "Private")
    system_metadata = _metadata(None, marker, "System")
    _additional_workspace_metadata(public_workspace, marker, "Public")
    _additional_workspace_metadata(private_workspace, marker, "Private")
    system_qualifier = ResultQualifierFactory(
        workspace=None,
        code=f"SystemResultQualifier-{marker}",
        description=f"E2E scenario result qualifier {marker}",
    )

    public_datastream = _datastream(
        public_monitoring_site,
        marker,
        name="Public Datastream 1",
        **public_metadata,
    )
    private_visible_datastream = _datastream(
        public_monitoring_site,
        marker,
        name="Private Datastream 1",
        private=True,
        **public_metadata,
    )
    public_system_datastream = _datastream(
        public_monitoring_site,
        marker,
        name="Public Datastream 2",
        **system_metadata,
    )
    private_workspace_datastream = _datastream(
        private_workspace_public_monitoring_site,
        marker,
        name="Private Datastream 4",
        **private_metadata,
    )

    begin = datetime(2025, 2, 10, 8, 0, tzinfo=timezone.utc)
    end = datetime(2025, 2, 10, 9, 0, tzinfo=timezone.utc)
    for datastream, values in (
        (public_datastream, (1.1, 3.1)),
        (private_visible_datastream, (1.2, 3.2)),
        (public_system_datastream, (1.9, 3.9)),
        (private_workspace_datastream, (1.5, 3.5)),
    ):
        ObservationFactory(
            datastream=datastream,
            phenomenon_time=begin,
            result=values[0],
            quality_code="E2E",
        )
        ObservationFactory(
            datastream=datastream,
            phenomenon_time=end,
            result=values[1],
            quality_code="E2E",
            result_qualifiers=[system_qualifier.code]
            if datastream == public_datastream
            else [],
        )

    data_connection = DataConnectionFactory(
        workspace=private_workspace,
        name=_name("Test ETL Data Connection", marker),
        source_url="https://example.com/data.csv",
    )
    PayloadFactory(data_connection=data_connection)
    interval = IntervalSchedule.objects.create(
        every=1, period=IntervalSchedule.DAYS
    )
    periodic_task = PeriodicTask.objects.create(
        name=f"E2E ETL {marker}",
        task="processing.etl.tasks.run_etl_task",
        kwargs=json.dumps({"scenario": marker}),
        interval=interval,
        enabled=False,
    )
    etl_task = EtlTaskFactory(
        data_connection=data_connection,
        name=_name("Test ETL Task", marker),
        periodic_task=periodic_task,
    )
    EtlMappingFactory(
        etl_task=etl_task,
        source_identifier="test_value",
        target_datastream=private_workspace_datastream,
    )

    def user_data(user):
        return {"email": user.email, "password": E2E_PASSWORD}

    return {
        "scenarioKey": marker,
        "users": {
            "owner": user_data(owner),
            "editor": user_data(editor),
            "viewer": user_data(viewer),
            "limited": user_data(limited),
            "unaffiliated": user_data(unaffiliated),
            "profile": user_data(profile),
            "deleteMe": user_data(delete_me),
        },
        "fixtures": {
            "workspaces": {
                "public": {"id": str(public_workspace.id), "name": public_workspace.name},
                "private": {"id": str(private_workspace.id), "name": private_workspace.name},
                "transfer": {"id": str(transfer_workspace.id), "name": transfer_workspace.name},
            },
            "monitoringSites": {
                "public": {
                    "id": str(public_monitoring_site.id),
                    "name": public_monitoring_site.name,
                    "siteCode": public_monitoring_site.code,
                },
                "private": {
                    "id": str(private_monitoring_site.id),
                    "name": private_monitoring_site.name,
                    "siteCode": private_monitoring_site.code,
                },
                "privatePublic": {
                    "id": str(private_public_monitoring_site.id),
                    "name": private_public_monitoring_site.name,
                    "siteCode": private_public_monitoring_site.code,
                },
                "privateWorkspacePublic": {
                    "id": str(private_workspace_public_monitoring_site.id),
                    "name": private_workspace_public_monitoring_site.name,
                    "siteCode": private_workspace_public_monitoring_site.code,
                },
                "mutablePublic": {
                    "id": str(mutable_public_monitoring_site.id),
                    "name": mutable_public_monitoring_site.name,
                    "siteCode": mutable_public_monitoring_site.code,
                },
            },
            "datastreams": {
                "public": {"id": str(public_datastream.id), "name": public_datastream.name},
                "publicSystemMetadata": {
                    "id": str(public_system_datastream.id),
                    "name": public_system_datastream.name,
                },
                "privateVisible": {
                    "id": str(private_visible_datastream.id),
                    "name": private_visible_datastream.name,
                },
                "privateWorkspacePublic": {
                    "id": str(private_workspace_datastream.id),
                    "name": private_workspace_datastream.name,
                },
            },
            "metadata": {
                "privateAssignedMethod": {
                    "id": str(private_metadata["method"].id),
                    "name": private_metadata["method"].name,
                },
                "publicAssignedMethod": {
                    "id": str(public_metadata["method"].id),
                    "name": public_metadata["method"].name,
                },
                "publicAssignedObservedProperty": {
                    "id": str(public_metadata["observed_property"].id),
                    "name": public_metadata["observed_property"].name,
                },
                "publicAssignedProcessingLevel": {
                    "id": str(public_metadata["processing_level"].id),
                    "name": public_metadata["processing_level"].code,
                },
                "publicAssignedUnit": {
                    "id": str(public_metadata["unit"].id),
                    "name": public_metadata["unit"].name,
                },
                "systemMethod": {
                    "id": str(system_metadata["method"].id),
                    "name": system_metadata["method"].name,
                },
            },
            "orchestration": {
                "systemName": "Test Streaming Data Loader",
                "dataConnectionName": data_connection.name,
                "taskName": etl_task.name,
            },
        },
    }
