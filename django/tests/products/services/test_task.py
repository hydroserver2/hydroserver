import uuid
import pytest
from collections import Counter
from ninja.errors import HttpError
from processing.products.services.task import DataProductTaskService
from processing.products.models import DataProductTask

task_service = DataProductTaskService()

TASK1 = "019c0003-0000-7000-8000-000000000001"  # private workspace, private thing
PRIVATE_THING = "76dadda5-224b-4e1f-8570-e385bd482b2d"
PUBLIC_THING = "3b7818af-eff7-4149-8517-e5cad9dc22e1"
PRIVATE_WORKSPACE = "b27c51a0-7374-462d-8a53-d97d47176c10"
PUBLIC_WORKSPACE = "6e0deaf2-a92b-421b-9ece-86783265596f"
# Datastreams: e0506cac is private DS in public workspace — unused as output in fixture
OUTPUT_DS = "e0506cac-3e50-4d0a-814d-7ae0146705b2"
INPUT_DS = "27c70b41-e845-40ea-8cc7-d1b40f89816b"
# Rating curve and expression from products fixtures
RATING_CURVE = "019c0002-0000-7000-8000-000000000001"
EXPRESSION = "019c0001-0000-7000-8000-000000000001"
NONEXISTENT = "00000000-0000-0000-0000-000000000000"


def _err(exc_info):
    val = exc_info.value
    return val.message if isinstance(val, HttpError) else str(val)


def _temporal_aggregation_mapping(output_ds=OUTPUT_DS, input_ds=INPUT_DS):
    return {
        "transformation_type": "temporal_aggregation",
        "output_datastream_id": uuid.UUID(output_ds),
        "aggregation_method": "simple_mean",
        "aggregation_period": "daily",
        "input_mappings": [{"datastream_id": uuid.UUID(input_ds), "variable_name": None}],
    }


@pytest.mark.parametrize(
    "principal, params, expected_names, max_queries",
    [
        # User access — task is in private workspace
        ("owner", {}, ["Test Data Product Task"], 10),
        ("editor", {}, ["Test Data Product Task"], 10),
        ("viewer", {}, ["Test Data Product Task"], 10),
        ("admin", {}, ["Test Data Product Task"], 10),
        # API key only has access to public workspace; task is in private workspace
        ("apikey", {}, [], 10),
        # No access
        ("unaffiliated", {}, [], 10),
        ("anonymous", {}, [], 10),
        # Pagination — only 1 task, page 2 is empty
        ("owner", {"page": 2, "page_size": 1}, [], 10),
        # Workspace filter
        ("owner", {"workspace": [uuid.UUID(PRIVATE_WORKSPACE)]}, ["Test Data Product Task"], 10),
        ("owner", {"workspace": [uuid.UUID(PUBLIC_WORKSPACE)]}, [], 10),
        # Thing filter
        ("owner", {"thing": [uuid.UUID(PRIVATE_THING)]}, ["Test Data Product Task"], 10),
        ("owner", {"thing": [uuid.UUID(PUBLIC_THING)]}, [], 10),
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
        ("owner", TASK1, "Test Data Product Task", None, None),
        ("editor", TASK1, "Test Data Product Task", None, None),
        ("viewer", TASK1, "Test Data Product Task", None, None),
        ("admin", TASK1, "Test Data Product Task", None, None),
        # API key cannot see private workspace tasks
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


def test_get_data_product_task_includes_latest_run_and_mappings(get_principal):
    result = task_service.get(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
    )
    assert getattr(result, "latest_run_status", None) == "SUCCESS"
    assert result.mappings.count() == 1
    mapping = result.mappings.first()
    assert mapping.transformation_type == "temporal_aggregation"
    assert mapping.input_mappings.count() == 1


@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("admin", None, None),
        # Viewer has no create permission
        ("viewer", PermissionError, "do not have permission"),
        # Unaffiliated: thing found but no workspace permission
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
    with pytest.raises(HttpError) as exc_info:
        task_service.create(
            principal=get_principal("owner"),
            thing=uuid.UUID(NONEXISTENT),
            name="New Task",
        )
    assert "does not exist" in _err(exc_info)


def test_create_data_product_task_with_temporal_aggregation_mapping(get_principal):
    result = task_service.create(
        principal=get_principal("owner"),
        thing=uuid.UUID(PRIVATE_THING),
        name="Aggregation Task",
        mappings=[_temporal_aggregation_mapping()],
    )
    assert result.mappings.count() == 1
    mapping = result.mappings.first()
    assert mapping.transformation_type == "temporal_aggregation"
    assert mapping.aggregation_method == "simple_mean"
    assert mapping.aggregation_period == "daily"
    assert mapping.output_datastream_id == uuid.UUID(OUTPUT_DS)
    assert mapping.input_mappings.count() == 1


def test_create_data_product_task_with_rating_curve_mapping(get_principal):
    result = task_service.create(
        principal=get_principal("owner"),
        thing=uuid.UUID(PRIVATE_THING),
        name="Rating Curve Task",
        mappings=[{
            "transformation_type": "rating_curve",
            "output_datastream_id": uuid.UUID(OUTPUT_DS),
            "rating_curve_id": uuid.UUID(RATING_CURVE),
            "input_mappings": [{"datastream_id": uuid.UUID(INPUT_DS), "variable_name": None}],
        }],
    )
    assert result.mappings.count() == 1
    mapping = result.mappings.first()
    assert mapping.transformation_type == "rating_curve"
    assert mapping.rating_curve_id == uuid.UUID(RATING_CURVE)


def test_create_data_product_task_with_expression_mapping(get_principal):
    # EXP1 has formula "x + y" which requires variables x and y
    result = task_service.create(
        principal=get_principal("owner"),
        thing=uuid.UUID(PRIVATE_THING),
        name="Expression Task",
        mappings=[{
            "transformation_type": "expression",
            "output_datastream_id": uuid.UUID(OUTPUT_DS),
            "expression_id": uuid.UUID(EXPRESSION),
            "input_mappings": [
                {"datastream_id": uuid.UUID(INPUT_DS), "variable_name": "x"},
                {"datastream_id": uuid.UUID(INPUT_DS), "variable_name": "y"},
            ],
        }],
    )
    assert result.mappings.count() == 1
    mapping = result.mappings.first()
    assert mapping.transformation_type == "expression"
    assert mapping.expression_id == uuid.UUID(EXPRESSION)
    assert mapping.input_mappings.count() == 2


def test_create_data_product_task_with_schedule(get_principal):
    result = task_service.create(
        principal=get_principal("owner"),
        thing=uuid.UUID(PRIVATE_THING),
        name="Scheduled Task",
        interval=6,
        interval_period="hours",
        enabled=True,
    )
    assert result.periodic_task is not None
    assert result.periodic_task.interval.every == 6
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


def test_update_data_product_task_replaces_mappings(get_principal):
    result = task_service.update(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        mappings=[_temporal_aggregation_mapping(output_ds=OUTPUT_DS)],
    )
    assert result.mappings.count() == 1
    assert result.mappings.first().output_datastream_id == uuid.UUID(OUTPUT_DS)


def test_update_data_product_task_clears_mappings(get_principal):
    result = task_service.update(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        mappings=[],
    )
    assert result.mappings.count() == 0


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


# --- Mapping validation ---

def test_mapping_validation_rating_curve_requires_rating_curve(get_principal):
    with pytest.raises(ValueError) as exc_info:
        task_service.create(
            principal=get_principal("owner"),
            thing=uuid.UUID(PRIVATE_THING),
            name="Bad Task",
            mappings=[{
                "transformation_type": "rating_curve",
                "output_datastream_id": uuid.UUID(OUTPUT_DS),
                # missing rating_curve_id
            }],
        )
    assert "rating_curve" in str(exc_info.value).lower()


def test_mapping_validation_expression_requires_expression(get_principal):
    with pytest.raises(ValueError) as exc_info:
        task_service.create(
            principal=get_principal("owner"),
            thing=uuid.UUID(PRIVATE_THING),
            name="Bad Task",
            mappings=[{
                "transformation_type": "expression",
                "output_datastream_id": uuid.UUID(OUTPUT_DS),
                # missing expression_id
            }],
        )
    assert "expression" in str(exc_info.value).lower()


def test_mapping_validation_temporal_aggregation_requires_period_and_method(get_principal):
    with pytest.raises(ValueError) as exc_info:
        task_service.create(
            principal=get_principal("owner"),
            thing=uuid.UUID(PRIVATE_THING),
            name="Bad Task",
            mappings=[{
                "transformation_type": "temporal_aggregation",
                "output_datastream_id": uuid.UUID(OUTPUT_DS),
                # missing aggregation_method and aggregation_period
            }],
        )
    assert "aggregation" in str(exc_info.value).lower()


def test_mapping_validation_duplicate_variable_names_rejected(get_principal):
    with pytest.raises(ValueError) as exc_info:
        task_service.create(
            principal=get_principal("owner"),
            thing=uuid.UUID(PRIVATE_THING),
            name="Bad Task",
            mappings=[{
                "transformation_type": "expression",
                "output_datastream_id": uuid.UUID(OUTPUT_DS),
                "expression_id": uuid.UUID(EXPRESSION),
                "input_mappings": [
                    {"datastream_id": uuid.UUID(INPUT_DS), "variable_name": "x"},
                    {"datastream_id": uuid.UUID(INPUT_DS), "variable_name": "x"},
                ],
            }],
        )
    assert "Duplicate" in str(exc_info.value)
