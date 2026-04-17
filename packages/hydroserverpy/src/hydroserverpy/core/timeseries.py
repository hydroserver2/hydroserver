import logging
import math
import re
import functools
import pytz
import polars as pl

from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from pydantic import ConfigDict, validate_call

from .duration import Duration, duration_to_us


TIMESTAMP_COL = "timestamp"
RESULT_COL = "result"

SCHEMA = pl.Schema(
    {
        TIMESTAMP_COL: pl.Datetime(time_unit="us", time_zone="UTC"),
        RESULT_COL: pl.Float64,
    }
)

_OFFSET_RE = re.compile(r"^([+-])(\d{2}):?(\d{2})$")
_SIGN_FLIP = {"+": "-", "-": "+"}

logger = logging.getLogger(__name__)


def accept_pandas(func):
    """
    Decorator that converts pandas DataFrame arguments to Polars before calling
    func, then converts the result back to pandas if any input was a pandas DataFrame.

    Handles plain DataFrame args/kwargs and dict-of-DataFrame kwargs (e.g., the
    'inputs' parameter of apply_expression). Casts the timestamp column to the
    canonical schema dtype on conversion in.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            import pandas as pd
        except ImportError:
            return func(*args, **kwargs)

        was_pandas = False

        def _convert(obj):
            nonlocal was_pandas
            if isinstance(obj, pd.DataFrame):
                was_pandas = True
                pl_df = pl.from_pandas(obj)
                if TIMESTAMP_COL in pl_df.schema:
                    pl_df = pl_df.with_columns(
                        pl.col(TIMESTAMP_COL).cast(SCHEMA[TIMESTAMP_COL])
                    )
                return pl_df
            return obj

        new_args = [_convert(a) for a in args]
        new_kwargs = {
            k: (
                {ik: _convert(iv) for ik, iv in v.items()}
                if isinstance(v, dict) else _convert(v)
            )
            for k, v in kwargs.items()
        }

        result = func(*new_args, **new_kwargs)

        if was_pandas and isinstance(result, pl.DataFrame):
            return result.to_pandas()

        return result

    return wrapper


@validate_call(config=ConfigDict(arbitrary_types_allowed=True))
def validate_timeseries(
    df: pl.DataFrame
) -> None:
    """
    Raise ValueError if df does not match the canonical schema.

    Checks that both required columns are present with the correct dtypes.
    Extra columns are allowed.
    """

    if missing := [column for column in SCHEMA.keys() if column not in df.schema]:
        raise ValueError(
            f"Timeseries DataFrame is missing required columns: {missing}."
        )

    for col_name, expected_dtype in SCHEMA.items():
        if df.schema[col_name] != expected_dtype:
            raise ValueError(
                f"Timeseries DataFrame has invalid dtype for column '{col_name}': "
                f"{df.schema[col_name]}; expected {expected_dtype}."
            )


@validate_call(config=ConfigDict(arbitrary_types_allowed=True))
def align_timeseries(
    df: pl.DataFrame,
    *,
    interval: Duration,
    anchor: Optional[datetime] = None,
    on_missing: Literal["drop", "interpolate", "stop", "raise"] = "drop",
    interpolation: Literal["linear", "nearest"] = "linear",
    max_gap: Optional[Duration] = None,
) -> pl.DataFrame:
    """
    Align a timeseries DataFrame to a regular interval grid.

    Generates a grid spanning the full range of the input timestamps and
    left-joins the input onto it. Grid points with no matching observation
    are handled according to on_missing.
    """

    validate_timeseries(df)

    if max_gap is not None and on_missing != "interpolate":
        raise ValueError("max_gap requires on_missing='interpolate'.")

    if interpolation != "linear" and on_missing != "interpolate":
        raise ValueError("interpolation requires on_missing='interpolate'.")

    logger.debug(
        "Aligning %d row(s) to grid (interval=%r, onMissing=%r, interpolation=%r, maxGap=%r).",
        df.height, interval, on_missing, interpolation, max_gap,
    )

    interval_us = duration_to_us(interval)

    # Normalize anchor to UTC. Defaults to the Unix epoch, which produces
    # round-unit grid boundaries (e.g. "1h" → every hour on the hour).
    anchor_utc = (
        anchor.replace(tzinfo=timezone.utc) if anchor and not anchor.tzinfo
        else anchor or datetime(1970, 1, 1, tzinfo=timezone.utc)
    )
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)

    grid_start = df[TIMESTAMP_COL].min()
    grid_end = df[TIMESTAMP_COL].max()

    # Find the first grid point >= grid_start that is aligned to the anchor.
    # ceil((grid_start - anchor) / interval) gives the number of steps needed.
    delta_us = int((grid_start.replace(tzinfo=timezone.utc) - epoch).total_seconds() * 1_000_000)
    anchor_us = int((anchor_utc - epoch).total_seconds() * 1_000_000)
    n = math.ceil((delta_us - anchor_us) / interval_us)
    grid_start = anchor_utc + timedelta(microseconds=n * interval_us)

    grid = pl.DataFrame({
        TIMESTAMP_COL: pl.datetime_range(
            grid_start, grid_end, interval,
            time_unit="us", time_zone="UTC", eager=True,
        )
    })

    # Left join preserves all grid points; observations that fall exactly on a
    # grid timestamp are matched, all others produce null in RESULT_COL.
    aligned_timeseries = grid.join(
        df.select([TIMESTAMP_COL, RESULT_COL]),
        on=TIMESTAMP_COL,
        how="left",
    )

    grid_size = aligned_timeseries.height
    missing_count = aligned_timeseries[RESULT_COL].null_count()
    logger.debug(
        "Grid has %d point(s); %d matched, %d missing.",
        grid_size, grid_size - missing_count, missing_count,
    )

    if on_missing == "raise":
        if missing_count > 0:
            raise ValueError(
                "Timeseries has missing values at one or more grid points."
            )
        logger.info("Alignment produced %d row(s) from %d input row(s).", aligned_timeseries.height, df.height)
        return aligned_timeseries

    if on_missing == "stop":
        # Truncate at the first null — returns a contiguous series up to the first gap.
        first_null = aligned_timeseries[RESULT_COL].is_null().arg_true()
        if len(first_null) > 0:
            aligned_timeseries = aligned_timeseries.slice(0, first_null[0])
        logger.info("Alignment produced %d row(s) from %d input row(s).", aligned_timeseries.height, df.height)
        return aligned_timeseries

    if on_missing == "drop":
        result = aligned_timeseries.drop_nulls(subset=[RESULT_COL])
        logger.info("Alignment produced %d row(s) from %d input row(s).", result.height, df.height)
        return result

    # interpolate: fill nulls using the chosen method.
    # With max_gap, gaps wider than the threshold are left as null rather than
    # interpolated — prevents silently bridging long outages.
    max_gap_us = duration_to_us(max_gap) if max_gap else None

    if max_gap_us is None:
        result = aligned_timeseries.with_columns(pl.col(RESULT_COL).interpolate(method=interpolation))
        logger.info("Alignment produced %d row(s) from %d input row(s).", result.height, df.height)
        return result

    # Mark which rows were originally null and record the timestamp of each
    # real observation so we can measure the gap around each null later.
    aligned_timeseries = aligned_timeseries.with_columns([
        pl.col(RESULT_COL).is_null().alias("_was_null"),
        pl.when(pl.col(RESULT_COL).is_not_null())
          .then(pl.col(TIMESTAMP_COL).cast(pl.Int64))
          .otherwise(None)
          .alias("_real_ts"),
    ]).with_columns([
        # Forward/backward fill gives each null row the timestamps of its
        # nearest real neighbors on both sides.
        pl.col("_real_ts").forward_fill().alias("_prev_real_ts"),
        pl.col("_real_ts").backward_fill().alias("_next_real_ts"),
    ]).with_columns(
        pl.col(RESULT_COL).interpolate(method=interpolation)
    ).with_columns(
        # Restore null for any row that was interpolated across a gap wider
        # than max_gap (measured between the surrounding real observations).
        pl.when(
            pl.col("_was_null") &
            ((pl.col("_next_real_ts") - pl.col("_prev_real_ts")) > max_gap_us)
        ).then(None)
        .otherwise(pl.col(RESULT_COL))
        .alias(RESULT_COL)
    ).drop(["_was_null", "_real_ts", "_prev_real_ts", "_next_real_ts"])

    logger.info("Alignment produced %d row(s) from %d input row(s).", aligned_timeseries.height, df.height)

    return aligned_timeseries


def normalize_tz(tz: str) -> str:
    """
    Normalize a timezone string to a Polars and zoneinfo compatible IANA name.

    Accepts any of the following:
      - IANA timezone names (e.g. 'America/Denver', 'UTC')
      - Etc/GMT offset names (e.g. 'Etc/GMT+5', 'Etc/GMT-7')
      - UTC offset strings in ±HHMM or ±HH:MM format (e.g. '+0500', '-07:00')

    UTC offset strings are converted to Etc/GMT±H names. Note that Etc/GMT sign
    convention is the reverse of the UTC offset sign (POSIX legacy):
      '+05:00' (UTC+5) → 'Etc/GMT-5'
      '-07:00' (UTC-7) → 'Etc/GMT+7'

    Only whole-hour offsets are supported via the offset format. For non-whole-hour
    offsets (e.g., UTC+5:30), use the IANA name directly (e.g. 'Asia/Kolkata').

    Raises ValueError for unrecognized or invalid input.
    """

    offset_match = _OFFSET_RE.fullmatch(tz)

    if offset_match:
        sign, hours, minutes = offset_match.group(1), int(offset_match.group(2)), int(offset_match.group(3))

        if minutes != 0:
            raise ValueError(
                f"UTC offset '{tz}' has a non-zero minute component. "
                "Use an IANA timezone name for non-whole-hour offsets "
                "(e.g. 'Asia/Kolkata' for UTC+5:30)."
            )
        if hours > 14:
            raise ValueError(
                f"UTC offset '{tz}' is out of the valid range (±14:00)."
            )
        if hours == 0:
            return "UTC"

        # Etc/GMT sign is opposite to the UTC offset sign (POSIX convention)
        return f"Etc/GMT{_SIGN_FLIP[sign]}{hours}"

    if tz not in pytz.all_timezones_set:
        raise ValueError(
            f"Unknown timezone '{tz}'. "
            "Provide a valid IANA timezone name (e.g. 'America/Denver') "
            "or a UTC offset in ±HHMM or ±HH:MM format (e.g. '-0700' or '-07:00')."
        )

    return tz
