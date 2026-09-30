import pytest

from tests.core.iam.factories import UserFactory
from tests.core.sta.factories import AggregationStatisticFactory

pytestmark = pytest.mark.django_db

AGGREGATION_STATISTICS_URL = "/api/data/aggregation-statistics"


def _detail_url(aggregation_statistic_id):
    return f"{AGGREGATION_STATISTICS_URL}/{aggregation_statistic_id}"


def _aggregation_statistic_body(**overrides):
    body = {
        "name": "New Statistic",
        "description": "A new aggregation statistic.",
    }
    body.update(overrides)
    return body


# --- get_aggregation_statistics --------------------------------------------------------------


def test_get_aggregation_statistics_visible_to_anonymous(client):
    aggregation_statistic = AggregationStatisticFactory()

    response = client.get(AGGREGATION_STATISTICS_URL)

    assert response.status_code == 200
    assert str(aggregation_statistic.id) in [r["id"] for r in response.json()["data"]]


def test_get_aggregation_statistics_visible_to_any_authenticated_user(client):
    aggregation_statistic = AggregationStatisticFactory()
    client.force_login(UserFactory())

    response = client.get(AGGREGATION_STATISTICS_URL)

    assert response.status_code == 200
    assert str(aggregation_statistic.id) in [r["id"] for r in response.json()["data"]]


def test_get_aggregation_statistics_properties_filters_every_item_in_the_list(client):
    AggregationStatisticFactory(name="A")
    AggregationStatisticFactory(name="B")

    response = client.get(AGGREGATION_STATISTICS_URL, {"properties": "id,name"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 2
    for item in items:
        assert set(item.keys()) == {"id", "name"}


def test_get_aggregation_statistics_properties_rejects_unknown_property(client):
    response = client.get(AGGREGATION_STATISTICS_URL, {"properties": "id,bogus"})

    assert response.status_code == 400


def test_get_aggregation_statistics_without_properties_returns_every_field(client):
    AggregationStatisticFactory(name="A")

    response = client.get(AGGREGATION_STATISTICS_URL)

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert set(item.keys()) == {"id", "name", "description"}


def test_get_aggregation_statistics_q_searches_name_and_description(client):
    AggregationStatisticFactory(name="Alpha term", description="")
    AggregationStatisticFactory(name="Beta term", description="")

    response = client.get(AGGREGATION_STATISTICS_URL, {"q": "alpha"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["name"] == "Alpha term"


def test_get_aggregation_statistics_sortby_name_descending(client):
    AggregationStatisticFactory(name="Alpha")
    AggregationStatisticFactory(name="Beta")

    response = client.get(AGGREGATION_STATISTICS_URL, {"sortby": "-name"})

    assert response.status_code == 200
    names = [item["name"] for item in response.json()["data"]]
    assert names.index("Beta") < names.index("Alpha")


# --- create_aggregation_statistic ------------------------------------------------------------


def test_create_aggregation_statistic_succeeds_for_superuser(client):
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.post(
        AGGREGATION_STATISTICS_URL,
        data=_aggregation_statistic_body(),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json().keys()) == {"id"}
    aggregation_statistic_id = response.json()["id"]

    detail = client.get(_detail_url(aggregation_statistic_id))
    assert detail.json()["data"]["name"] == "New Statistic"


def test_create_aggregation_statistic_returns_401_when_unauthenticated(client):
    response = client.post(
        AGGREGATION_STATISTICS_URL,
        data=_aggregation_statistic_body(),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_create_aggregation_statistic_returns_403_for_non_superuser(client):
    client.force_login(UserFactory())

    response = client.post(
        AGGREGATION_STATISTICS_URL,
        data=_aggregation_statistic_body(),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_aggregation_statistic_returns_400_for_duplicate_name(client):
    AggregationStatisticFactory(name="Duplicate")
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.post(
        AGGREGATION_STATISTICS_URL,
        data=_aggregation_statistic_body(name="Duplicate"),
        content_type="application/json",
    )

    assert response.status_code == 400


# --- get_aggregation_statistic ----------------------------------------------------------------


def test_get_aggregation_statistic_returns_200_for_anonymous(client):
    aggregation_statistic = AggregationStatisticFactory()

    response = client.get(_detail_url(aggregation_statistic.id))

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(aggregation_statistic.id)


def test_get_aggregation_statistic_returns_404_for_nonexistent_term(client):
    response = client.get(_detail_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 404


def test_get_aggregation_statistic_properties_rejects_unknown_property(client):
    aggregation_statistic = AggregationStatisticFactory()

    response = client.get(_detail_url(aggregation_statistic.id), {"properties": "bogus"})

    assert response.status_code == 400


# --- update_aggregation_statistic -------------------------------------------------------------


def test_update_aggregation_statistic_succeeds_for_superuser(client):
    aggregation_statistic = AggregationStatisticFactory(name="Original Name")
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.patch(
        _detail_url(aggregation_statistic.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 204
    assert not response.content

    detail = client.get(_detail_url(aggregation_statistic.id))
    assert detail.json()["data"]["name"] == "Updated Name"


def test_update_aggregation_statistic_returns_401_when_unauthenticated(client):
    aggregation_statistic = AggregationStatisticFactory()

    response = client.patch(
        _detail_url(aggregation_statistic.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 401


def test_update_aggregation_statistic_returns_403_for_non_superuser(client):
    aggregation_statistic = AggregationStatisticFactory()
    client.force_login(UserFactory())

    response = client.patch(
        _detail_url(aggregation_statistic.id),
        data={"name": "Updated Name"},
        content_type="application/json",
    )

    assert response.status_code == 403


# --- delete_aggregation_statistic -------------------------------------------------------------


def test_delete_aggregation_statistic_succeeds_for_superuser(client):
    aggregation_statistic = AggregationStatisticFactory()
    superuser = UserFactory(is_superuser=True)
    client.force_login(superuser)

    response = client.delete(_detail_url(aggregation_statistic.id))

    assert response.status_code == 204
    assert client.get(_detail_url(aggregation_statistic.id)).status_code == 404


def test_delete_aggregation_statistic_returns_403_for_non_superuser(client):
    aggregation_statistic = AggregationStatisticFactory()
    client.force_login(UserFactory())

    response = client.delete(_detail_url(aggregation_statistic.id))

    assert response.status_code == 403
