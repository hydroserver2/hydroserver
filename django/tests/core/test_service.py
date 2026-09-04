from interfaces.api.service import APIService
from core.sta.models import Datastream


def test_apply_ordering_appends_id_tiebreaker_for_deterministic_pagination():
    """Regression test for #484 ("Not all datastreams show up in
    aggregation/expression form").

    Rows that tie on the requested ordering field (e.g. many datastreams
    named "Mean daily discharge (gpm) - provisional" across different
    sites) have no guaranteed relative order. Pages are fetched with
    independent queries (see the client's `paginatedFetch`), so without a
    unique tiebreaker a tied row can land on neither page and silently
    disappear from every page of results. Appending the primary key as a
    final sort key makes ordering - and therefore pagination - deterministic.
    """
    queryset = APIService.apply_ordering(Datastream.objects.all(), ["name"], ["name"])
    assert queryset.query.order_by == ("name", "id")


def test_apply_ordering_does_not_duplicate_an_already_requested_id():
    queryset = APIService.apply_ordering(Datastream.objects.all(), ["id"], ["id"])
    assert queryset.query.order_by == ("id",)
