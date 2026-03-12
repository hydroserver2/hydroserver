import math
import pandas as pd
from typing import Literal, Optional
from bisect import bisect_left
from datetime import datetime, time, timedelta, timezone as dt_timezone
from .base import DataOperation
from ..models.timestamp import Timezone


AggregationStatistic = Literal["simple_mean", "time_weighted_mean", "last_value_of_period"]
AggregationIntervalUnit = Literal["day"]


class TemporalAggregationOperation(DataOperation, Timezone):
    aggregation_statistic: AggregationStatistic
    aggregation_interval: int = 1
    aggregation_interval_unit: AggregationIntervalUnit = "day"

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate a (timestamp, value) DataFrame over fixed-duration day windows.

        The df must have a UTC-normalized 'timestamp' column and a numeric 'value'
        column. The returned DataFrame has one row per window with the window-start
        UTC timestamp as the 'timestamp' column. Windows with no observations are
        dropped entirely.
        """

        if df.empty:
            return pd.DataFrame(columns=["timestamp", "value"])

        timestamps: list[datetime] = df["timestamp"].dt.to_pydatetime().tolist()
        values: list[float] = pd.to_numeric(df["value"], errors="coerce").tolist()
        start_utc = timestamps[0]
        end_utc = timestamps[-1]

        result_timestamps: list = []
        result_values: list = []

        for ws, we in self._iter_windows(start_utc, end_utc):
            value = self._aggregate_window(timestamps, values, ws, we)
            if value is None:
                continue
            result_timestamps.append(ws)
            result_values.append(value)

        out = pd.DataFrame({"timestamp": result_timestamps, "value": result_values})
        out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True)

        return out

    def _effective_tz(self):
        """
        Return the tzinfo to use for window boundaries, defaulting to UTC.
        """

        return self.tz or dt_timezone.utc

    def _interval_delta(self) -> timedelta:
        """
        Return the timedelta for the configured aggregation interval.
        """

        if self.aggregation_interval_unit == "day":
            return timedelta(days=self.aggregation_interval)

        raise NotImplementedError(
            f"Invalid temporal aggregation configuration. "
            f"Received unsupported aggregation interval unit: {self.aggregation_interval_unit!r}"
        )

    def _window_start(self, ts_utc: datetime) -> datetime:
        """
        Return the local datetime aligned to the start of the window containing ts_utc.
        """

        tz = self._effective_tz()
        local = ts_utc.astimezone(tz)

        if self.aggregation_interval_unit == "day":
            return datetime.combine(local.date(), time.min, tzinfo=tz)

        raise NotImplementedError(
            f"Invalid temporal aggregation configuration. "
            f"Received unsupported aggregation interval unit: {self.aggregation_interval_unit!r}"
        )

    def _next_window_start(self, current: datetime) -> datetime:
        """
        Return the local datetime of the next window boundary after current.
        """

        tz = self._effective_tz()

        if self.aggregation_interval_unit == "day":
            next_date = current.date() + timedelta(days=self.aggregation_interval)
            return datetime.combine(next_date, time.min, tzinfo=tz)

        raise NotImplementedError(
            f"Invalid temporal aggregation configuration. "
            f"Received unsupported aggregation interval unit: {self.aggregation_interval_unit!r}"
        )

    def _iter_windows(self, start_utc: datetime, end_utc: datetime):
        """
        Yield (window_start_utc, window_end_utc) pairs covering [start_utc, end_utc).

        Windows are aligned to unit boundaries in local time (e.g. midnight for days)
        and stepped using _next_window_start to handle DST transitions correctly.
        """

        current_local = self._window_start(start_utc)
        end_local = self._window_start(end_utc)

        while current_local < end_local:
            next_local = self._next_window_start(current_local)
            yield current_local.astimezone(dt_timezone.utc), next_local.astimezone(dt_timezone.utc)
            current_local = next_local

    @staticmethod
    def _boundary_value(
        target: datetime,
        timestamps: list[datetime],
        values: list[float],
        prev_idx: Optional[int],
        next_idx: Optional[int],
    ) -> Optional[float]:
        """
        Estimate the value at a window boundary by exact match or linear interpolation.

        If the observation immediately before (prev_idx) or after (next_idx) the boundary
        falls exactly on the target timestamp, that value is returned directly. Otherwise,
        if observations exist on both sides, the value is linearly interpolated. If only
        one side is available, that side's value is used as a flat extrapolation.

        Returns None if no usable observations are available on either side.
        """

        prev = None
        nxt = None

        if prev_idx is not None and 0 <= prev_idx < len(timestamps):
            prev = (timestamps[prev_idx], values[prev_idx])
        if next_idx is not None and 0 <= next_idx < len(timestamps):
            nxt = (timestamps[next_idx], values[next_idx])

        if prev is not None and prev[0] == target:
            return prev[1]
        if nxt is not None and nxt[0] == target:
            return nxt[1]

        if prev is not None and nxt is not None:
            t0, v0 = prev
            t1, v1 = nxt
            span = (t1 - t0).total_seconds()
            if span <= 0:
                return v1
            ratio = (target - t0).total_seconds() / span
            return v0 + ratio * (v1 - v0)

        if prev is not None:
            return prev[1]
        if nxt is not None:
            return nxt[1]

        return None

    def _aggregate_window(
        self,
        timestamps: list[datetime],
        values: list[float],
        window_start: datetime,
        window_end: datetime,
    ) -> Optional[float]:
        """
        Compute the configured aggregation statistic for a single window.

        Observations are selected from timestamps in [window_start, window_end) using
        binary search. Returns None if no observations fall within the window.

        For simple_mean: returns the arithmetic mean of all observations in the window.
        For last_value_of_period: returns the last observation in the window.
        For time_weighted_mean: computes a time-weighted mean via trapezoidal integration
            over the full window duration. Boundary values at window_start and window_end
            are estimated by _boundary_value if no observation falls exactly on those
            timestamps. Returns None if either boundary value cannot be determined.
        """

        if not timestamps or window_end <= window_start:
            return None

        left = bisect_left(timestamps, window_start)
        right = bisect_left(timestamps, window_end)

        if left == right:
            return None

        window_values = values[left:right]

        if self.aggregation_statistic == "simple_mean":
            return sum(window_values) / len(window_values)

        if self.aggregation_statistic == "last_value_of_period":
            return window_values[-1]

        # time_weighted_mean: trapezoidal integration over the window.
        start_value = self._boundary_value(
            target=window_start,
            timestamps=timestamps,
            values=values,
            prev_idx=(left - 1) if left > 0 else None,
            next_idx=left,
        )
        end_value = self._boundary_value(
            target=window_end,
            timestamps=timestamps,
            values=values,
            prev_idx=(right - 1) if right > 0 else None,
            next_idx=right if right < len(timestamps) else None,
        )

        if start_value is None or end_value is None:
            return None

        area_points: list[tuple[datetime, float]] = [(window_start, start_value)]
        for idx in range(left, right):
            ts = timestamps[idx]
            val = values[idx]
            if ts == window_start:
                area_points[0] = (ts, val)
                continue
            area_points.append((ts, val))

        if area_points[-1][0] == window_end:
            area_points[-1] = (window_end, end_value)
        else:
            area_points.append((window_end, end_value))

        total_area = 0.0
        for idx in range(1, len(area_points)):
            t0, v0 = area_points[idx - 1]
            t1, v1 = area_points[idx]
            span = (t1 - t0).total_seconds()
            if span > 0:
                total_area += (v0 + v1) * 0.5 * span

        duration = (window_end - window_start).total_seconds()
        if duration <= 0:
            return None

        result = total_area / duration

        return None if (math.isnan(result) or math.isinf(result)) else result
