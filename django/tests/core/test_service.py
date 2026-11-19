import pytest
from django.db.models.expressions import OrderBy

from interfaces.api.service import APIService
from core.sta.models import Datastream, MonitoringSite, Observation


def test_apply_sorting_appends_id_tiebreaker_for_deterministic_pagination():
    """Regression test for #484 ("Not all datastreams show up in
    aggregation/expression form").

    Rows that tie on the requested sorting field (e.g., many datastreams
    named "Mean daily discharge (gpm) - provisional" across different
    sites) have no guaranteed relative order. Pages are fetched with
    independent queries (see the client's `paginatedFetch`), so without a
    unique tiebreaker a tied row can land on neither page and silently
    disappear from every page of results. Appending the primary key as a
    final sort key makes sorting - and therefore pagination - deterministic.
    """
    queryset = APIService.apply_sorting(Datastream.objects.all(), ["name"], ["name"])
    assert queryset.query.order_by == ("name", "id")


def test_apply_sorting_does_not_duplicate_an_already_requested_id():
    queryset = APIService.apply_sorting(Datastream.objects.all(), ["id"], ["id"])
    assert queryset.query.order_by == ("id",)


@pytest.mark.parametrize(
    ("model", "field", "nullable"),
    [
        (Datastream, "-phenomenonEndTime", True),
        (Datastream, "-monitoringSite__elevationM", True),
        (MonitoringSite, "-datastreams__name", True),
        # NOT NULL stays plain: NULLS LAST would stop Postgres using the index for DESC.
        (Observation, "-phenomenonTime", False),
    ],
)
def test_apply_sorting_puts_nulls_last_only_for_fields_that_can_be_null(model, field, nullable):
    first = APIService.apply_sorting(model.objects.all(), [field], [field]).query.order_by[0]
    if nullable:
        assert isinstance(first, OrderBy) and first.descending and first.nulls_last
    else:
        assert first == "-phenomenon_time"
