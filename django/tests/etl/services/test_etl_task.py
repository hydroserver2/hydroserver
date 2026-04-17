import uuid
import pytest
from collections import Counter
from ninja.errors import HttpError
from processing.etl.services.task import EtlTaskService
from processing.etl.models import EtlTask

etl_task_service = EtlTaskService()

TASK1 = "019adbc3-35e8-7f25-bc68-171fb66d446e"  # private workspace, via DC1
DC1 = "019adb5c-da8b-7970-877d-c3b4ca37cc60"    # private workspace
DC2 = "019bbd9d-ee62-7669-8db0-3ef50802f1d8"    # public workspace
PRIVATE_WORKSPACE = "b27c51a0-7374-462d-8a53-d97d47176c10"
PUBLIC_WORKSPACE = "6e0deaf2-a92b-421b-9ece-86783265596f"
DS_PRIVATE_WS = "dd1f9293-ce29-4b6a-88e6-d65110d1be65"   # public datastream, public thing, private workspace (mapped by TASK1)
DS_PRIVATE_WS_2 = "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2"  # private datastream, public thing, private workspace
DS_PUBLIC_WS = "27c70b41-e845-40ea-8cc7-d1b40f89816b"   # public datastream, public thing, public workspace
NONEXISTENT = "00000000-0000-0000-0000-000000000000"


@pytest.mark.parametrize(
    "principal, params, expected_names, max_queries",
    [
        # User access — task is in private workspace so all affiliated users see it
        ("owner", {}, ["Test ETL Task"], 10),
        ("editor", {}, ["Test ETL Task"], 10),
        ("viewer", {}, ["Test ETL Task"], 10),
        ("admin", {}, ["Test ETL Task"], 10),
        # API key only has access to public workspace; task is in private workspace
        ("apikey", {}, [], 10),
        # No access
        ("unaffiliated", {}, [], 10),
        ("anonymous", {}, [], 10),
        # Pagination — only 1 task, page 2 is empty
        ("owner", {"page": 2, "page_size": 1}, [], 10),
        # Workspace filter
        ("owner", {"workspace": [uuid.UUID(PRIVATE_WORKSPACE)]}, ["Test ETL Task"], 10),
        ("owner", {"workspace": [uuid.UUID(PUBLIC_WORKSPACE)]}, [], 10),
        # Data connection filter
        ("owner", {"data_connection": [uuid.UUID(DC1)]}, ["Test ETL Task"], 10),
        ("owner", {"data_connection": [uuid.UUID(DC2)]}, [], 10),
    ],
)
def test_list_etl_tasks(
    django_assert_max_num_queries, get_principal, principal, params, expected_names, max_queries
):
    with django_assert_max_num_queries(max_queries):
        count, tasks = etl_task_service.get_collection(
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
        ("owner", TASK1, "Test ETL Task", None, None),
        ("editor", TASK1, "Test ETL Task", None, None),
        ("viewer", TASK1, "Test ETL Task", None, None),
        ("admin", TASK1, "Test ETL Task", None, None),
        # API key cannot see private workspace tasks
        ("apikey", TASK1, None, LookupError, "does not exist"),
        # No access
        ("unaffiliated", TASK1, None, LookupError, "does not exist"),
        ("anonymous", TASK1, None, LookupError, "does not exist"),
        # Not found
        ("owner", NONEXISTENT, None, LookupError, "does not exist"),
    ],
)
def test_get_etl_task(get_principal, principal, task, expected_name, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            etl_task_service.get(
                task=uuid.UUID(task),
                principal=get_principal(principal),
            )
        assert error_fragment in str(exc_info.value)
    else:
        result = etl_task_service.get(
            task=uuid.UUID(task),
            principal=get_principal(principal),
        )
        assert result.name == expected_name


def test_get_etl_task_includes_latest_run_and_mappings(get_principal):
    result = etl_task_service.get(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
    )
    assert getattr(result, "latest_run_status", None) == "SUCCESS"
    assert result.etl_mappings.count() == 1
    assert result.etl_mappings.first().source_identifier == "test_value"


def _create_params():
    return dict(
        name="New ETL Task",
        data_connection=uuid.UUID(DC1),
        mappings=[{"source_identifier": "col1", "target_datastream": uuid.UUID(DS_PRIVATE_WS_2)}],
    )


@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("admin", None, None),
        # Viewer has no create permission
        ("viewer", PermissionError, "do not have permission"),
        # API key and unaffiliated: DC fetched without visibility filter, then create permission denied
        ("apikey", PermissionError, "do not have permission"),
        ("unaffiliated", PermissionError, "do not have permission"),
    ],
)
def test_create_etl_task(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            etl_task_service.create(
                principal=get_principal(principal),
                **_create_params(),
            )
        assert error_fragment in str(exc_info.value)
    else:
        result = etl_task_service.create(
            principal=get_principal(principal),
            **_create_params(),
        )
        assert result.name == "New ETL Task"
        assert result.data_connection_id == uuid.UUID(DC1)


def test_create_etl_task_nonexistent_data_connection(get_principal):
    with pytest.raises(LookupError) as exc_info:
        etl_task_service.create(
            principal=get_principal("owner"),
            name="New ETL Task",
            data_connection=uuid.UUID(NONEXISTENT),
        )
    assert "does not exist" in str(exc_info.value)


def test_create_etl_task_creates_mappings(get_principal):
    result = etl_task_service.create(
        principal=get_principal("owner"),
        **_create_params(),
    )
    assert result.etl_mappings.count() == 1
    mapping = result.etl_mappings.first()
    assert mapping.source_identifier == "col1"
    assert mapping.target_datastream_id == uuid.UUID(DS_PRIVATE_WS_2)


def test_create_etl_task_with_schedule(get_principal):
    result = etl_task_service.create(
        principal=get_principal("owner"),
        name="Scheduled Task",
        data_connection=uuid.UUID(DC1),
        interval=1,
        interval_period="days",
        enabled=True,
    )
    assert result.periodic_task is not None
    assert result.periodic_task.interval.every == 1
    assert result.periodic_task.interval.period == "days"
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
def test_update_etl_task(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            etl_task_service.update(
                task=uuid.UUID(TASK1),
                principal=get_principal(principal),
                name="Updated Name",
            )
        assert error_fragment in str(exc_info.value)
    else:
        result = etl_task_service.update(
            task=uuid.UUID(TASK1),
            principal=get_principal(principal),
            name="Updated Name",
        )
        assert result.name == "Updated Name"


def test_update_etl_task_nonexistent(get_principal):
    with pytest.raises(LookupError) as exc_info:
        etl_task_service.update(
            task=uuid.UUID(NONEXISTENT),
            principal=get_principal("owner"),
            name="Updated Name",
        )
    assert "does not exist" in str(exc_info.value)


def test_update_etl_task_replaces_mappings(get_principal):
    result = etl_task_service.update(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        mappings=[{"source_identifier": "new_col", "target_datastream": uuid.UUID(DS_PRIVATE_WS)}],
    )
    assert result.etl_mappings.count() == 1
    assert result.etl_mappings.first().source_identifier == "new_col"


def test_update_etl_task_clears_mappings(get_principal):
    result = etl_task_service.update(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        mappings=[],
    )
    assert result.etl_mappings.count() == 0


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
def test_delete_etl_task(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            etl_task_service.delete(
                task=uuid.UUID(TASK1),
                principal=get_principal(principal),
            )
        assert error_fragment in str(exc_info.value)
    else:
        etl_task_service.delete(
            task=uuid.UUID(TASK1),
            principal=get_principal(principal),
        )
        assert not EtlTask.objects.filter(pk=uuid.UUID(TASK1)).exists()


def test_delete_etl_task_nonexistent(get_principal):
    with pytest.raises(LookupError) as exc_info:
        etl_task_service.delete(
            task=uuid.UUID(NONEXISTENT),
            principal=get_principal("owner"),
        )
    assert "does not exist" in str(exc_info.value)


def test_apply_mappings_rejects_nonexistent_datastream(get_principal):
    with pytest.raises(HttpError) as exc_info:
        etl_task_service.apply_mappings(
            task=uuid.UUID(TASK1),
            mappings=[{"source_identifier": "col1", "target_datastream": uuid.UUID(NONEXISTENT)}],
            principal=get_principal("owner"),
        )
    assert exc_info.value.status_code == 404


def test_apply_mappings_rejects_wrong_workspace_datastream(get_principal):
    with pytest.raises(ValueError) as exc_info:
        etl_task_service.apply_mappings(
            task=uuid.UUID(TASK1),
            mappings=[{"source_identifier": "col1", "target_datastream": uuid.UUID(DS_PUBLIC_WS)}],
            principal=get_principal("owner"),
        )
    assert "does not belong to workspace" in str(exc_info.value)


def test_apply_mappings_rejects_no_edit_access(get_principal):
    with pytest.raises(HttpError) as exc_info:
        etl_task_service.apply_mappings(
            task=uuid.UUID(TASK1),
            mappings=[{"source_identifier": "col1", "target_datastream": uuid.UUID(DS_PRIVATE_WS)}],
            principal=get_principal("viewer"),
        )
    assert exc_info.value.status_code == 403


def test_apply_mappings_rejects_already_mapped_datastream(get_principal):
    second_task = etl_task_service.create(
        principal=get_principal("owner"),
        name="Second Task",
        data_connection=uuid.UUID(DC1),
    )
    with pytest.raises(ValueError) as exc_info:
        etl_task_service.apply_mappings(
            task=second_task.pk,
            mappings=[{"source_identifier": "col1", "target_datastream": uuid.UUID(DS_PRIVATE_WS)}],
            principal=get_principal("owner"),
        )
    assert "already mapped to by another task" in str(exc_info.value)
