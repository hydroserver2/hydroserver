"""
Transformation service tests.

Fixture transformations (both under TASK1, private workspace):
  T_RC  — rating_curve,  output=DS_OUT_RC,  input=DS_IN_RC,  rating_curve=RC1
  T_EXP — derivation,    output=DS_OUT_EXP, input=DS_IN_EXP, formula="x * 2.0"

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
from datetime import datetime, timedelta, timezone as dt_timezone
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
def test_create_derivation_transformation_permissions(get_principal, ds_free, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            transformation_service.create(
                task=uuid.UUID(TASK1),
                principal=get_principal(principal),
                transformation_type="derivation",
                output_datastream=ds_free,
                formula="x * 3.0",
                input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC), variable_name="x")],
            )
        assert error_fragment in str(exc_info.value)
    else:
        result = transformation_service.create(
            task=uuid.UUID(TASK1),
            principal=get_principal(principal),
            transformation_type="derivation",
            output_datastream=ds_free,
            formula="x * 3.0",
            input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC), variable_name="x")],
        )
        assert result.transformation_type == "derivation"
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


def test_create_aggregation_transformation_time_weighted_mean(get_principal, ds_free):
    result = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        transformation_type="aggregation",
        output_datastream=ds_free,
        aggregation_method="time_weighted_mean",
        output_interval_units="hours",
        output_interval=1,
        input_datastreams=[TransformationInput(datastream=uuid.UUID(DS_IN_RC))],
    )
    assert result.transformation_type == "aggregation"
    assert result.aggregation_method == "time_weighted_mean"


def test_create_derivation_transformation_with_multiple_inputs(get_principal, ds_free):
    result = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        transformation_type="derivation",
        output_datastream=ds_free,
        formula="a + b",
        input_datastreams=[
            TransformationInput(datastream=uuid.UUID(DS_IN_RC), variable_name="a"),
            TransformationInput(datastream=uuid.UUID(DS_OUT_RC), variable_name="b"),
        ],
    )
    assert result.transformation_type == "derivation"
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


def test_create_derivation_requires_formula(get_principal, ds_free):
    with pytest.raises(ValueError, match="formula"):
        transformation_service.create(
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
            transformation_type="derivation",
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
            transformation_type="derivation",
            output_datastream=ds_free,
            formula="x + x",
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

def test_run_derivation(run_context):
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
        transformation_type="derivation",
        output_datastream=ds_out.pk,
        formula="x * 2.0",
        input_datastreams=[TransformationInput(datastream=ds_in.pk, variable_name="x")],
    )
    loaded = transformation_service.run(t)
    assert loaded == 2

    from core.sta.models.observation import Observation
    results = sorted(Observation.objects.filter(datastream=ds_out).values_list("result", flat=True))
    np.testing.assert_allclose(results, [4.0, 6.0])


def test_run_derivation_idempotent(run_context):
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
        transformation_type="derivation",
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


def test_run_derivation_with_multiple_inputs(run_context):
    """
    formula "a + b", inputs matched on exact timestamp.
    ds_a: 08:00→2.0, 09:00→4.0
    ds_b: 08:00→1.0, 09:00→2.0
    Both inputs agree at 08:00 and 09:00 → a+b = [3.0, 6.0].
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
        transformation_type="derivation",
        output_datastream=ds_out.pk,
        formula="a + b",
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


def test_run_derivation_stops_at_first_misaligned_timestamp(run_context):
    """
    formula "a + b". ds_b is missing the 09:00 reading ds_a has, so the run
    should load only the 08:00 row and stop before the misaligned one.
    """
    ctx = run_context
    kwargs = {k: ctx[k] for k in ("thing", "sensor", "observed_property", "processing_level", "unit")}
    ds_a   = _make_datastream(**kwargs)
    ds_b   = _make_datastream(**kwargs)
    ds_out = _make_datastream(**kwargs)

    t1 = datetime(2025, 2, 10, 8, 0, tzinfo=dt_timezone.utc)
    t2 = datetime(2025, 2, 10, 9, 0, tzinfo=dt_timezone.utc)
    _add_obs(ds_a, t1, 2.0)
    _add_obs(ds_a, t2, 4.0)
    _set_end_time(ds_a, t2)
    _add_obs(ds_b, t1, 1.0)
    _set_end_time(ds_b, t2)

    t = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=ctx["owner"],
        transformation_type="derivation",
        output_datastream=ds_out.pk,
        formula="a + b",
        input_datastreams=[
            TransformationInput(datastream=ds_a.pk, variable_name="a"),
            TransformationInput(datastream=ds_b.pk, variable_name="b"),
        ],
    )
    loaded = transformation_service.run(t)
    assert loaded == 1

    from core.sta.models.observation import Observation
    out_obs = list(Observation.objects.filter(datastream=ds_out))
    assert len(out_obs) == 1
    np.testing.assert_allclose(out_obs[0].result, 3.0)


def _run_offset_derivation(ctx, obs_a, obs_b, stop_on_gaps=Unset):
    """
    Create inputs ds_a/ds_b from {hour: value} dicts (2025-02-10 UTC), derive
    "a + b" into an empty output, run once, and return (loaded, transformation,
    ds_a, ds_b, ds_out).
    """
    kwargs = {k: ctx[k] for k in ("thing", "sensor", "observed_property", "processing_level", "unit")}
    ds_a   = _make_datastream(**kwargs)
    ds_b   = _make_datastream(**kwargs)
    ds_out = _make_datastream(**kwargs)

    for ds, obs in [(ds_a, obs_a), (ds_b, obs_b)]:
        for hour, value in obs.items():
            _add_obs(ds, datetime(2025, 2, 10, hour, 0, tzinfo=dt_timezone.utc), value)
        _set_end_time(ds, datetime(2025, 2, 10, max(obs), 0, tzinfo=dt_timezone.utc))

    t = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=ctx["owner"],
        transformation_type="derivation",
        output_datastream=ds_out.pk,
        formula="a + b",
        stop_on_gaps=stop_on_gaps,
        input_datastreams=[
            TransformationInput(datastream=ds_a.pk, variable_name="a"),
            TransformationInput(datastream=ds_b.pk, variable_name="b"),
        ],
    )
    loaded = transformation_service.run(t)
    return loaded, t, ds_a, ds_b, ds_out


def _append_obs(t, ds, obs):
    """Add {hour: value} readings to ds, advance its end time, and reload t."""
    for hour, value in obs.items():
        _add_obs(ds, datetime(2025, 2, 10, hour, 0, tzinfo=dt_timezone.utc), value)
    _set_end_time(ds, datetime(2025, 2, 10, max(obs), 0, tzinfo=dt_timezone.utc))
    return _load(str(t.pk))


def _output_results(ds_out):
    from core.sta.models.observation import Observation
    return list(
        Observation.objects.filter(datastream=ds_out)
        .order_by("phenomenon_time")
        .values_list("phenomenon_time__hour", "result")
    )


def test_run_derivation_initial_load_starts_at_latest_input_start(run_context):
    """
    ds_a starts at 08:00, ds_b at 10:00, aligned from there. The initial load
    should start at 10:00 rather than stopping at ds_a's leading readings.
    """
    loaded, _, _, _, ds_out = _run_offset_derivation(
        run_context,
        obs_a={8: 1.0, 9: 2.0, 10: 3.0, 11: 4.0},
        obs_b={10: 10.0, 11: 20.0},
    )
    assert loaded == 2
    assert _output_results(ds_out) == [(10, 13.0), (11, 24.0)]


def test_run_derivation_offset_start_then_incremental_run(run_context):
    """After an offset-start initial load, the next run appends normally."""
    ctx = run_context
    loaded, t, ds_a, ds_b, ds_out = _run_offset_derivation(
        ctx,
        obs_a={8: 1.0, 9: 2.0, 10: 3.0},
        obs_b={9: 10.0, 10: 20.0},
    )
    assert loaded == 2

    t12 = datetime(2025, 2, 10, 12, 0, tzinfo=dt_timezone.utc)
    for ds, value in [(ds_a, 5.0), (ds_b, 50.0)]:
        _add_obs(ds, datetime(2025, 2, 10, 11, 0, tzinfo=dt_timezone.utc), value - 1)
        _add_obs(ds, t12, value)
        _set_end_time(ds, t12)

    t = _load(str(t.pk))   # reload to pick up updated phenomenon_end_time
    loaded = transformation_service.run(t)
    assert loaded == 2
    assert _output_results(ds_out) == [(9, 12.0), (10, 23.0), (11, 53.0), (12, 55.0)]


def test_run_derivation_offset_start_stops_at_divergence(run_context):
    """Trimming to the latest start doesn't bypass divergence after that point."""
    loaded, _, _, _, ds_out = _run_offset_derivation(
        run_context,
        obs_a={8: 1.0, 10: 3.0, 11: 4.0, 12: 5.0},
        obs_b={10: 10.0, 12: 30.0},
        stop_on_gaps=True,
    )
    assert loaded == 1
    assert _output_results(ds_out) == [(10, 13.0)]


def test_run_derivation_stop_on_gaps_true_waits_at_gap(run_context):
    """With the toggle on, a gap holds the output back on every run until it's filled."""
    loaded, t, ds_a, ds_b, ds_out = _run_offset_derivation(
        run_context,
        obs_a={8: 1.0, 9: 2.0, 10: 3.0},
        obs_b={8: 10.0, 10: 30.0},
        stop_on_gaps=True,
    )
    assert loaded == 1

    t = _append_obs(t, ds_a, {11: 4.0})
    t = _append_obs(t, ds_b, {11: 40.0})
    assert transformation_service.run(t) == 0

    _add_obs(ds_b, datetime(2025, 2, 10, 9, 0, tzinfo=dt_timezone.utc), 20.0)
    assert transformation_service.run(t) == 3
    assert _output_results(ds_out) == [(8, 11.0), (9, 22.0), (10, 33.0), (11, 44.0)]


def test_run_derivation_skips_gaps_when_stop_on_gaps_false(run_context):
    """With the toggle off, timestamps not shared by both inputs are skipped."""
    loaded, t, ds_a, ds_b, ds_out = _run_offset_derivation(
        run_context,
        obs_a={8: 1.0, 9: 2.0, 10: 3.0, 11: 4.0},
        obs_b={8: 10.0, 10: 30.0, 11: 40.0},
        stop_on_gaps=False,
    )
    assert loaded == 3
    assert _output_results(ds_out) == [(8, 11.0), (10, 33.0), (11, 44.0)]

    # The incremental run picks up after the last output and skips new gaps too.
    t = _append_obs(t, ds_a, {13: 6.0, 14: 7.0})
    t = _append_obs(t, ds_b, {12: 50.0, 14: 70.0})
    assert transformation_service.run(t) == 1
    assert _output_results(ds_out) == [(8, 11.0), (10, 33.0), (11, 44.0), (14, 77.0)]


def test_run_derivation_lagging_input_holds_output_back(run_context):
    """
    ds_a falls behind ds_b. Output stops at ds_a's last reading rather than
    skipping ds_b's newer readings, then catches up once ds_a reports again,
    skipping the hour ds_a never reported.
    """
    loaded, t, ds_a, ds_b, ds_out = _run_offset_derivation(
        run_context,
        obs_a={8: 1.0, 9: 2.0},
        obs_b={8: 10.0, 9: 20.0, 10: 30.0, 11: 40.0},
        stop_on_gaps=False,
    )
    assert loaded == 2
    assert _output_results(ds_out) == [(8, 11.0), (9, 22.0)]

    t = _append_obs(t, ds_a, {11: 4.0})
    assert transformation_service.run(t) == 1
    assert _output_results(ds_out) == [(8, 11.0), (9, 22.0), (11, 44.0)]


def test_run_derivation_no_data_values_fill_output_and_continue(run_context):
    """
    Each input is checked against its own no-data value, and those rows get the
    output's no-data value. The run continues with the toggle at its default (off).
    """
    ctx = run_context
    kwargs = {k: ctx[k] for k in ("thing", "sensor", "observed_property", "processing_level", "unit")}
    ds_a   = _make_datastream(**kwargs)
    ds_b   = _make_datastream(**kwargs)
    ds_out = _make_datastream(**kwargs)
    for ds, ndv in [(ds_a, -9999), (ds_b, -1), (ds_out, -555)]:
        ds.no_data_value = ndv
        ds.save(update_fields=["no_data_value"])

    # 09:00: ds_a at its no-data value. 10:00: ds_b at its no-data value.
    # 11:00: each holds the *other's* no-data value, which is real data.
    for ds, values in [(ds_a, (1.0, -9999.0, 3.0, -1.0)), (ds_b, (10.0, 20.0, -1.0, -9999.0))]:
        for hour, value in zip((8, 9, 10, 11), values):
            _add_obs(ds, datetime(2025, 2, 10, hour, 0, tzinfo=dt_timezone.utc), value)
        _set_end_time(ds, datetime(2025, 2, 10, 11, 0, tzinfo=dt_timezone.utc))

    t = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=ctx["owner"],
        transformation_type="derivation",
        output_datastream=ds_out.pk,
        formula="a + b",
        input_datastreams=[
            TransformationInput(datastream=ds_a.pk, variable_name="a"),
            TransformationInput(datastream=ds_b.pk, variable_name="b"),
        ],
    )
    assert t.stop_on_gaps is False
    assert transformation_service.run(t) == 4
    assert _output_results(ds_out) == [(8, 11.0), (9, -555.0), (10, -555.0), (11, -10000.0)]


def test_run_derivation_latest_start_not_shared_loads_nothing(run_context):
    """
    ds_a starts at 02:00 and ds_b at 01:00, but ds_b has no 02:00 reading; the
    first shared timestamp is 03:00. The latest start doesn't align, so nothing loads.
    """
    loaded, _, _, _, ds_out = _run_offset_derivation(
        run_context,
        obs_a={2: 1.0, 3: 2.0},
        obs_b={1: 10.0, 3: 20.0},
        stop_on_gaps=True,
    )
    assert loaded == 0
    assert _output_results(ds_out) == []


def test_run_derivation_non_overlapping_inputs_load_nothing(run_context):
    """ds_b starts after ds_a's last reading, so there's nothing to derive yet."""
    loaded, _, _, _, ds_out = _run_offset_derivation(
        run_context,
        obs_a={8: 1.0, 9: 2.0},
        obs_b={10: 10.0, 11: 20.0},
    )
    assert loaded == 0
    assert _output_results(ds_out) == []


def test_run_aggregation_local_timezone_watermark(run_context):
    """
    Regression test for bug_014: watermark must advance to local-midnight boundaries,
    not UTC-midnight boundaries, so the second run doesn't re-emit the last bucket.

    Setup: daily aggregation in America/Denver (UTC-7), no DST (January dates).
      Local day 2025-01-01 Denver = 2025-01-01T07:00Z → 2025-01-02T07:00Z UTC.
      Local day 2025-01-02 Denver = 2025-01-02T07:00Z → 2025-01-03T07:00Z UTC.

    Run 1: input covers local day 1 only.
      → 1 bucket emitted, labeled 2025-01-01T07:00Z, mean = 3.0.
      → output phenomenon_end_time = 2025-01-01T07:00Z.

    Run 2: input extended to cover local day 2.
      → watermark (fixed): start = 2025-01-02T07:00Z (next local midnight).
      → watermark (buggy): start = 2025-01-02T00:00Z (UTC midnight, inside local day 1).
      → buggy watermark re-fetches local day 1 tail, re-emits 2025-01-01T07:00Z → 400.
      → fixed watermark emits exactly 1 new bucket for local day 2, mean = 7.0.
    """
    from core.sta.models.observation import Observation

    ctx = run_context
    kwargs = {k: ctx[k] for k in ("thing", "sensor", "observed_property", "processing_level", "unit")}
    ds_in  = _make_datastream(**kwargs)
    ds_out = _make_datastream(**kwargs)

    # Local day 1 observations (all within 2025-01-01T07:00Z – 2025-01-02T07:00Z)
    day1_obs = [
        (datetime(2025, 1, 1, 10, 0, tzinfo=dt_timezone.utc), 2.0),  # 03:00 Denver
        (datetime(2025, 1, 1, 18, 0, tzinfo=dt_timezone.utc), 4.0),  # 11:00 Denver
    ]
    for dt, val in day1_obs:
        _add_obs(ds_in, dt, val)
    # Set end to local day 2 midnight so the day 1 bucket is not discarded as incomplete
    _set_end_time(ds_in, datetime(2025, 1, 2, 7, 0, tzinfo=dt_timezone.utc))

    t = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=ctx["owner"],
        transformation_type="aggregation",
        output_datastream=ds_out.pk,
        aggregation_method="mean",
        output_interval_units="days",
        output_interval=1,
        timezone_type="iana",
        timezone="America/Denver",
        input_datastreams=[TransformationInput(datastream=ds_in.pk)],
    )

    count1 = transformation_service.run(t)
    assert count1 == 1
    out_obs = list(Observation.objects.filter(datastream=ds_out).order_by("phenomenon_time"))
    assert len(out_obs) == 1
    assert out_obs[0].phenomenon_time == datetime(2025, 1, 1, 7, 0, tzinfo=dt_timezone.utc)
    np.testing.assert_allclose(out_obs[0].result, 3.0)

    # Extend input with local day 2 observations (2025-01-02T07:00Z – 2025-01-03T07:00Z)
    day2_obs = [
        (datetime(2025, 1, 2, 10, 0, tzinfo=dt_timezone.utc), 6.0),  # 03:00 Denver Jan 2
        (datetime(2025, 1, 2, 18, 0, tzinfo=dt_timezone.utc), 8.0),  # 11:00 Denver Jan 2
    ]
    for dt, val in day2_obs:
        _add_obs(ds_in, dt, val)
    _set_end_time(ds_in, datetime(2025, 1, 3, 7, 0, tzinfo=dt_timezone.utc))

    t.refresh_from_db()
    count2 = transformation_service.run(t)
    assert count2 == 1
    out_obs = list(Observation.objects.filter(datastream=ds_out).order_by("phenomenon_time"))
    assert len(out_obs) == 2
    assert out_obs[1].phenomenon_time == datetime(2025, 1, 2, 7, 0, tzinfo=dt_timezone.utc)
    np.testing.assert_allclose(out_obs[1].result, 7.0)


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


def test_run_aggregation_time_weighted_mean(run_context):
    """
    time_weighted_mean, 1-day UTC bucket [2025-02-10T00:00Z, 2025-02-11T00:00Z).

    Observations at 06:00=1.0, 08:00=3.0, 10:00=2.0, 12:00=4.0. Boundary values are
    flat-extrapolated (00:00 -> 1.0, 24:00 -> 4.0), then trapezoidal integration gives:
      [00-06]: (1+1)/2*6 =  6
      [06-08]: (1+3)/2*2 =  4
      [08-10]: (3+2)/2*2 =  5
      [10-12]: (2+4)/2*2 =  6
      [12-24]: (4+4)/2*12= 48
      total = 69 over 24h -> 2.875
    This differs from the simple arithmetic mean of the same observations (2.5),
    confirming the time-weighted method is actually wired through the run pipeline.
    """
    ctx = run_context
    kwargs = {k: ctx[k] for k in ("thing", "sensor", "observed_property", "processing_level", "unit")}
    ds_in = _make_datastream(**kwargs)
    ds_out = _make_datastream(**kwargs)

    for dt, val in [
        (datetime(2025, 2, 10, 6, 0, tzinfo=dt_timezone.utc), 1.0),
        (datetime(2025, 2, 10, 8, 0, tzinfo=dt_timezone.utc), 3.0),
        (datetime(2025, 2, 10, 10, 0, tzinfo=dt_timezone.utc), 2.0),
        (datetime(2025, 2, 10, 12, 0, tzinfo=dt_timezone.utc), 4.0),
    ]:
        _add_obs(ds_in, dt, val)
    _set_end_time(ds_in, datetime(2025, 2, 11, 0, 0, tzinfo=dt_timezone.utc))

    t = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=ctx["owner"],
        transformation_type="aggregation",
        output_datastream=ds_out.pk,
        aggregation_method="time_weighted_mean",
        output_interval_units="days",
        output_interval=1,
        input_datastreams=[TransformationInput(datastream=ds_in.pk)],
    )
    loaded = transformation_service.run(t)
    assert loaded == 1

    from core.sta.models.observation import Observation
    out_obs = list(Observation.objects.filter(datastream=ds_out))
    assert len(out_obs) == 1
    assert out_obs[0].phenomenon_time == datetime(2025, 2, 10, 0, 0, tzinfo=dt_timezone.utc)
    np.testing.assert_allclose(out_obs[0].result, 2.875)


# ============================================================
# run_aggregation: incremental runs and DST (issue #642)
# ============================================================

def _utc(*args):
    return datetime(*args, tzinfo=dt_timezone.utc)


def _add_half_hourly_obs(datastream, start, end, value=1.0):
    """Insert an observation every 30 minutes over [start, end)."""
    ts = start
    while ts < end:
        _add_obs(datastream, ts, value)
        ts += timedelta(minutes=30)


def _output_rows(ds_out):
    from core.sta.models.observation import Observation
    return list(
        Observation.objects.filter(datastream=ds_out)
        .order_by("phenomenon_time")
        .values_list("phenomenon_time", "result")
    )


def _create_aggregation(ctx, ds_in, ds_out, **kwargs):
    params = dict(
        aggregation_method="sum",
        output_interval_units="days",
        output_interval=1,
        timezone_type="iana",
        timezone="America/Denver",
    )
    params.update(kwargs)
    return transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=ctx["owner"],
        transformation_type="aggregation",
        output_datastream=ds_out.pk,
        input_datastreams=[TransformationInput(datastream=ds_in.pk)],
        **params,
    )


def _make_in_out(ctx):
    kwargs = {k: ctx[k] for k in ("thing", "sensor", "observed_property", "processing_level", "unit")}
    return _make_datastream(**kwargs), _make_datastream(**kwargs)


def test_run_aggregation_dst_fall_back(run_context):
    """
    Regression test for #642. 2026-11-01 is a 25-hour day in America/Denver:
      Oct 31 local = 2026-10-31T06:00Z → 2026-11-01T06:00Z (24h, 48 half-hours)
      Nov  1 local = 2026-11-01T06:00Z → 2026-11-02T07:00Z (25h, 50 half-hours)
      Nov  2 local = 2026-11-02T07:00Z → 2026-11-03T07:00Z (24h, 48 half-hours)

    The Nov 1 bucket must not be released until its true end (07:00Z), and the
    next run must start at 07:00Z rather than 06:00Z. Starting at 06:00Z
    re-emits Nov 1 and the task fails on every run after that.
    """
    ds_in, ds_out = _make_in_out(run_context)
    _add_half_hourly_obs(ds_in, _utc(2026, 10, 31, 6), _utc(2026, 11, 3, 8))
    t = _create_aggregation(run_context, ds_in, ds_out)

    # Nov 1 is still in progress at 06:30Z (local 23:30 MST).
    _set_end_time(ds_in, _utc(2026, 11, 2, 6, 30))
    assert transformation_service.run(t) == 1
    assert _output_rows(ds_out) == [(_utc(2026, 10, 31, 6), 48.0)]

    _set_end_time(ds_in, _utc(2026, 11, 2, 7))
    t.refresh_from_db()
    assert transformation_service.run(t) == 1
    assert _output_rows(ds_out)[-1] == (_utc(2026, 11, 1, 6), 50.0)

    _set_end_time(ds_in, _utc(2026, 11, 3, 7))
    t.refresh_from_db()
    assert transformation_service.run(t) == 1
    assert _output_rows(ds_out)[-1] == (_utc(2026, 11, 2, 7), 48.0)

    t.refresh_from_db()
    assert transformation_service.run(t) == 0


def test_run_aggregation_dst_fall_back_recovers_from_stuck_state(run_context):
    """
    Tasks stuck in production already have a (partial) Nov 1 bucket in the
    output. The next run must continue with Nov 2 instead of re-emitting Nov 1.
    """
    ds_in, ds_out = _make_in_out(run_context)
    _add_half_hourly_obs(ds_in, _utc(2026, 11, 1, 6), _utc(2026, 11, 3, 8))
    _add_obs(ds_out, _utc(2026, 11, 1, 6), 49.0)
    _set_end_time(ds_out, _utc(2026, 11, 1, 6))
    _set_end_time(ds_in, _utc(2026, 11, 3, 7))
    t = _create_aggregation(run_context, ds_in, ds_out)

    assert transformation_service.run(t) == 1
    assert _output_rows(ds_out) == [
        (_utc(2026, 11, 1, 6), 49.0),
        (_utc(2026, 11, 2, 7), 48.0),
    ]


def test_run_aggregation_dst_spring_forward(run_context):
    """
    2026-03-08 is a 23-hour day in America/Denver:
      Mar 8 local = 2026-03-08T07:00Z → 2026-03-09T06:00Z (23h, 46 half-hours)
      Mar 9 local = 2026-03-09T06:00Z → 2026-03-10T06:00Z (24h, 48 half-hours)

    Mar 8 is complete at 06:00Z, and the next run must start at 06:00Z (not
    07:00Z), so Mar 9 keeps its first local hour.
    """
    ds_in, ds_out = _make_in_out(run_context)
    _add_half_hourly_obs(ds_in, _utc(2026, 3, 8, 7), _utc(2026, 3, 10, 7))
    t = _create_aggregation(run_context, ds_in, ds_out)

    _set_end_time(ds_in, _utc(2026, 3, 9, 6))
    assert transformation_service.run(t) == 1
    assert _output_rows(ds_out) == [(_utc(2026, 3, 8, 7), 46.0)]

    _set_end_time(ds_in, _utc(2026, 3, 10, 6))
    t.refresh_from_db()
    assert transformation_service.run(t) == 1
    assert _output_rows(ds_out)[-1] == (_utc(2026, 3, 9, 6), 48.0)


def test_run_aggregation_dst_transition_at_midnight(run_context):
    """
    America/Santiago springs forward at local midnight, so 2026-09-06 00:00 doesn't
    exist and that local day starts at 01:00 (-03):
      Sep 5 local = 2026-09-05T04:00Z → 2026-09-06T04:00Z (24h, 48 half-hours)
      Sep 6 local = 2026-09-06T04:00Z → 2026-09-07T03:00Z (23h, 46 half-hours)

    The Sep 5 bucket's end falls on the nonexistent midnight and must resolve to
    04:00Z instead of raising. (Data starts the day before so pandas' resample
    doesn't have to anchor on the nonexistent midnight itself.)
    """
    ds_in, ds_out = _make_in_out(run_context)
    _add_half_hourly_obs(ds_in, _utc(2026, 9, 4, 4), _utc(2026, 9, 7, 4))
    _set_end_time(ds_in, _utc(2026, 9, 7, 3))
    t = _create_aggregation(run_context, ds_in, ds_out, timezone="America/Santiago")

    assert transformation_service.run(t) == 3
    assert _output_rows(ds_out) == [
        (_utc(2026, 9, 4, 4), 48.0),
        (_utc(2026, 9, 5, 4), 48.0),
        (_utc(2026, 9, 6, 4), 46.0),
    ]


@pytest.mark.parametrize("min_values", [None, 2])
def test_run_aggregation_incremental_includes_observation_at_next_bucket_start(run_context, min_values):
    ds_in, ds_out = _make_in_out(run_context)
    for ts, value in [(_utc(2026, 1, 1, 0), 1.0), (_utc(2026, 1, 1, 0, 30), 2.0), (_utc(2026, 1, 1, 1), 100.0)]:
        _add_obs(ds_in, ts, value)
    _set_end_time(ds_in, _utc(2026, 1, 1, 1))
    t = _create_aggregation(
        run_context, ds_in, ds_out,
        output_interval_units="hours", timezone_type=None, timezone=None, min_values=min_values,
    )

    assert transformation_service.run(t) == 1
    assert _output_rows(ds_out) == [(_utc(2026, 1, 1, 0), 3.0)]

    for ts, value in [(_utc(2026, 1, 1, 1, 30), 2.0), (_utc(2026, 1, 1, 2), 0.0)]:
        _add_obs(ds_in, ts, value)
    _set_end_time(ds_in, _utc(2026, 1, 1, 2))
    t.refresh_from_db()

    assert transformation_service.run(t) == 1
    assert _output_rows(ds_out) == [(_utc(2026, 1, 1, 0), 3.0), (_utc(2026, 1, 1, 1), 102.0)]
    t.refresh_from_db()
    assert transformation_service.run(t) == 0


def test_run_aggregation_incremental_time_weighted_mean_interpolates_from_previous_observation(run_context):
    from hydroserverpy.core.timeseries import RESULT_COL
    from hydroserverpy.products.aggregation import apply_aggregation

    ds_in, ds_out = _make_in_out(run_context)
    for ts, value in [(_utc(2026, 1, 1, 0), 0.0), (_utc(2026, 1, 1, 0, 40), 4.0), (_utc(2026, 1, 1, 1, 20), 8.0)]:
        _add_obs(ds_in, ts, value)
    _set_end_time(ds_in, _utc(2026, 1, 1, 1, 20))
    t = _create_aggregation(
        run_context, ds_in, ds_out,
        aggregation_method="time_weighted_mean", output_interval_units="hours", timezone_type=None, timezone=None,
    )

    assert transformation_service.run(t) == 1

    for ts, value in [(_utc(2026, 1, 1, 1, 50), 2.0), (_utc(2026, 1, 1, 2, 10), 2.0)]:
        _add_obs(ds_in, ts, value)
    _set_end_time(ds_in, _utc(2026, 1, 1, 2, 10))
    t.refresh_from_db()

    assert transformation_service.run(t) == 1
    rows = _output_rows(ds_out)
    # The 01:00 boundary interpolates between 00:40=4 and 01:20=8 -> 6, and the
    # result matches aggregating the full history in one pass.
    full = apply_aggregation(
        transformation_service._fetch_observations(ds_in), interval="1h", method="time_weighted_mean",
    )
    assert [ts for ts, _ in rows] == [_utc(2026, 1, 1, 0), _utc(2026, 1, 1, 1)]
    assert [r for _, r in rows] == pytest.approx([3.0, 31 / 6])
    assert [r for _, r in rows] == pytest.approx(full[RESULT_COL].tolist()[:2])


@pytest.mark.parametrize("transformation_type", ["derivation", "rating_curve"])
def test_run_pointwise_transformations_exclude_already_processed_observation(run_context, transformation_type):
    ds_in, ds_out = _make_in_out(run_context)
    _add_obs(ds_out, _utc(2026, 1, 1, 1), 2.0)
    _set_end_time(ds_out, _utc(2026, 1, 1, 1))
    for ts, value in [(_utc(2026, 1, 1, 1), 1.0), (_utc(2026, 1, 1, 2), 2.0)]:
        _add_obs(ds_in, ts, value)
    _set_end_time(ds_in, _utc(2026, 1, 1, 2))

    t = transformation_service.create(
        task=uuid.UUID(TASK1),
        principal=run_context["owner"],
        transformation_type=transformation_type,
        output_datastream=ds_out.pk,
        input_datastreams=[TransformationInput(datastream=ds_in.pk, variable_name="x")],
        **({"formula": "x * 2"} if transformation_type == "derivation" else {"rating_curve": uuid.UUID(RC1)}),
    )

    assert transformation_service.run(t) == 1
    assert _output_rows(ds_out) == [(_utc(2026, 1, 1, 1), 2.0), (_utc(2026, 1, 1, 2), 4.0)]
