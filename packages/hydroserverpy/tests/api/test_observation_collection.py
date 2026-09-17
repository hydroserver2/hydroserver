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
    # First page reports total_count=2 (an estimate), but 5 rows actually
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
