import re
import pandas as pd
import pytz

from pydantic import ConfigDict, validate_call


TIMESTAMP_COL = "timestamp"
RESULT_COL = "result"

_OFFSET_RE = re.compile(r"^([+-])(\d{2}):?(\d{2})$")
_SIGN_FLIP = {"+": "-", "-": "+"}


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
