"""
Transformation service tests.

Fixture transformations (both under TASK1, private workspace):
  T_RC  — rating_curve,  output=DS_OUT_RC,  input=DS_IN_RC,  rating_curve=RC1
  T_EXP — expression,    output=DS_OUT_EXP, input=DS_IN_EXP, formula="x * 2.0"

These reference existing datastreams from test_datastreams.yaml so that no
sta.* models need to be added to the shared fixture (which would break STA tests).

Create/update tests that need a free output datastream use the `ds_free` fixture,
which creates a temporary datastream per test within the transaction rollback.

Run method tests create their own datastreams/observations programmatically;
the db fixture rolls everything back after each test.
"""
import uuid
import pytest
import numpy as np
from datetime import datetime, timezone as dt_timezone
from core.types import Unset
from processing.products.models import DataProductTransformation, DataProductTask
from processing.products.services.transformation import DataProductTransformationService, TransformationInput

transformation_service = DataProductTransformationService()

# Tasks
TASK1 = "019c0003-0000-7000-8000-000000000001"  # private workspace, private thing
TASK2 = "019c0003-0000-7000-8000-000000000002"  # public workspace

# Fixture transformations
T_RC  = "019c0005-0000-7000-8000-000000000001"
T_EXP = "019c0005-0000-7000-8000-000000000002"

# Existing datastreams from test_datastreams.yaml (private workspace)
DS_OUT_RC  = "42e08eea-27bb-4ea3-8ced-63acff0f3334"  # T_RC output
DS_IN_RC   = "9f96957b-ee20-4c7b-bf2b-673a0cda3a04"  # T_RC input / T_EXP output
DS_OUT_EXP = "9f96957b-ee20-4c7b-bf2b-673a0cda3a04"  # T_EXP output
DS_IN_EXP  = "42e08eea-27bb-4ea3-8ced-63acff0f3334"  # T_EXP input

RC1 = "019c0002-0000-7000-8000-000000000001"  # linear: (1→2, 2→4)

NONEXISTENT = "00000000-0000-0000-0000-000000000000"


# ============================================================
# Helpers
# ============================================================

def _load(transformation_id, task_id=TASK1):
    return transformation_service.get(
        transformation=uuid.UUID(transformation_id),
        task=uuid.UUID(task_id),
        principal=Unset,
        action="view",
    )


def _make_datastream(thing, sensor, observed_property, processing_level, unit):
    """Create a minimal datastream in the current transaction (rolled back after test)."""
    from core.sta.models import Datastream
    import uuid6
    return Datastream.objects.create(
        pk=uuid6.uuid7(),
        thing=thing,
        sensor=sensor,
        observed_property=observed_property,
        processing_level=processing_level,
        unit=unit,
        name="Run Test DS",
        description="Temporary datastream for run test",
        observation_type="Field Observation",
        result_type="Time Series",
        status="Ongoing",
        sampled_medium="Surface Water",
        value_count=0,
        no_data_value=-9999,
        intended_time_spacing=1,
        intended_time_spacing_unit="hours",
        aggregation_statistic="Continuous",
        time_aggregation_interval=1,
        time_aggregation_interval_unit="hours",
        is_private=True,
        is_visible=True,
    )


def _add_obs(datastream, phenomenon_time, result):
    """Insert a single observation (rolled back after test)."""
    from core.sta.models.observation import Observation
    import uuid6
    return Observation.objects.create(
        pk=uuid6.uuid7(),
        datastream=datastream,
        phenomenon_time=phenomenon_time,
        result=result,
    )


def _set_end_time(datastream, dt):
    """Set phenomenon_end_time on a datastream directly."""
    datastream.phenomenon_end_time = dt
    datastream.save(update_fields=["phenomenon_end_time"])


@pytest.fixture
def ds_free():
    """
    A fresh datastream on TASK1's thing/workspace, created per test and rolled
    back with the surrounding transaction. Avoids the unique output_datastream
    constraint without touching the shared fixture files.
    """
    from core.sta.models import Datastream
    task = DataProductTask.objects.select_related("thing__workspace").get(pk=TASK1)
    ref = Datastream.objects.select_related(
        "sensor", "observed_property", "processing_level", "unit"
    ).get(pk=DS_OUT_RC)
    ds = _make_datastream(
        thing=task.thing,
        sensor=ref.sensor,
        observed_property=ref.observed_property,
        processing_level=ref.processing_level,
        unit=ref.unit,
    )
    return ds.pk


@pytest.fixture
def run_context(get_principal):
    """
    Fixture that provides model instances needed to create run-test datastreams.
    Pulls metadata from one of the existing private-workspace datastreams.
    """
    from core.sta.models import Datastream
    task = DataProductTask.objects.select_related("thing__workspace").get(pk=TASK1)
    ref_ds = Datastream.objects.select_related(
        "sensor", "observed_property", "processing_level", "unit"
    ).get(pk=DS_OUT_RC)
    return {
        "thing": task.thing,
        "sensor": ref_ds.sensor,
        "observed_property": ref_ds.observed_property,
        "processing_level": ref_ds.processing_level,
        "unit": ref_ds.unit,
        "owner": get_principal("owner"),
    }


# ============================================================
# get_collection
# ============================================================

@pytest.mark.parametrize(
    "principal, task, expected_count, error, error_fragment",
    [
        ("owner", TASK1, 2, None, None),
        ("editor", TASK1, 2, None, None),
        ("viewer", TASK1, 2, None, None),
        ("admin", TASK1, 2, None, None),
        ("apikey", TASK1, None, LookupError, "does not exist"),
        ("unaffiliated", TASK1, None, LookupError, "does not exist"),
        ("owner", TASK2, 0, None, None),
    ],
)
def test_list_transformations(get_principal, principal, task, expected_count, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            transformation_service.get_collection(
                task=uuid.UUID(task),
                principal=get_principal(principal),
            )
        assert error_fragment in str(exc_info.value)
    else:
        count, _ = transformation_service.get_collection(
            task=uuid.UUID(task),
            principal=get_principal(principal),
        )
        assert count == expected_count


def test_list_transformations_filter_by_type(get_principal):
    count, qs = transformation_service.get_collection(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        transformation_type=["rating_curve"],
    )
    assert count == 1
    assert list(qs)[0].transformation_type == "rating_curve"


def test_list_transformations_filter_by_output_datastream(get_principal):
    count, qs = transformation_service.get_collection(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        output_datastream=[uuid.UUID(DS_OUT_RC)],
    )
    assert count == 1
    assert str(list(qs)[0].pk) == T_RC


def test_list_transformations_filter_by_input_datastream(get_principal):
    count, _ = transformation_service.get_collection(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        input_datastream=[uuid.UUID(DS_IN_RC)],
    )
    assert count == 1


# ============================================================
# get
# ============================================================

@pytest.mark.parametrize(
    "principal, transformation, error, error_fragment",
    [
        ("owner", T_RC, None, None),
        ("editor", T_RC, None, None),
        ("viewer", T_RC, None, None),
        ("admin", T_RC, None, None),
        ("apikey", T_RC, LookupError, "does not exist"),
        ("unaffiliated", T_RC, LookupError, "does not exist"),
        ("owner", NONEXISTENT, LookupError, "does not exist"),
    ],
)
def test_get_transformation(get_principal, principal, transformation, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            transformation_service.get(
                transformation=uuid.UUID(transformation),
                task=uuid.UUID(TASK1),
                principal=get_principal(principal),
                action="view",
            )
        assert error_fragment in str(exc_info.value)
    else:
        result = transformation_service.get(
            transformation=uuid.UUID(transformation),
            task=uuid.UUID(TASK1),
            principal=get_principal(principal),
            action="view",
        )
        assert str(result.pk) == transformation


def test_get_transformation_includes_related_data(get_principal):
    result = _load(T_RC)
    assert result.transformation_type == "rating_curve"
    assert result.rating_curve is not None
    assert str(result.rating_curve.pk) == RC1
    assert result.input_datastreams.count() == 1
    assert str(result.input_datastreams.first().datastream_id) == DS_IN_RC


# ============================================================
# create
# ============================================================

@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("admin", None, None),
        ("viewer", PermissionError, "do not have permission"),
        ("apikey", LookupError, "does not exist"),
        ("unaffiliated", LookupError, "does not exist"),
    ],
)
def test_create_expression_transformation_permissions(get_principal, ds_free, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            transformation_service.create(
                task=uuid.UUID(TASK1),
                principal=get_principal(principal),
                transformation_type="expression",
                output_datastream=ds_free,
                formula="x * 3.0",
                input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC), variable_name="x")],
            )
        assert error_fragment in str(exc_info.value)
    else:
        result = transformation_service.create(
            task=uuid.UUID(TASK1),
            principal=get_principal(principal),
            transformation_type="expression",
            output_datastream=ds_free,
            formula="x * 3.0",
            input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC), variable_name="x")],
        )
        assert result.transformation_type == "expression"
        assert result.formula == "x * 3.0"


def test_create_rating_curve_transformation(get_principal, ds_free):
    result = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        transformation_type="rating_curve",
        output_datastream=ds_free,
        rating_curve=uuid.UUID(RC1),
        input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC))],
    )
    assert result.transformation_type == "rating_curve"
    assert str(result.rating_curve_id) == RC1


def test_create_aggregation_transformation(get_principal, ds_free):
    result = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        transformation_type="aggregation",
        output_datastream=ds_free,
        aggregation_method="mean",
        output_interval_units="hours",
        output_interval=1,
        input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC))],
    )
    assert result.transformation_type == "aggregation"
    assert result.aggregation_method == "mean"


def test_create_composite_expression_transformation(get_principal, ds_free):
    result = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        transformation_type="composite_expression",
        output_datastream=ds_free,
        formula="a + b",
        output_interval_units="hours",
        output_interval=1,
        input_datastreams=[
            TransformationInput(datastream=uuid.UUID(DS_IN_RC), variable_name="a"),
            TransformationInput(datastream=uuid.UUID(DS_OUT_RC), variable_name="b"),
        ],
    )
    assert result.transformation_type == "composite_expression"
    assert result.input_datastreams.count() == 2


# --- Validation ---

def test_create_rating_curve_requires_rating_curve(get_principal, ds_free):
    with pytest.raises(ValueError, match="rating_curve is required"):
        transformation_service.create(
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
            transformation_type="rating_curve",
            output_datastream=ds_free,
            input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC))],
        )


def test_create_expression_requires_formula(get_principal, ds_free):
    with pytest.raises(ValueError, match="formula"):
        transformation_service.create(
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
            transformation_type="expression",
            output_datastream=ds_free,
            input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC), variable_name="x")],
        )


def test_create_aggregation_requires_method_and_interval(get_principal, ds_free):
    with pytest.raises(ValueError):
        transformation_service.create(
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
            transformation_type="aggregation",
            output_datastream=ds_free,
            input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC))],
        )


def test_create_duplicate_variable_names_rejected(get_principal, ds_free):
    with pytest.raises(ValueError, match="Duplicate"):
        transformation_service.create(
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
            transformation_type="composite_expression",
            output_datastream=ds_free,
            formula="x + x",
            output_interval_units="hours",
            output_interval=1,
            input_datastreams=[
                TransformationInput(datastream=uuid.UUID(DS_IN_RC), variable_name="x"),
                TransformationInput(datastream=uuid.UUID(DS_OUT_RC), variable_name="x"),
            ],
        )


# --- Timezone validation ---

def test_create_aggregation_with_iana_timezone(get_principal, ds_free):
    result = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        transformation_type="aggregation",
        output_datastream=ds_free,
        aggregation_method="mean",
        output_interval_units="hours",
        output_interval=1,
        timezone_type="iana",
        timezone="America/Denver",
        input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC))],
    )
    assert result.timezone_type == "iana"
    assert result.timezone == "America/Denver"


def test_create_aggregation_with_utc_timezone(get_principal, ds_free):
    result = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        transformation_type="aggregation",
        output_datastream=ds_free,
        aggregation_method="mean",
        output_interval_units="hours",
        output_interval=1,
        timezone_type="utc",
        input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC))],
    )
    assert result.timezone_type == "utc"


def test_create_aggregation_with_offset_timezone(get_principal, ds_free):
    result = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        transformation_type="aggregation",
        output_datastream=ds_free,
        aggregation_method="mean",
        output_interval_units="hours",
        output_interval=1,
        timezone_type="offset",
        timezone="-07:00",
        input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC))],
    )
    assert result.timezone_type == "offset"
    assert result.timezone == "-07:00"


def test_create_aggregation_invalid_iana_timezone(get_principal, ds_free):
    with pytest.raises(ValueError, match="Unknown timezone"):
        transformation_service.create(
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
            transformation_type="aggregation",
            output_datastream=ds_free,
            aggregation_method="mean",
            output_interval_units="hours",
            output_interval=1,
            timezone_type="iana",
            timezone="Not/ATimezone",
            input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC))],
        )


def test_create_aggregation_invalid_offset_timezone(get_principal, ds_free):
    with pytest.raises(ValueError, match="Unknown timezone"):
        transformation_service.create(
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
            transformation_type="aggregation",
            output_datastream=ds_free,
            aggregation_method="mean",
            output_interval_units="hours",
            output_interval=1,
            timezone_type="offset",
            timezone="bad_offset",
            input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC))],
        )


def test_create_aggregation_timezone_without_timezone_type(get_principal, ds_free):
    with pytest.raises(ValueError, match="timezone_type is required"):
        transformation_service.create(
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
            transformation_type="aggregation",
            output_datastream=ds_free,
            aggregation_method="mean",
            output_interval_units="hours",
            output_interval=1,
            timezone="America/Denver",
            input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC))],
        )


def test_create_aggregation_utc_with_timezone_value_rejected(get_principal, ds_free):
    with pytest.raises(ValueError, match="timezone must not be set"):
        transformation_service.create(
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
            transformation_type="aggregation",
            output_datastream=ds_free,
            aggregation_method="mean",
            output_interval_units="hours",
            output_interval=1,
            timezone_type="utc",
            timezone="America/Denver",
            input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC))],
        )


# ============================================================
# update
# ============================================================

@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("admin", None, None),
        ("viewer", PermissionError, "do not have permission"),
        ("apikey", LookupError, "does not exist"),
        ("unaffiliated", LookupError, "does not exist"),
    ],
)
def test_update_transformation_permissions(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            transformation_service.update(
                transformation=uuid.UUID(T_EXP),
                task=uuid.UUID(TASK1),
                principal=get_principal(principal),
                formula="x * 3.0",
            )
        assert error_fragment in str(exc_info.value)
    else:
        result = transformation_service.update(
            transformation=uuid.UUID(T_EXP),
            task=uuid.UUID(TASK1),
            principal=get_principal(principal),
            formula="x * 3.0",
        )
        assert result.formula == "x * 3.0"


def test_update_transformation_replaces_inputs(get_principal):
    result = transformation_service.update(
        transformation=uuid.UUID(T_EXP),
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        input_datastreams=[{"datastream": uuid.UUID(DS_IN_RC), "variable_name": "x"}],
    )
    assert result.input_datastreams.count() == 1
    assert str(result.input_datastreams.first().datastream_id) == DS_IN_RC


def test_update_transformation_nonexistent(get_principal):
    with pytest.raises(LookupError, match="does not exist"):
        transformation_service.update(
            transformation=uuid.UUID(NONEXISTENT),
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
            formula="x",
        )


def test_update_aggregation_partial_does_not_fail_validation(get_principal, ds_free):
    """Updating a single field on an aggregation should not fail due to unrelated None fields."""
    created = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        transformation_type="aggregation",
        output_datastream=ds_free,
        aggregation_method="mean",
        output_interval_units="hours",
        output_interval=1,
        input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC))],
    )
    result = transformation_service.update(
        transformation=created.pk,
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        aggregation_method="sum",
    )
    assert result.aggregation_method == "sum"


def test_update_aggregation_timezone(get_principal, ds_free):
    created = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        transformation_type="aggregation",
        output_datastream=ds_free,
        aggregation_method="mean",
        output_interval_units="hours",
        output_interval=1,
        input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC))],
    )
    result = transformation_service.update(
        transformation=created.pk,
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        timezone_type="iana",
        timezone="America/Denver",
    )
    assert result.timezone_type == "iana"
    assert result.timezone == "America/Denver"


def test_update_aggregation_invalid_timezone_rejected(get_principal, ds_free):
    created = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        transformation_type="aggregation",
        output_datastream=ds_free,
        aggregation_method="mean",
        output_interval_units="hours",
        output_interval=1,
        input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC))],
    )
    with pytest.raises(ValueError, match="Unknown timezone"):
        transformation_service.update(
            transformation=created.pk,
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
            timezone_type="iana",
            timezone="Not/ATimezone",
        )


# ============================================================
# delete
# ============================================================

@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("admin", None, None),
        ("viewer", PermissionError, "do not have permission"),
        ("apikey", LookupError, "does not exist"),
        ("unaffiliated", LookupError, "does not exist"),
    ],
)
def test_delete_transformation_permissions(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            transformation_service.delete(
                transformation=uuid.UUID(T_EXP),
                task=uuid.UUID(TASK1),
                principal=get_principal(principal),
            )
        assert error_fragment in str(exc_info.value)
    else:
        transformation_service.delete(
            transformation=uuid.UUID(T_EXP),
            task=uuid.UUID(TASK1),
            principal=get_principal(principal),
        )
        assert not DataProductTransformation.objects.filter(pk=uuid.UUID(T_EXP)).exists()


def test_delete_transformation_nonexistent(get_principal):
    with pytest.raises(LookupError, match="does not exist"):
        transformation_service.delete(
            transformation=uuid.UUID(NONEXISTENT),
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
        )


# ============================================================
# Run methods
#
# Each test creates its own datastreams and observations within
# the db transaction, which is rolled back after the test.
# ============================================================

def test_run_expression(run_context):
    """formula "x * 2.0", inputs [2.0, 3.0] → outputs [4.0, 6.0]."""
    ctx = run_context
    ds_in  = _make_datastream(**{k: ctx[k] for k in ("thing", "sensor", "observed_property", "processing_level", "unit")})
    ds_out = _make_datastream(**{k: ctx[k] for k in ("thing", "sensor", "observed_property", "processing_level", "unit")})

    t1 = datetime(2025, 2, 10, 8, 0, tzinfo=dt_timezone.utc)
    t2 = datetime(2025, 2, 10, 9, 0, tzinfo=dt_timezone.utc)
    _add_obs(ds_in, t1, 2.0)
    _add_obs(ds_in, t2, 3.0)
    _set_end_time(ds_in, t2)

    t = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=ctx["owner"],
        transformation_type="expression",
        output_datastream=ds_out.pk,
        formula="x * 2.0",
        input_datastreams=[TransformationInput(datastream=ds_in.pk, variable_name="x")],
    )
    loaded = transformation_service.run(t)
    assert loaded == 2

    from core.sta.models.observation import Observation
    results = sorted(Observation.objects.filter(datastream=ds_out).values_list("result", flat=True))
    np.testing.assert_allclose(results, [4.0, 6.0])


def test_run_expression_idempotent(run_context):
    """Running a second time after output is populated loads 0."""
    ctx = run_context
    ds_in  = _make_datastream(**{k: ctx[k] for k in ("thing", "sensor", "observed_property", "processing_level", "unit")})
    ds_out = _make_datastream(**{k: ctx[k] for k in ("thing", "sensor", "observed_property", "processing_level", "unit")})

    t1 = datetime(2025, 2, 10, 8, 0, tzinfo=dt_timezone.utc)
    _add_obs(ds_in, t1, 2.0)
    _set_end_time(ds_in, t1)

    t = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=ctx["owner"],
        transformation_type="expression",
        output_datastream=ds_out.pk,
        formula="x * 2.0",
        input_datastreams=[TransformationInput(datastream=ds_in.pk, variable_name="x")],
    )
    transformation_service.run(t)
    t = _load(str(t.pk))   # reload to pick up updated phenomenon_end_time
    loaded = transformation_service.run(t)
    assert loaded == 0


def test_run_rating_curve(run_context):
    """RC1 linear (1→2, 2→4), inputs [1.0, 2.0] → outputs [2.0, 4.0]."""
    ctx = run_context
    ds_in  = _make_datastream(**{k: ctx[k] for k in ("thing", "sensor", "observed_property", "processing_level", "unit")})
    ds_out = _make_datastream(**{k: ctx[k] for k in ("thing", "sensor", "observed_property", "processing_level", "unit")})

    t1 = datetime(2025, 2, 10, 8, 0, tzinfo=dt_timezone.utc)
    t2 = datetime(2025, 2, 10, 9, 0, tzinfo=dt_timezone.utc)
    _add_obs(ds_in, t1, 1.0)
    _add_obs(ds_in, t2, 2.0)
    _set_end_time(ds_in, t2)

    t = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=ctx["owner"],
        transformation_type="rating_curve",
        output_datastream=ds_out.pk,
        rating_curve=uuid.UUID(RC1),
        input_datastreams=[TransformationInput(datastream=ds_in.pk)],
    )
    loaded = transformation_service.run(t)
    assert loaded == 2

    from core.sta.models.observation import Observation
    results = sorted(Observation.objects.filter(datastream=ds_out).values_list("result", flat=True))
    np.testing.assert_allclose(results, [2.0, 4.0])


def test_run_composite_expression(run_context):
    """
    formula "a + b", 1-hour grid (UTC).
    ds_a: 08:00→2.0, 09:00→4.0
    ds_b: 08:00→1.0, 09:00→2.0
    Grid points at 08:00 and 09:00 UTC → a+b = [3.0, 6.0].
    """
    ctx = run_context
    kwargs = {k: ctx[k] for k in ("thing", "sensor", "observed_property", "processing_level", "unit")}
    ds_a   = _make_datastream(**kwargs)
    ds_b   = _make_datastream(**kwargs)
    ds_out = _make_datastream(**kwargs)

    t1 = datetime(2025, 2, 10, 8, 0, tzinfo=dt_timezone.utc)
    t2 = datetime(2025, 2, 10, 9, 0, tzinfo=dt_timezone.utc)
    for ds, vals in [(ds_a, (2.0, 4.0)), (ds_b, (1.0, 2.0))]:
        _add_obs(ds, t1, vals[0])
        _add_obs(ds, t2, vals[1])
        _set_end_time(ds, t2)

    t = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=ctx["owner"],
        transformation_type="composite_expression",
        output_datastream=ds_out.pk,
        formula="a + b",
        output_interval_units="hours",
        output_interval=1,
        input_datastreams=[
            TransformationInput(datastream=ds_a.pk, variable_name="a"),
            TransformationInput(datastream=ds_b.pk, variable_name="b"),
        ],
    )
    loaded = transformation_service.run(t)
    assert loaded == 2

    from core.sta.models.observation import Observation
    results = sorted(Observation.objects.filter(datastream=ds_out).values_list("result", flat=True))
    np.testing.assert_allclose(results, [3.0, 6.0])


def test_run_aggregation(run_context):
    """
    simple_mean, 1-hour UTC buckets.
    [07:00, 08:00): mean(2.0, 4.0) = 3.0
    [08:00, 09:00): mean(1.0, 3.0) = 2.0
    phenomenon_end_time = 09:00 UTC → both buckets complete.
    """
    ctx = run_context
    kwargs = {k: ctx[k] for k in ("thing", "sensor", "observed_property", "processing_level", "unit")}
    ds_in  = _make_datastream(**kwargs)
    ds_out = _make_datastream(**kwargs)

    end = datetime(2025, 2, 10, 9, 0, tzinfo=dt_timezone.utc)
    for dt, val in [
        (datetime(2025, 2, 10, 7,  0, tzinfo=dt_timezone.utc), 2.0),
        (datetime(2025, 2, 10, 7, 30, tzinfo=dt_timezone.utc), 4.0),
        (datetime(2025, 2, 10, 8,  0, tzinfo=dt_timezone.utc), 1.0),
        (datetime(2025, 2, 10, 8, 30, tzinfo=dt_timezone.utc), 3.0),
    ]:
        _add_obs(ds_in, dt, val)
    _set_end_time(ds_in, end)

    t = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=ctx["owner"],
        transformation_type="aggregation",
        output_datastream=ds_out.pk,
        aggregation_method="mean",
        output_interval_units="hours",
        output_interval=1,
        input_datastreams=[TransformationInput(datastream=ds_in.pk)],
    )
    loaded = transformation_service.run(t)
    assert loaded == 2

    from core.sta.models.observation import Observation
    results = sorted(Observation.objects.filter(datastream=ds_out).values_list("result", flat=True))
    np.testing.assert_allclose(results, [2.0, 3.0])
