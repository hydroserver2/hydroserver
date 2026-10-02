from unittest.mock import MagicMock

import pandas as pd

from hydroserverpy.api.models.sta.observation import ObservationCollection


def _collection(datastream, values, limit, offset, total_count):
    df = pd.DataFrame({"phenomenon_time": values, "result": values})
    return ObservationCollection(
        datastream=datastream,
        dataframe=df,
        offset=offset,
        limit=limit,
        total_count=total_count,
    )


def test_fetch_all_continues_past_an_underestimated_total_count():
    datastream = MagicMock()
    # The first page reports total_count=2 (an estimate), but 5 rows actually
    # exist across 3 pages of limit=2 - the last page is short, proving
    # completion.
    page2 = _collection(datastream, [2, 3], limit=2, offset=2, total_count=2)
    page3 = _collection(datastream, [4], limit=2, offset=4, total_count=2)
    datastream.get_observations.side_effect = [page2, page3]

    first_page = _collection(datastream, [0, 1], limit=2, offset=0, total_count=2)

    result = first_page.fetch_all()

    assert list(result.dataframe["result"]) == [0, 1, 2, 3, 4]
    assert result.total_count == 5
    assert datastream.get_observations.call_count == 2


def test_fetch_all_stops_immediately_when_first_page_is_already_short():
    datastream = MagicMock()
    first_page = _collection(datastream, [0], limit=2, offset=0, total_count=1)

    result = first_page.fetch_all()

    assert list(result.dataframe["result"]) == [0]
    assert result.total_count == 1
    datastream.get_observations.assert_not_called()


def test_column_profile_pages_combine_their_datastream_groups():
    response = MagicMock()
    response.json.return_value = {
        "data": [
            {
                "datastreamId": "ds-1",
                "workspaceId": "ws-1",
                "columns": {
                    "id": ["o-1", "o-2"],
                    "phenomenonTime": ["2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z"],
                    "result": [1.0, 2.0],
                    "resultQualifierCodes": [[], ["A"]],
                },
            }
        ],
        "meta": {"offset": 0, "limit": 100, "totalCount": 2},
    }

    collection = ObservationCollection(datastream=MagicMock(), response=response)

    assert list(collection.dataframe["result"]) == [1.0, 2.0]
    assert list(collection.dataframe["result_qualifier_codes"]) == [[], ["A"]]
    assert list(collection.dataframe["id"]) == ["o-1", "o-2"]
    assert list(collection.dataframe["workspace_id"]) == ["ws-1", "ws-1"]
    assert str(collection.dataframe["phenomenon_time"].dt.tz) == "UTC"
    assert collection.total_count == 2


def test_an_empty_column_profile_page_has_the_observation_columns():
    response = MagicMock()
    response.json.return_value = {"data": [], "meta": {"offset": 0, "limit": 100, "totalCount": 0}}

    collection = ObservationCollection(datastream=MagicMock(), response=response)

    assert collection.dataframe.empty
    assert list(collection.dataframe.columns) == ["id", "phenomenon_time", "result", "result_qualifier_codes"]
