import uuid
import pytest
from datetime import datetime, timezone as dt_timezone
from collections import Counter
from ninja.errors import HttpError
from processing.products.services.task import DataProductTaskService
from processing.products.models import DataProductTask

task_service = DataProductTaskService()

TASK1 = "019c0003-0000-7000-8000-000000000001"  # private workspace, private thing
TASK2 = "019c0003-0000-7000-8000-000000000002"  # public workspace, public thing
PRIVATE_THING = "76dadda5-224b-4e1f-8570-e385bd482b2d"
PUBLIC_THING = "3b7818af-eff7-4149-8517-e5cad9dc22e1"
PRIVATE_WORKSPACE = "b27c51a0-7374-462d-8a53-d97d47176c10"
PUBLIC_WORKSPACE = "6e0deaf2-a92b-421b-9ece-86783265596f"
NONEXISTENT = "00000000-0000-0000-0000-000000000000"

# Datastream that is the input for T_RC (fixture transformation in TASK1)
DS_IN_RC = "9f96957b-ee20-4c7b-bf2b-673a0cda3a04"


def _err(exc_info):
    val = exc_info.value
    return val.message if isinstance(val, HttpError) else str(val)


@pytest.mark.parametrize(
    "principal, params, expected_names, max_queries",
    [
        # Users with DataProducts view access see both tasks
        ("owner", {}, ["Test Task", "Test Public Task"], 10),
        ("editor", {}, ["Test Task", "Test Public Task"], 10),
        ("viewer", {}, ["Test Task", "Test Public Task"], 10),
        ("admin", {}, ["Test Task", "Test Public Task"], 10),
        # API key has view access to public workspace only
        ("apikey", {}, ["Test Public Task"], 10),
        # No access
        ("unaffiliated", {}, [], 10),
        ("anonymous", {}, [], 10),
        # Pagination — tasks ordered by -id; TASK2 > TASK1 so page 2 has "Test Task"
        ("owner", {"page": 2, "page_size": 1}, ["Test Task"], 10),
        # Workspace filter
        ("owner", {"workspace": [uuid.UUID(PRIVATE_WORKSPACE)]}, ["Test Task"], 10),
        ("owner", {"workspace": [uuid.UUID(PUBLIC_WORKSPACE)]}, ["Test Public Task"], 10),
        # Thing filter
        ("owner", {"thing": [uuid.UUID(PRIVATE_THING)]}, ["Test Task"], 10),
        ("owner", {"thing": [uuid.UUID(PUBLIC_THING)]}, ["Test Public Task"], 10),
    ],
)
def test_list_data_product_tasks(
    django_assert_max_num_queries, get_principal, principal, params, expected_names, max_queries
):
    with django_assert_max_num_queries(max_queries):
        count, tasks = task_service.get_collection(
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
        ("owner", TASK1, "Test Task", None, None),
        ("owner", TASK2, "Test Public Task", None, None),
        ("editor", TASK1, "Test Task", None, None),
        ("viewer", TASK1, "Test Task", None, None),
        ("admin", TASK1, "Test Task", None, None),
        # API key can see public workspace task
        ("apikey", TASK2, "Test Public Task", None, None),
        # API key cannot see private workspace task
        ("apikey", TASK1, None, LookupError, "does not exist"),
        # No access
        ("unaffiliated", TASK1, None, LookupError, "does not exist"),
        ("anonymous", TASK1, None, LookupError, "does not exist"),
        # Not found
        ("owner", NONEXISTENT, None, LookupError, "does not exist"),
    ],
)
def test_get_data_product_task(get_principal, principal, task, expected_name, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            task_service.get(
                task=uuid.UUID(task),
                principal=get_principal(principal),
            )
        assert error_fragment in _err(exc_info)
    else:
        result = task_service.get(
            task=uuid.UUID(task),
            principal=get_principal(principal),
        )
        assert result.name == expected_name


def test_get_data_product_task_includes_latest_run(get_principal):
    """TASK1 has a TaskRun with status SUCCESS in the fixture."""
    result = task_service.get(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
    )
    assert result.latest_run_status == "SUCCESS"
    assert result.latest_run_finished_at is not None


def test_get_data_product_task_includes_transformations(get_principal):
    """TASK1 has 2 fixture transformations: rating_curve and expression."""
    result = task_service.get(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
    )
    types = {t.transformation_type for t in result.transformations.all()}
    assert types == {"rating_curve", "expression"}


@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("admin", None, None),
        # Viewer has no create permission
        ("viewer", PermissionError, "do not have permission"),
        # API key and unaffiliated: no edit permission
        ("apikey", PermissionError, "do not have permission"),
        ("unaffiliated", PermissionError, "do not have permission"),
    ],
)
def test_create_data_product_task(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            task_service.create(
                principal=get_principal(principal),
                thing=uuid.UUID(PRIVATE_THING),
                name="New Task",
            )
        assert error_fragment in _err(exc_info)
    else:
        result = task_service.create(
            principal=get_principal(principal),
            thing=uuid.UUID(PRIVATE_THING),
            name="New Task",
        )
        assert result.name == "New Task"
        assert result.thing_id == uuid.UUID(PRIVATE_THING)


def test_create_data_product_task_nonexistent_thing(get_principal):
    with pytest.raises(LookupError) as exc_info:
        task_service.create(
            principal=get_principal("owner"),
            thing=uuid.UUID(NONEXISTENT),
            name="New Task",
        )
    assert "does not exist" in _err(exc_info)


def test_update_data_product_task_clears_schedule(get_principal):
    task = task_service.create(
        principal=get_principal("owner"),
        thing=uuid.UUID(PRIVATE_THING),
        name="Scheduled Task",
        interval=6,
        interval_period="hours",
        enabled=True,
    )
    assert task.periodic_task is not None
    assert task.next_run_at is not None

    result = task_service.update(
        task=task.pk,
        principal=get_principal("owner"),
        crontab=None,
        interval=None,
    )
    assert result.periodic_task is None
    assert result.next_run_at is None


def test_create_data_product_task_with_crontab_schedule(get_principal):
    result = task_service.create(
        principal=get_principal("owner"),
        thing=uuid.UUID(PRIVATE_THING),
        name="Scheduled Task",
        crontab="0 8 * * *",
        enabled=True,
    )
    assert result.periodic_task is not None
    assert result.periodic_task.crontab is not None
    assert result.periodic_task.enabled is True


def test_create_data_product_task_with_interval_schedule(get_principal):
    result = task_service.create(
        principal=get_principal("owner"),
        thing=uuid.UUID(PRIVATE_THING),
        name="Interval Task",
        interval=6,
        interval_period="hours",
        enabled=True,
    )
    assert result.periodic_task is not None
    assert result.periodic_task.interval.every == 6
    assert result.periodic_task.interval.period == "hours"


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
def test_update_data_product_task(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            task_service.update(
                task=uuid.UUID(TASK1),
                principal=get_principal(principal),
                name="Updated Task",
            )
        assert error_fragment in _err(exc_info)
    else:
        result = task_service.update(
            task=uuid.UUID(TASK1),
            principal=get_principal(principal),
            name="Updated Task",
        )
        assert result.name == "Updated Task"


def test_update_data_product_task_nonexistent(get_principal):
    with pytest.raises(LookupError) as exc_info:
        task_service.update(
            task=uuid.UUID(NONEXISTENT),
            principal=get_principal("owner"),
            name="Updated",
        )
    assert "does not exist" in str(exc_info.value)


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
def test_delete_data_product_task(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            task_service.delete(
                task=uuid.UUID(TASK1),
                principal=get_principal(principal),
            )
        assert error_fragment in _err(exc_info)
    else:
        task_service.delete(
            task=uuid.UUID(TASK1),
            principal=get_principal(principal),
        )
        assert not DataProductTask.objects.filter(pk=uuid.UUID(TASK1)).exists()


def test_delete_data_product_task_nonexistent(get_principal):
    with pytest.raises(LookupError) as exc_info:
        task_service.delete(
            task=uuid.UUID(NONEXISTENT),
            principal=get_principal("owner"),
        )
    assert "does not exist" in str(exc_info.value)


# --- Task run ---

def test_run_data_product_task_loads_observations(get_principal):
    """Running TASK1 processes T_RC (rating_curve) and T_EXP (expression) and loads observations."""
    from core.sta.models import Datastream
    from core.sta.models.observation import Observation
    import uuid6

    # Seed one observation into the T_RC input datastream (DS_IN_RC) so the run
    # has something to process. Setting phenomenon_end_time is required by the
    # run methods as the "end of available data" boundary.
    ds_in = Datastream.objects.get(pk=DS_IN_RC)
    t = datetime(2025, 3, 1, 12, 0, tzinfo=dt_timezone.utc)
    Observation.objects.create(pk=uuid6.uuid7(), datastream=ds_in, phenomenon_time=t, result=1.5)
    ds_in.phenomenon_end_time = t
    ds_in.save(update_fields=["phenomenon_end_time"])

    result = task_service.run(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
    )
    assert result["loaded_total"] > 0
    assert "observation" in result["message"].lower() or "loaded" in result["message"].lower()


def test_run_data_product_task_permission_denied(get_principal):
    with pytest.raises(PermissionError):
        task_service.run(
            task=uuid.UUID(TASK1),
            principal=get_principal("viewer"),
        )


def test_run_data_product_task_not_visible(get_principal):
    with pytest.raises(LookupError):
        task_service.run(
            task=uuid.UUID(TASK1),
            principal=get_principal("apikey"),
        )
