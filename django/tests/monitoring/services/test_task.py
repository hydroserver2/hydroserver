import uuid
import pytest
from collections import Counter
from ninja.errors import HttpError
from processing.monitoring.services.task import MonitoringTaskService
from processing.monitoring.models import MonitoringTask

monitoring_task_service = MonitoringTaskService()

TASK1 = "019d0001-0000-7000-8000-000000000001"  # private workspace
TASK2 = "019d0001-0000-7000-8000-000000000002"  # public workspace
# thing 819260c8 = Public Thing, Private Workspace
PRIVATE_WS_THING = "819260c8-2543-4046-b8c4-7431243ed7c5"
# thing 3b7818af = Public Thing, Public Workspace
PUBLIC_WS_THING = "3b7818af-eff7-4149-8517-e5cad9dc22e1"
PRIVATE_WORKSPACE = "b27c51a0-7374-462d-8a53-d97d47176c10"
PUBLIC_WORKSPACE = "6e0deaf2-a92b-421b-9ece-86783265596f"
NONEXISTENT = "00000000-0000-0000-0000-000000000000"


def _err(exc_info):
    val = exc_info.value
    return val.message if isinstance(val, HttpError) else str(val)


@pytest.mark.parametrize(
    "principal, params, expected_names, max_queries",
    [
        # User access — both tasks visible
        ("owner", {}, ["Test Monitoring Task", "Test Public Monitoring Task"], 10),
        ("editor", {}, ["Test Monitoring Task", "Test Public Monitoring Task"], 10),
        ("viewer", {}, ["Test Monitoring Task", "Test Public Monitoring Task"], 10),
        ("admin", {}, ["Test Monitoring Task", "Test Public Monitoring Task"], 10),
        # API key has view access to public workspace only
        ("apikey", {}, ["Test Public Monitoring Task"], 10),
        # No access
        ("unaffiliated", {}, [], 10),
        ("anonymous", {}, [], 10),
        # Pagination
        ("owner", {"page": 2, "page_size": 1}, ["Test Monitoring Task"], 10),
        # Workspace filter
        ("owner", {"workspace": [uuid.UUID(PRIVATE_WORKSPACE)]}, ["Test Monitoring Task"], 10),
        ("owner", {"workspace": [uuid.UUID(PUBLIC_WORKSPACE)]}, ["Test Public Monitoring Task"], 10),
        # Thing filter
        ("owner", {"thing": [uuid.UUID(PRIVATE_WS_THING)]}, ["Test Monitoring Task"], 10),
        ("owner", {"thing": [uuid.UUID(PUBLIC_WS_THING)]}, ["Test Public Monitoring Task"], 10),
        # Rule type filter — TASK1 has a range rule; TASK2 has none
        ("owner", {"rule_type": ["range"]}, ["Test Monitoring Task"], 10),
        ("owner", {"rule_type": ["rate_of_change"]}, [], 10),
        # Datastream filter
        ("owner", {"datastream": [uuid.UUID("dd1f9293-ce29-4b6a-88e6-d65110d1be65")]}, ["Test Monitoring Task"], 10),
        ("owner", {"datastream": [uuid.UUID("27c70b41-e845-40ea-8cc7-d1b40f89816b")]}, [], 10),
    ],
)
def test_list_monitoring_tasks(
    django_assert_max_num_queries, get_principal, principal, params, expected_names, max_queries
):
    with django_assert_max_num_queries(max_queries):
        count, tasks = monitoring_task_service.get_collection(
            principal=get_principal(principal),
            page=params.pop("page", 1),
            page_size=params.pop("page_size", 100),
            order_by=params.pop("order_by", []),
            **params,
        )
        assert Counter(t.name for t in tasks) == Counter(expected_names)


@pytest.mark.parametrize(
    "principal, task, expected_name, error, error_fragment",
    [
        # Successful reads
        ("owner", TASK1, "Test Monitoring Task", None, None),
        ("owner", TASK2, "Test Public Monitoring Task", None, None),
        ("editor", TASK1, "Test Monitoring Task", None, None),
        ("viewer", TASK1, "Test Monitoring Task", None, None),
        ("admin", TASK1, "Test Monitoring Task", None, None),
        # API key can view public workspace task
        ("apikey", TASK2, "Test Public Monitoring Task", None, None),
        # API key cannot see private workspace task
        ("apikey", TASK1, None, LookupError, "does not exist"),
        # No access
        ("unaffiliated", TASK1, None, LookupError, "does not exist"),
        ("anonymous", TASK1, None, LookupError, "does not exist"),
        # Not found
        ("owner", NONEXISTENT, None, LookupError, "does not exist"),
    ],
)
def test_get_monitoring_task(get_principal, principal, task, expected_name, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            monitoring_task_service.get(
                task=uuid.UUID(task),
                principal=get_principal(principal),
            )
        assert error_fragment in _err(exc_info)
    else:
        result = monitoring_task_service.get(
            task=uuid.UUID(task),
            principal=get_principal(principal),
        )
        assert result.name == expected_name


def test_get_monitoring_task_includes_latest_run_rules_and_recipients(get_principal):
    result = monitoring_task_service.get(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
    )
    assert getattr(result, "latest_run_status", None) == "SUCCESS"
    assert result.rules.count() == 1
    assert result.rules.first().rule_type == "range"
    assert result.recipients.count() == 1
    assert result.recipients.first().email == "owner@example.com"


@pytest.mark.parametrize(
    "principal, thing, error, error_fragment",
    [
        ("owner", PRIVATE_WS_THING, None, None),
        ("owner", PUBLIC_WS_THING, None, None),
        ("editor", PRIVATE_WS_THING, None, None),
        ("admin", PRIVATE_WS_THING, None, None),
        # Viewer has no create permission
        ("viewer", PRIVATE_WS_THING, PermissionError, "do not have permission"),
        ("viewer", PUBLIC_WS_THING, PermissionError, "do not have permission"),
        # API key has view-only access
        ("apikey", PUBLIC_WS_THING, PermissionError, "do not have permission"),
        # Unaffiliated: thing found but no workspace create permission
        ("unaffiliated", PRIVATE_WS_THING, PermissionError, "do not have permission"),
        ("unaffiliated", PUBLIC_WS_THING, PermissionError, "do not have permission"),
        # Not found
        ("owner", NONEXISTENT, HttpError, "does not exist"),
    ],
)
def test_create_monitoring_task(get_principal, principal, thing, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            monitoring_task_service.create(
                principal=get_principal(principal),
                thing=uuid.UUID(thing),
                name="New Monitoring Task",
            )
        assert error_fragment in _err(exc_info)
    else:
        result = monitoring_task_service.create(
            principal=get_principal(principal),
            thing=uuid.UUID(thing),
            name="New Monitoring Task",
        )
        assert result.name == "New Monitoring Task"
        assert result.thing_id == uuid.UUID(thing)


def test_create_monitoring_task_with_recipients(get_principal):
    result = monitoring_task_service.create(
        principal=get_principal("owner"),
        thing=uuid.UUID(PRIVATE_WS_THING),
        name="Task With Recipients",
        recipients=["alert1@example.com", "alert2@example.com"],
    )
    emails = {r.email for r in result.recipients.all()}
    assert emails == {"alert1@example.com", "alert2@example.com"}


def test_create_monitoring_task_deduplicates_recipients(get_principal):
    result = monitoring_task_service.create(
        principal=get_principal("owner"),
        thing=uuid.UUID(PRIVATE_WS_THING),
        name="Dedup Recipients",
        recipients=["dup@example.com", "dup@example.com"],
    )
    assert result.recipients.count() == 1


def test_update_monitoring_task_clears_schedule(get_principal):
    task = monitoring_task_service.create(
        principal=get_principal("owner"),
        thing=uuid.UUID(PRIVATE_WS_THING),
        name="Scheduled Task",
        interval=1,
        interval_period="hours",
        enabled=True,
    )
    assert task.periodic_task is not None
    assert task.next_run_at is not None

    result = monitoring_task_service.update(
        task=task.pk,
        principal=get_principal("owner"),
        crontab=None,
        interval=None,
    )
    assert result.periodic_task is None
    assert result.next_run_at is None


def test_create_monitoring_task_with_schedule(get_principal):
    result = monitoring_task_service.create(
        principal=get_principal("owner"),
        thing=uuid.UUID(PRIVATE_WS_THING),
        name="Scheduled Task",
        interval=1,
        interval_period="hours",
        enabled=True,
    )
    assert result.periodic_task is not None
    assert result.periodic_task.interval.every == 1
    assert result.periodic_task.interval.period == "hours"
    assert result.periodic_task.enabled is True


@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("admin", None, None),
        # View-only
        ("viewer", PermissionError, "do not have permission"),
        # Not visible
        ("apikey", LookupError, "does not exist"),
        ("unaffiliated", LookupError, "does not exist"),
    ],
)
def test_update_monitoring_task(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            monitoring_task_service.update(
                task=uuid.UUID(TASK1),
                principal=get_principal(principal),
                name="Updated Task",
            )
        assert error_fragment in _err(exc_info)
    else:
        result = monitoring_task_service.update(
            task=uuid.UUID(TASK1),
            principal=get_principal(principal),
            name="Updated Task",
        )
        assert result.name == "Updated Task"


def test_update_monitoring_task_nonexistent(get_principal):
    with pytest.raises(LookupError) as exc_info:
        monitoring_task_service.update(
            task=uuid.UUID(NONEXISTENT),
            principal=get_principal("owner"),
            name="Updated",
        )
    assert "does not exist" in str(exc_info.value)


def test_update_monitoring_task_replaces_recipients(get_principal):
    result = monitoring_task_service.update(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        recipients=["new@example.com"],
    )
    emails = {r.email for r in result.recipients.all()}
    assert emails == {"new@example.com"}


def test_update_monitoring_task_clears_recipients(get_principal):
    result = monitoring_task_service.update(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        recipients=[],
    )
    assert result.recipients.count() == 0


@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("admin", None, None),
        # View-only
        ("viewer", PermissionError, "do not have permission"),
        # Not visible
        ("apikey", LookupError, "does not exist"),
        ("unaffiliated", LookupError, "does not exist"),
    ],
)
def test_delete_monitoring_task(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            monitoring_task_service.delete(
                task=uuid.UUID(TASK1),
                principal=get_principal(principal),
            )
        assert error_fragment in _err(exc_info)
    else:
        monitoring_task_service.delete(
            task=uuid.UUID(TASK1),
            principal=get_principal(principal),
        )
        assert not MonitoringTask.objects.filter(pk=uuid.UUID(TASK1)).exists()


def test_delete_monitoring_task_nonexistent(get_principal):
    with pytest.raises(LookupError) as exc_info:
        monitoring_task_service.delete(
            task=uuid.UUID(NONEXISTENT),
            principal=get_principal("owner"),
        )
    assert "does not exist" in str(exc_info.value)
