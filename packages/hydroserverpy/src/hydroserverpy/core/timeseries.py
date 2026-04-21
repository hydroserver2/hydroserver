import logging
import math
import re
import numpy as np
import pandas as pd
import pytz

from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from pydantic import ConfigDict, validate_call

from .duration import Duration, duration_to_us


TIMESTAMP_COL = "timestamp"
RESULT_COL = "result"

_OFFSET_RE = re.compile(r"^([+-])(\d{2}):?(\d{2})$")
_SIGN_FLIP = {"+": "-", "-": "+"}

logger = logging.getLogger(__name__)


@validate_call(config=ConfigDict(arbitrary_types_allowed=True))
def validate_timeseries(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate and coerce a DataFrame to the canonical timeseries schema.

    Attempts to coerce the timestamp column to datetime64[us, UTC] and the
    result column to float64. Raises ValueError if required columns are missing,
    if any timestamp values are NaT, or if any result values are NaN after coercion.
    Extra columns are preserved unchanged.
    """

    if missing := [col for col in [TIMESTAMP_COL, RESULT_COL] if col not in df.columns]:
        raise ValueError(
            f"Timeseries DataFrame is missing required columns: {missing}."
        )

    df = df.copy()

    ts_coerced = pd.to_datetime(df[TIMESTAMP_COL], utc=True, errors="coerce").dt.as_unit("us")
    if ts_coerced.isna().any():
        raise ValueError(
            f"Column '{TIMESTAMP_COL}' contains NaT or values that could not be converted to UTC datetime."
        )
    df[TIMESTAMP_COL] = ts_coerced

    result_coerced = pd.to_numeric(df[RESULT_COL], errors="coerce").astype("float64")
    if result_coerced.isna().any():
        raise ValueError(
            f"Column '{RESULT_COL}' contains NaN or non-numeric values that could not be converted to float."
        )
    df[RESULT_COL] = result_coerced

    return df


@validate_call(config=ConfigDict(arbitrary_types_allowed=True))
def align_timeseries(
    df: pd.DataFrame,
    *,
    interval: Duration,
    anchor: Optional[datetime] = None,
    on_missing: Literal["drop", "interpolate", "stop", "raise"] = "drop",
    interpolation: Literal["linear", "nearest"] = "linear",
    max_gap: Optional[Duration] = None,
) -> pd.DataFrame:
    """
    Align a timeseries DataFrame to a regular interval grid.

    Generates a grid spanning the full range of the input timestamps and
    re-indexes the input onto it. Grid points with no matching observation
    are handled according to on_missing.
    """

    df = validate_timeseries(df)

    if max_gap is not None and on_missing != "interpolate":
        raise ValueError("max_gap requires on_missing='interpolate'.")

    if interpolation != "linear" and on_missing != "interpolate":
        raise ValueError("interpolation requires on_missing='interpolate'.")

    logger.debug(
        "Aligning %d row(s) to grid (interval=%r, onMissing=%r, interpolation=%r, maxGap=%r).",
        len(df), interval, on_missing, interpolation, max_gap,
    )

    interval_us = duration_to_us(interval)

    # Normalize anchor to UTC. Defaults to the Unix epoch, which produces
    # round-unit grid boundaries (e.g. "1h" → every hour on the hour).
    anchor_utc = (
        anchor.replace(tzinfo=timezone.utc) if anchor and not anchor.tzinfo
        else anchor or datetime(1970, 1, 1, tzinfo=timezone.utc)
    )
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)

    grid_start_dt = df[TIMESTAMP_COL].min().to_pydatetime()
    grid_end_dt = df[TIMESTAMP_COL].max().to_pydatetime()

    # Find the first grid point >= grid_start that is aligned to the anchor.
    # ceil((grid_start - anchor) / interval) gives the number of steps needed.
    delta_us = int((grid_start_dt - epoch).total_seconds() * 1_000_000)
    anchor_us = int((anchor_utc - epoch).total_seconds() * 1_000_000)
    n = math.ceil((delta_us - anchor_us) / interval_us)
    grid_start = anchor_utc + timedelta(microseconds=n * interval_us)

    grid_idx = pd.date_range(
        start=grid_start,
        end=grid_end_dt,
        freq=pd.Timedelta(microseconds=interval_us),
        tz="UTC",
    ).as_unit("us")

    # Reindex preserves all grid points; observations that fall exactly on a
    # grid timestamp are matched, all others produce NaN in RESULT_COL.
    aligned = (
        df.set_index(TIMESTAMP_COL)[RESULT_COL]
        .reindex(grid_idx)
        .rename_axis(TIMESTAMP_COL)
        .reset_index()
    )

    grid_size = len(aligned)
    missing_count = int(aligned[RESULT_COL].isna().sum())
    logger.debug(
        "Grid has %d point(s); %d matched, %d missing.",
        grid_size, grid_size - missing_count, missing_count,
    )

    if on_missing == "raise":
        if missing_count > 0:
            raise ValueError(
                "Timeseries has missing values at one or more grid points."
            )
        logger.info("Alignment produced %d row(s) from %d input row(s).", len(aligned), len(df))
        return aligned

    if on_missing == "stop":
        # Truncate at the first NaN — returns a contiguous series up to the first gap.
        first_null = np.where(aligned[RESULT_COL].isna())[0]
        if len(first_null) > 0:
            aligned = aligned.iloc[:first_null[0]].reset_index(drop=True)
        logger.info("Alignment produced %d row(s) from %d input row(s).", len(aligned), len(df))
        return aligned

    if on_missing == "drop":
        result = aligned.dropna(subset=[RESULT_COL]).reset_index(drop=True)
        logger.info("Alignment produced %d row(s) from %d input row(s).", len(result), len(df))
        return result

    # interpolate: fill NaNs using the chosen method.
    # With max_gap, gaps wider than the threshold are left as NaN rather than
    # interpolated — prevents silently bridging long outages.
    max_gap_us = duration_to_us(max_gap) if max_gap else None

    if max_gap_us is None:
        aligned = aligned.copy()
        aligned[RESULT_COL] = aligned[RESULT_COL].interpolate(method=interpolation)
        logger.info("Alignment produced %d row(s) from %d input row(s).", len(aligned), len(df))
        return aligned

    # Mark which rows were originally NaN and record the timestamp (in µs since
    # epoch) of each real observation so we can measure the gap around each null.
    was_null = aligned[RESULT_COL].isna()
    epoch_ts = pd.Timestamp("1970-01-01", tz="UTC")
    real_ts_us = (
        (aligned[TIMESTAMP_COL] - epoch_ts)
        .dt.total_seconds()
        .mul(1_000_000)
        .where(~was_null)
    )
    prev_real_ts_us = real_ts_us.ffill()
    next_real_ts_us = real_ts_us.bfill()

    aligned = aligned.copy()
    aligned[RESULT_COL] = aligned[RESULT_COL].interpolate(method=interpolation)

    # Restore NaN for any row interpolated across a gap wider than max_gap.
    too_wide = was_null & ((next_real_ts_us - prev_real_ts_us) > max_gap_us)
    aligned.loc[too_wide, RESULT_COL] = np.nan

    logger.info("Alignment produced %d row(s) from %d input row(s).", len(aligned), len(df))
    return aligned


def normalize_tz(tz: str) -> str:
    """
    Normalize a timezone string to a pandas and zoneinfo compatible IANA name.

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
