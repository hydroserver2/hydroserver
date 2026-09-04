import pytest
from django.core.exceptions import ValidationError

from processing.products.models import DataProductTransformation, DataProductTransformationInput
from tests.core.iam.factories import WorkspaceFactory
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory
from tests.processing.products.factories import (
    DataProductTaskFactory,
    DataProductTransformationFactory,
    DataProductTransformationInputFactory,
    RatingCurveFactory,
    RatingCurvePointFactory,
)

pytestmark = pytest.mark.django_db


def _task_and_site(workspace=None):
    workspace = workspace or WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    task = DataProductTaskFactory(monitoring_site=monitoring_site)
    return task, monitoring_site


# --- output datastream workspace/site scoping -----------------------------------------------


def test_full_clean_rejects_output_datastream_from_another_workspace():
    task, monitoring_site = _task_and_site()
    other_output = DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=WorkspaceFactory()))
    rating_curve = RatingCurveFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformation(
        task=task, output_datastream=other_output,
        transformation_type="rating_curve", rating_curve=rating_curve,
    )

    with pytest.raises(ValidationError):
        transformation.full_clean()


def test_full_clean_rejects_output_datastream_from_another_monitoring_site_in_same_workspace():
    workspace = WorkspaceFactory()
    task, monitoring_site = _task_and_site(workspace=workspace)
    other_site = MonitoringSiteFactory(workspace=workspace)
    other_output = DatastreamFactory(monitoring_site=other_site)
    rating_curve = RatingCurveFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformation(
        task=task, output_datastream=other_output,
        transformation_type="rating_curve", rating_curve=rating_curve,
    )

    with pytest.raises(ValidationError):
        transformation.full_clean()


# --- rating_curve type -------------------------------------------------------------------------


def test_full_clean_allows_valid_rating_curve_transformation():
    task, monitoring_site = _task_and_site()
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    rating_curve = RatingCurveFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformationFactory(
        task=task, output_datastream=output_ds,
        transformation_type="rating_curve", rating_curve=rating_curve, formula=None,
    )

    transformation.full_clean()  # does not raise


def test_full_clean_rejects_rating_curve_transformation_missing_rating_curve():
    task, monitoring_site = _task_and_site()
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformation(
        task=task, output_datastream=output_ds, transformation_type="rating_curve",
    )

    with pytest.raises(ValidationError):
        transformation.full_clean()


def test_full_clean_rejects_rating_curve_transformation_with_forbidden_formula():
    task, monitoring_site = _task_and_site()
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    rating_curve = RatingCurveFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformation(
        task=task, output_datastream=output_ds, transformation_type="rating_curve",
        rating_curve=rating_curve, formula="x",
    )

    with pytest.raises(ValidationError):
        transformation.full_clean()


def test_full_clean_rejects_rating_curve_from_another_monitoring_site():
    task, monitoring_site = _task_and_site()
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    other_rating_curve = RatingCurveFactory(monitoring_site=MonitoringSiteFactory(workspace=monitoring_site.workspace))
    transformation = DataProductTransformation(
        task=task, output_datastream=output_ds,
        transformation_type="rating_curve", rating_curve=other_rating_curve,
    )

    with pytest.raises(ValidationError):
        transformation.full_clean()


# --- derivation type -----------------------------------------------------------------------


def test_full_clean_allows_valid_derivation_transformation():
    task, monitoring_site = _task_and_site()
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformationFactory(
        task=task, output_datastream=output_ds,
        transformation_type="derivation", formula="a + b",
    )
    DataProductTransformationInputFactory(
        transformation=transformation,
        datastream=DatastreamFactory(monitoring_site=monitoring_site),
        variable_name="a",
    )
    DataProductTransformationInputFactory(
        transformation=transformation,
        datastream=DatastreamFactory(monitoring_site=monitoring_site),
        variable_name="b",
    )

    transformation.full_clean()  # does not raise


def test_full_clean_rejects_derivation_transformation_missing_formula():
    task, monitoring_site = _task_and_site()
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformation(
        task=task, output_datastream=output_ds, transformation_type="derivation", formula=None,
    )

    with pytest.raises(ValidationError):
        transformation.full_clean()


def test_full_clean_rejects_derivation_transformation_with_forbidden_rating_curve():
    task, monitoring_site = _task_and_site()
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    rating_curve = RatingCurveFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformationFactory(
        task=task, output_datastream=output_ds,
        transformation_type="derivation", formula="a", rating_curve=rating_curve,
    )
    DataProductTransformationInputFactory(
        transformation=transformation,
        datastream=DatastreamFactory(monitoring_site=monitoring_site),
        variable_name="a",
    )

    with pytest.raises(ValidationError):
        transformation.full_clean()


def test_full_clean_rejects_derivation_transformation_without_inputs():
    task, monitoring_site = _task_and_site()
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformationFactory(
        task=task, output_datastream=output_ds, transformation_type="derivation", formula="a",
    )

    with pytest.raises(ValidationError):
        transformation.full_clean()


def test_full_clean_rejects_derivation_transformation_with_invalid_formula():
    task, monitoring_site = _task_and_site()
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformationFactory(
        task=task, output_datastream=output_ds, transformation_type="derivation", formula="unknown_var + 1",
    )
    DataProductTransformationInputFactory(
        transformation=transformation,
        datastream=DatastreamFactory(monitoring_site=monitoring_site),
        variable_name="a",
    )

    with pytest.raises(ValidationError):
        transformation.full_clean()


# --- aggregation type -----------------------------------------------------------------------


def test_full_clean_allows_valid_aggregation_transformation():
    task, monitoring_site = _task_and_site()
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformationFactory(
        task=task, output_datastream=output_ds, transformation_type="aggregation", formula=None,
        aggregation_method="mean", output_interval_units="hours", output_interval=1,
    )

    transformation.full_clean()  # does not raise


def test_full_clean_rejects_aggregation_transformation_missing_required_fields():
    task, monitoring_site = _task_and_site()
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformation(
        task=task, output_datastream=output_ds, transformation_type="aggregation",
    )

    with pytest.raises(ValidationError):
        transformation.full_clean()


def test_full_clean_rejects_aggregation_transformation_with_forbidden_formula():
    task, monitoring_site = _task_and_site()
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformationFactory(
        task=task, output_datastream=output_ds, transformation_type="aggregation", formula="a",
        aggregation_method="mean", output_interval_units="hours", output_interval=1,
    )

    with pytest.raises(ValidationError):
        transformation.full_clean()


def test_full_clean_rejects_aggregation_timezone_without_timezone_type():
    task, monitoring_site = _task_and_site()
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformationFactory(
        task=task, output_datastream=output_ds, transformation_type="aggregation", formula=None,
        aggregation_method="mean", output_interval_units="hours", output_interval=1,
        timezone="America/Denver", timezone_type=None,
    )

    with pytest.raises(ValidationError):
        transformation.full_clean()


def test_full_clean_rejects_aggregation_utc_with_timezone_set():
    task, monitoring_site = _task_and_site()
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformationFactory(
        task=task, output_datastream=output_ds, transformation_type="aggregation", formula=None,
        aggregation_method="mean", output_interval_units="hours", output_interval=1,
        timezone_type="utc", timezone="America/Denver",
    )

    with pytest.raises(ValidationError):
        transformation.full_clean()


def test_full_clean_rejects_aggregation_iana_missing_timezone():
    task, monitoring_site = _task_and_site()
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformationFactory(
        task=task, output_datastream=output_ds, transformation_type="aggregation", formula=None,
        aggregation_method="mean", output_interval_units="hours", output_interval=1,
        timezone_type="iana", timezone=None,
    )

    with pytest.raises(ValidationError):
        transformation.full_clean()


def test_full_clean_rejects_aggregation_invalid_timezone_string():
    task, monitoring_site = _task_and_site()
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformationFactory(
        task=task, output_datastream=output_ds, transformation_type="aggregation", formula=None,
        aggregation_method="mean", output_interval_units="hours", output_interval=1,
        timezone_type="iana", timezone="Not/A_Real_Zone",
    )

    with pytest.raises(ValidationError):
        transformation.full_clean()


def test_full_clean_allows_valid_offset_timezone():
    task, monitoring_site = _task_and_site()
    output_ds = DatastreamFactory(monitoring_site=monitoring_site)
    transformation = DataProductTransformationFactory(
        task=task, output_datastream=output_ds, transformation_type="aggregation", formula=None,
        aggregation_method="mean", output_interval_units="hours", output_interval=1,
        timezone_type="offset", timezone="-07:00",
    )

    transformation.full_clean()  # does not raise


# --- DataProductTransformationInput.clean() -------------------------------------------------


def test_input_full_clean_rejects_datastream_from_another_workspace():
    task, monitoring_site = _task_and_site()
    transformation = DataProductTransformationFactory(
        task=task, output_datastream=DatastreamFactory(monitoring_site=monitoring_site),
        transformation_type="derivation", formula="a",
    )
    other_datastream = DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=WorkspaceFactory()))
    transformation_input = DataProductTransformationInput(
        transformation=transformation, datastream=other_datastream, variable_name="a",
    )

    with pytest.raises(ValidationError):
        transformation_input.full_clean()


def test_input_full_clean_rejects_missing_variable_name_for_derivation():
    task, monitoring_site = _task_and_site()
    transformation = DataProductTransformationFactory(
        task=task, output_datastream=DatastreamFactory(monitoring_site=monitoring_site),
        transformation_type="derivation", formula="a",
    )
    transformation_input = DataProductTransformationInput(
        transformation=transformation,
        datastream=DatastreamFactory(monitoring_site=monitoring_site),
        variable_name=None,
    )

    with pytest.raises(ValidationError):
        transformation_input.full_clean()


def test_input_full_clean_allows_valid_input():
    task, monitoring_site = _task_and_site()
    transformation = DataProductTransformationFactory(
        task=task, output_datastream=DatastreamFactory(monitoring_site=monitoring_site),
        transformation_type="derivation", formula="a",
    )
    transformation_input = DataProductTransformationInput(
        transformation=transformation,
        datastream=DatastreamFactory(monitoring_site=monitoring_site),
        variable_name="a",
    )

    transformation_input.full_clean()  # does not raise


# --- RatingCurvePoint unique_rating_curve_point_input_value constraint ----------------------


def test_full_clean_rejects_duplicate_rating_curve_point_input_value():
    rating_curve = RatingCurveFactory()
    RatingCurvePointFactory(rating_curve=rating_curve, input_value=1.0, output_value=2.0)
    duplicate = RatingCurvePointFactory.build(rating_curve=rating_curve, input_value=1.0, output_value=5.0)

    with pytest.raises(ValidationError):
        duplicate.full_clean()
