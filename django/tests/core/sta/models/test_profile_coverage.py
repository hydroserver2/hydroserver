from datetime import datetime, timezone
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from core.sta.models import Datastream, Observation
from tests.core.sta.factories import DatastreamFactory, UnitFactory

pytestmark = pytest.mark.django_db

PHENOMENON_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _observation(datastream, z=None, phenomenon_time=PHENOMENON_TIME):
    return Observation.objects.create(datastream=datastream, phenomenon_time=phenomenon_time, z=z, result=1.0)


# --- clean(): z fields by datastream type -------------------------------------------


@pytest.mark.parametrize("field", ["z_unit", "z_reference"])
def test_full_clean_rejects_profile_missing_z_field(field):
    datastream = DatastreamFactory(profile=True)
    setattr(datastream, field, None)

    with pytest.raises(ValidationError, match="require a z unit and a z reference"):
        datastream.full_clean()


@pytest.mark.parametrize("field", ["z_unit", "z_reference"])
def test_full_clean_rejects_time_series_with_z_field(field):
    datastream = DatastreamFactory()
    values = {
        "z_unit": UnitFactory(workspace=datastream.monitoring_site.workspace),
        "z_reference": "Depth below surface",
    }
    setattr(datastream, field, values[field])

    with pytest.raises(ValidationError, match="Only profile coverage datastreams"):
        datastream.full_clean()


def test_full_clean_rejects_z_unit_from_another_workspace():
    datastream = DatastreamFactory(profile=True)
    datastream.z_unit = UnitFactory()

    with pytest.raises(ValidationError, match="z unit cannot be associated"):
        datastream.full_clean()


# --- database constraints -----------------------------------------------------------


def test_check_constraint_rejects_time_series_with_z_reference():
    datastream = DatastreamFactory()

    with pytest.raises(IntegrityError), transaction.atomic():
        Datastream.objects.filter(pk=datastream.pk).update(z_reference="Depth below surface")


def test_check_constraint_rejects_profile_without_z_unit():
    datastream = DatastreamFactory(profile=True)

    with pytest.raises(IntegrityError), transaction.atomic():
        Datastream.objects.filter(pk=datastream.pk).update(z_unit=None)


def test_unique_constraint_rejects_time_series_rows_at_one_phenomenon_time():
    datastream = DatastreamFactory()
    _observation(datastream)

    with pytest.raises(IntegrityError), transaction.atomic():
        _observation(datastream)


def test_unique_constraint_accepts_profile_rows_at_one_phenomenon_time_with_different_z():
    datastream = DatastreamFactory(profile=True)
    _observation(datastream, z=Decimal("0.5"))
    _observation(datastream, z=Decimal("1.5"))

    assert Observation.objects.filter(datastream=datastream).count() == 2


def test_unique_constraint_rejects_profile_rows_with_equal_decimal_z():
    datastream = DatastreamFactory(profile=True)
    _observation(datastream, z=Decimal("1.5"))

    with pytest.raises(IntegrityError), transaction.atomic():
        _observation(datastream, z=Decimal("1.500000"))
