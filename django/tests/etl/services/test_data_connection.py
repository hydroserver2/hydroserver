import uuid
import pytest
from collections import Counter
from datetime import timedelta
from django.utils import timezone
from django_celery_beat.models import IntervalSchedule, PeriodicTask
from ninja.errors import HttpError
from processing.etl.services.data_connection import DataConnectionService
from processing.etl.models import DataConnection
from processing.orchestration.models import TaskRun

data_connection_service = DataConnectionService()

DC1 = "019adb5c-da8b-7970-877d-c3b4ca37cc60"  # private workspace
DC2 = "019bbd9d-ee62-7669-8db0-3ef50802f1d8"  # public workspace
PRIVATE_WORKSPACE = "b27c51a0-7374-462d-8a53-d97d47176c10"
PUBLIC_WORKSPACE = "6e0deaf2-a92b-421b-9ece-86783265596f"
NONEXISTENT = "00000000-0000-0000-0000-000000000000"


def _err(exc_info):
    """Return a consistent error message string from any exception type."""
    val = exc_info.value
    return val.message if isinstance(val, HttpError) else str(val)


def _make_schedule(enabled):
    interval, _ = IntervalSchedule.objects.get_or_create(
        every=1, period=IntervalSchedule.DAYS
    )
    return PeriodicTask.objects.create(
        name=f"attention-test-{uuid.uuid4()}",
        task="processing.etl.tasks.run_etl_task",
        interval=interval,
        enabled=enabled,
    )


def _make_task(dc, *, last_status=None, schedule_enabled=None, next_run_at=None):
    from processing.etl.models import EtlTask

    periodic_task = (
        _make_schedule(schedule_enabled) if schedule_enabled is not None else None
    )
    task = EtlTask.objects.create(
        name="attention task",
        data_connection=dc,
        periodic_task=periodic_task,
        next_run_at=next_run_at,
    )
    if last_status is not None:
        TaskRun.objects.create(task=task, status=last_status, message="")
    return task


def test_attention_count_matches_frontend_status_buckets(get_principal):
    """task_attention_count should equal the number of tasks the frontend shows
    as "Needs attention" or "Behind schedule" — and nothing else.

    The frontend marks a task "Behind schedule" only when it has an *enabled*
    schedule, a *successful* latest run, and a next run in the past. Paused,
    running (STARTED/PENDING), and never-run tasks are NOT issues even when
    overdue, so they must be excluded from the count.
    """
    past = timezone.now() - timedelta(hours=1)
    future = timezone.now() + timedelta(hours=1)

    dc = DataConnection.objects.create(
        name="Attention Count DC",
        workspace_id=uuid.UUID(PRIVATE_WORKSPACE),
        source_url="https://example.com/test.csv",
    )

    # Counted: latest run failed (Needs attention) — schedule state irrelevant.
    _make_task(dc, last_status="FAILURE", schedule_enabled=True, next_run_at=future)
    # Counted: enabled schedule, succeeded, overdue (Behind schedule).
    _make_task(dc, last_status="SUCCESS", schedule_enabled=True, next_run_at=past)

    # Not counted: succeeded and next run still in the future (OK).
    _make_task(dc, last_status="SUCCESS", schedule_enabled=True, next_run_at=future)
    # Not counted: overdue but schedule disabled / paused (Loading paused).
    _make_task(dc, last_status="SUCCESS", schedule_enabled=False, next_run_at=past)
    # Not counted: overdue but currently running (Pending).
    _make_task(dc, last_status="STARTED", schedule_enabled=True, next_run_at=past)
    # Not counted: overdue but has never run (Pending).
    _make_task(dc, last_status=None, schedule_enabled=True, next_run_at=past)

    annotated = DataConnectionService.annotate_task_counts(
        DataConnection.objects.filter(pk=dc.pk)
    ).get()

    assert annotated.task_count == 6
    assert annotated.task_attention_count == 2


@pytest.mark.parametrize(
    "principal, params, expected_names, max_queries",
    [
        # User access
        ("owner", {}, ["Test ETL Data Connection", "Test Public ETL Data Connection"], 10),
        ("editor", {}, ["Test ETL Data Connection", "Test Public ETL Data Connection"], 10),
        ("viewer", {}, ["Test ETL Data Connection", "Test Public ETL Data Connection"], 10),
        ("admin", {}, ["Test ETL Data Connection", "Test Public ETL Data Connection"], 10),
        # API key only sees public workspace data connections
        ("apikey", {}, ["Test Public ETL Data Connection"], 10),
        # No access
        ("unaffiliated", {}, [], 10),
        ("anonymous", {}, [], 10),
        # Pagination and ordering — page 2 of 1 gives the alphabetically lower name
        (
            "owner",
            {"page": 2, "page_size": 1, "order_by": ["-name"]},
            ["Test ETL Data Connection"],
            10,
        ),
        # Workspace filtering
        (
            "owner",
            {"workspace": [uuid.UUID(PRIVATE_WORKSPACE)]},
            ["Test ETL Data Connection"],
            10,
        ),
        (
            "owner",
            {"workspace": [uuid.UUID(PUBLIC_WORKSPACE)]},
            ["Test Public ETL Data Connection"],
            10,
        ),
    ],
)
def test_list_data_connections(
    django_assert_max_num_queries, get_principal, principal, params, expected_names, max_queries
):
    with django_assert_max_num_queries(max_queries):
        count, dcs = data_connection_service.get_collection(
            principal=get_principal(principal),
            page=params.pop("page", 1),
            page_size=params.pop("page_size", 100),
            order_by=params.pop("order_by", []),
            **params,
        )
        assert Counter(dc.name for dc in dcs) == Counter(expected_names)


@pytest.mark.parametrize(
    "principal, data_connection, expected_name, error, error_fragment",
    [
        # Successful reads
        ("owner", DC1, "Test ETL Data Connection", None, None),
        ("owner", DC2, "Test Public ETL Data Connection", None, None),
        ("editor", DC1, "Test ETL Data Connection", None, None),
        ("viewer", DC1, "Test ETL Data Connection", None, None),
        ("admin", DC1, "Test ETL Data Connection", None, None),
        ("apikey", DC2, "Test Public ETL Data Connection", None, None),
        # No access to private workspace
        ("apikey", DC1, None, LookupError, "does not exist"),
        # DataConnection is excluded from public-workspace auto-visibility
        ("unaffiliated", DC1, None, LookupError, "does not exist"),
        ("anonymous", DC1, None, LookupError, "does not exist"),
        ("anonymous", DC2, None, LookupError, "does not exist"),
        # Not found
        ("owner", NONEXISTENT, None, LookupError, "does not exist"),
    ],
)
def test_get_data_connection(
    get_principal, principal, data_connection, expected_name, error, error_fragment
):
    if error:
        with pytest.raises(error) as exc_info:
            data_connection_service.get(
                data_connection=uuid.UUID(data_connection),
                principal=get_principal(principal),
            )
        assert error_fragment in _err(exc_info)
    else:
        result = data_connection_service.get(
            data_connection=uuid.UUID(data_connection),
            principal=get_principal(principal),
        )
        assert result.name == expected_name


def _create_params():
    return dict(
        name="New Data Connection",
        source_url="https://example.com/test.csv",
        payload_type="CSV",
        timestamp_key="timestamp",
        header_row=1,
        data_start_row=2,
        delimiter=",",
    )


@pytest.mark.parametrize(
    "principal, workspace, error, error_fragment",
    [
        # Authorized
        ("owner", PRIVATE_WORKSPACE, None, None),
        ("owner", PUBLIC_WORKSPACE, None, None),
        ("editor", PRIVATE_WORKSPACE, None, None),
        ("admin", PRIVATE_WORKSPACE, None, None),
        # Viewer has no create permission
        ("viewer", PRIVATE_WORKSPACE, PermissionError, "do not have permission"),
        ("viewer", PUBLIC_WORKSPACE, PermissionError, "do not have permission"),
        # API key (Data Loader): has view but not create for ETL
        ("apikey", PUBLIC_WORKSPACE, PermissionError, "do not have permission"),
        # Unaffiliated and anonymous cannot create in accessible workspaces
        ("unaffiliated", PUBLIC_WORKSPACE, PermissionError, "do not have permission"),
        ("anonymous", PUBLIC_WORKSPACE, PermissionError, "do not have permission"),
        # Private workspace not accessible to apikey / anonymous
        ("apikey", PRIVATE_WORKSPACE, HttpError, "Workspace does not exist"),
        ("anonymous", PRIVATE_WORKSPACE, HttpError, "Workspace does not exist"),
        # Non-existent workspace
        ("owner", NONEXISTENT, HttpError, "Workspace does not exist"),
    ],
)
def test_create_data_connection(get_principal, principal, workspace, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            data_connection_service.create(
                principal=get_principal(principal),
                workspace=uuid.UUID(workspace),
                **_create_params(),
            )
        assert error_fragment in _err(exc_info)
    else:
        result = data_connection_service.create(
            principal=get_principal(principal),
            workspace=uuid.UUID(workspace),
            **_create_params(),
        )
        assert result.name == "New Data Connection"
        assert result.source_url == "https://example.com/test.csv"
        assert result.workspace_id == uuid.UUID(workspace)


def test_create_data_connection_stores_timestamp_fields_on_payload(get_principal):
    result = data_connection_service.create(
        principal=get_principal("owner"),
        workspace=uuid.UUID(PRIVATE_WORKSPACE),
        **_create_params(),
    )
    assert result.payload.timestamp_key == "timestamp"
    assert result.payload.timestamp_format is None
    assert not hasattr(result, "timestamp_key")


def test_create_data_connection_with_timestamp_format(get_principal):
    result = data_connection_service.create(
        principal=get_principal("owner"),
        workspace=uuid.UUID(PRIVATE_WORKSPACE),
        **{**_create_params(), "timestamp_format": "%Y-%m-%d %H:%M:%S"},
    )
    assert result.payload.timestamp_key == "timestamp"
    assert result.payload.timestamp_format == "%Y-%m-%d %H:%M:%S"


def test_create_data_connection_stores_timezone_on_data_connection(get_principal):
    result = data_connection_service.create(
        principal=get_principal("owner"),
        workspace=uuid.UUID(PRIVATE_WORKSPACE),
        **{**_create_params(), "timezone_type": "iana", "timezone": "America/Denver"},
    )
    assert result.timezone_type == "iana"
    assert result.timezone == "America/Denver"


def test_update_data_connection_timestamp_key(get_principal):
    result = data_connection_service.update(
        data_connection=uuid.UUID(DC1),
        principal=get_principal("owner"),
        timestamp_key="new_timestamp",
    )
    assert result.payload.timestamp_key == "new_timestamp"


def test_update_data_connection_timestamp_format(get_principal):
    result = data_connection_service.update(
        data_connection=uuid.UUID(DC1),
        principal=get_principal("owner"),
        timestamp_format="%m/%d/%Y",
    )
    assert result.payload.timestamp_format == "%m/%d/%Y"


def test_update_data_connection_timezone(get_principal):
    result = data_connection_service.update(
        data_connection=uuid.UUID(DC1),
        principal=get_principal("owner"),
        timezone_type="offset",
        timezone="+05:30",
    )
    assert result.timezone_type == "offset"
    assert result.timezone == "+05:30"


@pytest.mark.parametrize(
    "auth_header_name, auth_header_value, error",
    [
        ("X-API-Key", "secret", None),
        (None, None, None),
        ("X-API-Key", None, ValueError),
        (None, "secret", ValueError),
    ],
)
def test_create_data_connection_auth_headers(get_principal, auth_header_name, auth_header_value, error):
    params = {**_create_params(), "auth_header_name": auth_header_name, "auth_header_value": auth_header_value}
    if error:
        with pytest.raises(error):
            data_connection_service.create(
                principal=get_principal("owner"),
                workspace=uuid.UUID(PRIVATE_WORKSPACE),
                **params,
            )
    else:
        result = data_connection_service.create(
            principal=get_principal("owner"),
            workspace=uuid.UUID(PRIVATE_WORKSPACE),
            **params,
        )
        assert result.auth_header_name == auth_header_name
        assert result.auth_header_value == auth_header_value


@pytest.mark.parametrize(
    "auth_header_name, auth_header_value, error",
    [
        ("X-API-Key", "secret", None),
        (None, None, None),
        ("X-API-Key", None, ValueError),
        (None, "secret", ValueError),
    ],
)
def test_update_data_connection_auth_headers(get_principal, auth_header_name, auth_header_value, error):
    if error:
        with pytest.raises(error):
            data_connection_service.update(
                data_connection=uuid.UUID(DC1),
                principal=get_principal("owner"),
                auth_header_name=auth_header_name,
                auth_header_value=auth_header_value,
            )
    else:
        result = data_connection_service.update(
            data_connection=uuid.UUID(DC1),
            principal=get_principal("owner"),
            auth_header_name=auth_header_name,
            auth_header_value=auth_header_value,
        )
        assert result.auth_header_name == auth_header_name
        assert result.auth_header_value == auth_header_value


@pytest.mark.parametrize(
    "principal, data_connection, error, error_fragment",
    [
        # Authorized
        ("owner", DC1, None, None),
        ("editor", DC1, None, None),
        ("admin", DC1, None, None),
        # View-only
        ("viewer", DC1, PermissionError, "do not have permission"),
        # API key: not visible for private DC; view-only for public DC
        ("apikey", DC1, LookupError, "does not exist"),
        ("apikey", DC2, PermissionError, "do not have permission"),
        # Anonymous
        ("anonymous", DC1, LookupError, "does not exist"),
        # Not found
        ("owner", NONEXISTENT, LookupError, "does not exist"),
    ],
)
def test_update_data_connection(get_principal, principal, data_connection, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            data_connection_service.update(
                data_connection=uuid.UUID(data_connection),
                principal=get_principal(principal),
                name="Updated Name",
            )
        assert error_fragment in _err(exc_info)
    else:
        result = data_connection_service.update(
            data_connection=uuid.UUID(data_connection),
            principal=get_principal(principal),
            name="Updated Name",
        )
        assert result.name == "Updated Name"


@pytest.mark.parametrize(
    "principal, data_connection, error, error_fragment",
    [
        # Authorized
        ("owner", DC1, None, None),
        ("editor", DC1, None, None),
        ("admin", DC1, None, None),
        # View-only
        ("viewer", DC1, PermissionError, "do not have permission"),
        # Not visible
        ("apikey", DC1, LookupError, "does not exist"),
        ("anonymous", DC1, LookupError, "does not exist"),
        # Not found
        ("owner", NONEXISTENT, LookupError, "does not exist"),
    ],
)
def test_delete_data_connection(get_principal, principal, data_connection, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            data_connection_service.delete(
                data_connection=uuid.UUID(data_connection),
                principal=get_principal(principal),
            )
        assert error_fragment in _err(exc_info)
    else:
        data_connection_service.delete(
            data_connection=uuid.UUID(data_connection),
            principal=get_principal(principal),
        )
        assert not DataConnection.objects.filter(pk=uuid.UUID(data_connection)).exists()
