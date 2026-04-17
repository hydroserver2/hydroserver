import pytest
from hydroserverpy.core.duration import _validate_duration, duration_to_us


# ---------------------------------------------------------------------------
# _validate_duration
# ---------------------------------------------------------------------------

class TestValidateDuration:

    @pytest.mark.parametrize("s", ["1m", "30m", "60m", "1h", "24h", "1d", "7d", "1w", "2w"])
    def test_valid_strings_are_accepted(self, s):
        assert _validate_duration(s) == s

    def test_returns_the_input_string(self):
        assert _validate_duration("15m") == "15m"

    @pytest.mark.parametrize("s", ["1s", "1y", "1ms", "1us", "m", "1", ""])
    def test_unsupported_units_raise_value_error(self, s):
        with pytest.raises(ValueError):
            _validate_duration(s)

    @pytest.mark.parametrize("s", ["1M", "1H", "1D", "1W"])
    def test_uppercase_units_are_rejected(self, s):
        with pytest.raises(ValueError):
            _validate_duration(s)

    def test_decimal_value_is_rejected(self):
        with pytest.raises(ValueError):
            _validate_duration("1.5h")

    def test_negative_value_is_rejected(self):
        with pytest.raises(ValueError):
            _validate_duration("-1h")


# ---------------------------------------------------------------------------
# duration_to_us
# ---------------------------------------------------------------------------

class TestDurationToUs:

    def test_one_minute(self):
        assert duration_to_us("1m") == 60_000_000

    def test_thirty_minutes(self):
        assert duration_to_us("30m") == 30 * 60_000_000

    def test_one_hour(self):
        assert duration_to_us("1h") == 3_600_000_000

    def test_twenty_four_hours(self):
        assert duration_to_us("24h") == 24 * 3_600_000_000

    def test_one_day(self):
        assert duration_to_us("1d") == 86_400_000_000

    def test_seven_days(self):
        assert duration_to_us("7d") == 7 * 86_400_000_000

    def test_one_week(self):
        assert duration_to_us("1w") == 604_800_000_000

    def test_two_weeks(self):
        assert duration_to_us("2w") == 2 * 604_800_000_000

    def test_hours_and_days_agree(self):
        assert duration_to_us("24h") == duration_to_us("1d")

    def test_days_and_weeks_agree(self):
        assert duration_to_us("7d") == duration_to_us("1w")

    def test_result_is_int(self):
        assert isinstance(duration_to_us("1h"), int)
