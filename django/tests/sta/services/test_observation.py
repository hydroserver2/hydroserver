import pytest
import uuid
from collections import Counter
from django.http import HttpResponse
from core.sta.models import Observation
from core.sta.services import DatastreamService, ObservationService
from interfaces.api.schemas import (
    DatastreamPatchBody,
    ObservationBulkPostBody,
    ObservationBulkDeleteBody,
    ObservationPostBody,
    ObservationSummaryResponse,
)

observation_service = ObservationService()
datastream_service = DatastreamService()


@pytest.mark.parametrize(
    "principal, datastream_id, params, observation_results, max_queries",
    [
        # Test user access
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {},
            [1.1, 3.1],
            11,
        ),
        (
            "editor",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {},
            [1.1, 3.1],
            11,
        ),
        (
            "viewer",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {},
            [1.1, 3.1],
            11,
        ),
        (
            "admin",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {},
            [1.1, 3.1],
            11,
        ),
        (
            "apikey",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {},
            [1.1, 3.1],
            11,
        ),
        (
            "admin",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {},
            [1.1, 3.1],
            11,
        ),
        (
            "apikey",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {},
            [1.1, 3.1],
            11,
        ),
        (
            "unaffiliated",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {},
            [1.1, 3.1],
            11,
        ),
        (
            "anonymous",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {},
            [1.1, 3.1],
            11,
        ),
        # Test pagination and order_by
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"page": 2, "page_size": 1, "order_by": "-phenomenonTime"},
            [1.1],
            11,
        ),
        # Test filtering
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"phenomenon_time__gte": "2025-02-10 02:00:00.000 -0700"},
            [3.1],
            11,
        ),
        (
            "owner",
            "27c70b41-e845-40ea-8cc7-d1b40f89816b",
            {"result_qualifier_codes": ["SystemResultQualifier"]},
            [3.1],
            11,
        ),
    ],
)
def test_list_observation(
    django_assert_max_num_queries,
    get_principal,
    principal,
    datastream_id,
    params,
    observation_results,
    max_queries,
):
    with django_assert_max_num_queries(max_queries):
        http_response = HttpResponse()
        result = observation_service.list(
            principal=get_principal(principal),
            response=http_response,
            datastream_id=uuid.UUID(datastream_id),
            page=params.pop("page", 1),
            page_size=params.pop("page_size", 100),
            order_by=[params.pop("order_by")] if "order_by" in params else [],
            filtering=params,
        )
        assert Counter(observation.result for observation in result) == Counter(
            observation_results
        )
        assert (
            ObservationSummaryResponse.from_orm(observation) for observation in result
        )


def test_create_observation(
    django_assert_max_num_queries,
    get_principal,
):
    datastream_id = uuid.UUID("27c70b41-e845-40ea-8cc7-d1b40f89816b")

    with django_assert_max_num_queries(12):
        result = observation_service.create(
            principal=get_principal("owner"),
            datastream_id=datastream_id,
            data=ObservationPostBody(
                phenomenon_time="2025-03-10T01:00:00Z",
                result=9.1,
            ),
            update_datastream_statistics=False,
        )

    assert result.result == 9.1
    assert result.result_qualifier_codes == []


def test_create_observation_with_result_qualifier_codes(
    django_assert_max_num_queries,
    get_principal,
):
    datastream_id = uuid.UUID("27c70b41-e845-40ea-8cc7-d1b40f89816b")

    with django_assert_max_num_queries(14):
        result = observation_service.create(
            principal=get_principal("owner"),
            datastream_id=datastream_id,
            data=ObservationPostBody(
                phenomenon_time="2025-03-10T02:00:00Z",
                result=9.2,
                result_qualifier_codes=["SystemResultQualifier", "PublicResultQualifier"],
            ),
            update_datastream_statistics=False,
        )

    assert result.result == 9.2
    assert set(result.result_qualifier_codes) == {
        "SystemResultQualifier",
        "PublicResultQualifier",
    }


def test_create_observation_with_invalid_result_qualifier_code(
    get_principal,
):
    from ninja.errors import HttpError

    datastream_id = uuid.UUID("27c70b41-e845-40ea-8cc7-d1b40f89816b")

    with pytest.raises(HttpError) as exc_info:
        observation_service.create(
            principal=get_principal("owner"),
            datastream_id=datastream_id,
            data=ObservationPostBody(
                phenomenon_time="2025-03-10T03:00:00Z",
                result=9.3,
                result_qualifier_codes=["NonExistentCode"],
            ),
            update_datastream_statistics=False,
        )

    assert exc_info.value.status_code == 400


def test_create_observations(
    django_assert_max_num_queries,
    get_principal,
):
    with django_assert_max_num_queries(13):
        observation_service.bulk_create(
            principal=get_principal("owner"),
            datastream_id=uuid.UUID("27c70b41-e845-40ea-8cc7-d1b40f89816b"),
            data=ObservationBulkPostBody(
                fields=["phenomenonTime", "result", "resultQualifierCodes"],
                data=[
                    ["2025-03-10T01:00:00Z", 9.1, []],
                    ["2025-03-10T02:00:00Z", 9.2, ["SystemResultQualifier"]],
                    [
                        "2025-03-10T03:00:00Z",
                        9.2,
                        ["SystemResultQualifier", "PublicResultQualifier"],
                    ],
                ],
            ),
            mode="insert",
        )

    assert (
        Observation.objects.filter(
            datastream_id=uuid.UUID("27c70b41-e845-40ea-8cc7-d1b40f89816b")
        ).count()
        == 5
    )


REPLACE_DATASTREAM_ID = uuid.UUID("27c70b41-e845-40ea-8cc7-d1b40f89816b")


def replace_observations(get_principal, rows, **kwargs):
    observation_service.bulk_create(
        principal=get_principal("owner"),
        datastream_id=REPLACE_DATASTREAM_ID,
        data=ObservationBulkPostBody(fields=["phenomenonTime", "result"], data=rows),
        mode="replace",
        **kwargs,
    )
    return sorted(
        Observation.objects.filter(datastream_id=REPLACE_DATASTREAM_ID).values_list(
            "result", flat=True
        )
    )


def test_replace_observations_deletes_the_given_range(get_principal):
    # The existing points (08:00Z, 09:00Z) sit outside the upload's own span.
    results = replace_observations(
        get_principal,
        [["2025-02-10T08:30:00Z", 5.5]],
        phenomenon_time_start="2025-02-10T07:00:00Z",
        phenomenon_time_end="2025-02-10T10:00:00Z",
    )

    assert results == [5.5]


def test_replace_observations_with_an_empty_upload_clears_the_range(get_principal):
    results = replace_observations(
        get_principal,
        [],
        phenomenon_time_start="2025-02-10T07:00:00Z",
        phenomenon_time_end="2025-02-10T10:00:00Z",
    )

    assert results == []


def test_replace_observations_without_a_range_uses_the_upload_span(get_principal):
    results = replace_observations(get_principal, [["2025-02-10T08:30:00Z", 5.5]])

    assert results == [1.1, 3.1, 5.5]


def test_replace_observations_rejects_an_empty_upload_without_a_range(get_principal):
    from ninja.errors import HttpError

    with pytest.raises(HttpError) as exc_info:
        replace_observations(get_principal, [])

    assert exc_info.value.status_code == 400


def test_replace_observations_rejects_half_a_range(get_principal):
    from ninja.errors import HttpError

    with pytest.raises(HttpError) as exc_info:
        replace_observations(
            get_principal,
            [["2025-02-10T08:30:00Z", 5.5]],
            phenomenon_time_start="2025-02-10T07:00:00Z",
        )

    assert exc_info.value.status_code == 400


def test_create_observations_rejects_a_range_outside_replace_mode(get_principal):
    from ninja.errors import HttpError

    with pytest.raises(HttpError) as exc_info:
        observation_service.bulk_create(
            principal=get_principal("owner"),
            datastream_id=REPLACE_DATASTREAM_ID,
            data=ObservationBulkPostBody(
                fields=["phenomenonTime", "result"],
                data=[["2025-03-10T01:00:00Z", 9.1]],
            ),
            mode="insert",
            phenomenon_time_start="2025-03-10T00:00:00Z",
            phenomenon_time_end="2025-03-10T02:00:00Z",
        )

    assert exc_info.value.status_code == 400


def test_delete_observations(
    django_assert_max_num_queries,
    get_principal,
):
    with django_assert_max_num_queries(13):
        observation_service.bulk_delete(
            principal=get_principal("owner"),
            datastream_id=uuid.UUID("27c70b41-e845-40ea-8cc7-d1b40f89816b"),
            data=ObservationBulkDeleteBody(),
        )

    assert (
        Observation.objects.filter(
            datastream_id=uuid.UUID("27c70b41-e845-40ea-8cc7-d1b40f89816b")
        ).count()
        == 0
    )


def test_hidden_public_datastream_observations_are_not_listed_for_guests(
    get_principal,
):
    datastream_id = uuid.UUID("27c70b41-e845-40ea-8cc7-d1b40f89816b")

    datastream_service.update(
        principal=get_principal("owner"),
        uid=datastream_id,
        data=DatastreamPatchBody(is_visible=False),
    )

    anonymous_result = observation_service.list(
        principal=get_principal("anonymous"),
        response=HttpResponse(),
        datastream_id=datastream_id,
        page=1,
        page_size=100,
        order_by=[],
        filtering={},
    )
    owner_result = observation_service.list(
        principal=get_principal("owner"),
        response=HttpResponse(),
        datastream_id=datastream_id,
        page=1,
        page_size=100,
        order_by=[],
        filtering={},
    )

    assert anonymous_result == []
    assert Counter(observation.result for observation in owner_result) == Counter(
        [1.1, 3.1]
    )
