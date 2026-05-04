import uuid
import numpy as np
import pandas as pd
import pytest
from types import SimpleNamespace
from django.utils import timezone

from hydroserverpy.core.timeseries import TIMESTAMP_COL, RESULT_COL
from processing.monitoring.services.rule import MonitoringRuleService
from processing.monitoring.models import MonitoringRule

rule_service = MonitoringRuleService()

TASK1 = "019d0001-0000-7000-8000-000000000001"  # private workspace
TASK2 = "019d0001-0000-7000-8000-000000000002"  # public workspace
RULE1 = "019d0002-0000-7000-8000-000000000001"  # range rule on TASK1/dd1f9293

# dd1f9293 belongs to thing 819260c8 (same thing as TASK1)
TASK1_DATASTREAM = "dd1f9293-ce29-4b6a-88e6-d65110d1be65"
# 27c70b41 belongs to thing 3b7818af — wrong thing for TASK1
OTHER_THING_DATASTREAM = "27c70b41-e845-40ea-8cc7-d1b40f89816b"
NONEXISTENT = "00000000-0000-0000-0000-000000000000"


@pytest.mark.parametrize(
    "principal, rule_type_filter, expected_count, error, error_fragment",
    [
        # Successful reads — TASK1 has 1 rule
        ("owner", None, 1, None, None),
        ("editor", None, 1, None, None),
        ("viewer", None, 1, None, None),
        ("admin", None, 1, None, None),
        # API key cannot see private workspace task
        ("apikey", None, None, LookupError, "does not exist"),
        # Unaffiliated
        ("unaffiliated", None, None, LookupError, "does not exist"),
        # rule_type filter
        ("owner", ["range"], 1, None, None),
        ("owner", ["rate_of_change"], 0, None, None),
    ],
)
def test_list_monitoring_rules(
    get_principal, principal, rule_type_filter, expected_count, error, error_fragment
):
    kwargs = {"task": uuid.UUID(TASK1), "principal": get_principal(principal)}
    if rule_type_filter is not None:
        kwargs["rule_type"] = rule_type_filter

    if error:
        with pytest.raises(error) as exc_info:
            rule_service.get_collection(**kwargs)
        assert error_fragment in str(exc_info.value)
    else:
        count, rules = rule_service.get_collection(**kwargs)
        assert count == expected_count


def test_list_monitoring_rules_datastream_filter(get_principal):
    count, rules = rule_service.get_collection(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        datastream=[uuid.UUID(TASK1_DATASTREAM)],
    )
    assert count == 1

    count, rules = rule_service.get_collection(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        datastream=[uuid.UUID(OTHER_THING_DATASTREAM)],
    )
    assert count == 0


def test_list_monitoring_rules_nonexistent_task(get_principal):
    with pytest.raises(LookupError) as exc_info:
        rule_service.get_collection(
            task=uuid.UUID(NONEXISTENT),
            principal=get_principal("owner"),
        )
    assert "does not exist" in str(exc_info.value)


@pytest.mark.parametrize(
    "principal, expected_type, error, error_fragment",
    [
        ("owner", "range", None, None),
        ("editor", "range", None, None),
        ("viewer", "range", None, None),
        ("admin", "range", None, None),
        # API key cannot see private workspace task
        ("apikey", None, LookupError, "does not exist"),
        ("unaffiliated", None, LookupError, "does not exist"),
    ],
)
def test_get_monitoring_rule(get_principal, principal, expected_type, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            rule_service.get(
                rule=uuid.UUID(RULE1),
                task=uuid.UUID(TASK1),
                principal=get_principal(principal),
            )
        assert error_fragment in str(exc_info.value)
    else:
        result = rule_service.get(
            rule=uuid.UUID(RULE1),
            task=uuid.UUID(TASK1),
            principal=get_principal(principal),
        )
        assert result.rule_type == expected_type


def test_get_monitoring_rule_wrong_task(get_principal):
    with pytest.raises(LookupError) as exc_info:
        rule_service.get(
            rule=uuid.UUID(RULE1),
            task=uuid.UUID(TASK2),  # RULE1 belongs to TASK1, not TASK2
            principal=get_principal("owner"),
        )
    assert "does not exist" in str(exc_info.value)


def test_get_monitoring_rule_nonexistent(get_principal):
    with pytest.raises(LookupError) as exc_info:
        rule_service.get(
            rule=uuid.UUID(NONEXISTENT),
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
        )
    assert "does not exist" in str(exc_info.value)


@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("admin", None, None),
        # View-only
        ("viewer", PermissionError, "do not have permission"),
        # No view access to private workspace task
        ("apikey", LookupError, "does not exist"),
        ("unaffiliated", LookupError, "does not exist"),
    ],
)
def test_create_monitoring_rule(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            rule_service.create(
                task=uuid.UUID(TASK1),
                principal=get_principal(principal),
                datastream_id=uuid.UUID(TASK1_DATASTREAM),
                rule_type="rate_of_change",
                max_value=5.0,
                window_interval=1,
                window_interval_units="hours",
            )
        assert error_fragment in str(exc_info.value)
    else:
        result = rule_service.create(
            task=uuid.UUID(TASK1),
            principal=get_principal(principal),
            datastream_id=uuid.UUID(TASK1_DATASTREAM),
            rule_type="rate_of_change",
            max_value=5.0,
            window_interval=1,
            window_interval_units="hours",
        )
        assert result.rule_type == "rate_of_change"
        assert result.max_value == 5.0


def test_create_monitoring_rule_nonexistent_task(get_principal):
    with pytest.raises(LookupError) as exc_info:
        rule_service.create(
            task=uuid.UUID(NONEXISTENT),
            principal=get_principal("owner"),
            datastream_id=uuid.UUID(TASK1_DATASTREAM),
            rule_type="range",
            min_value=0.0,
        )
    assert "does not exist" in str(exc_info.value)


def test_create_monitoring_rule_wrong_thing_datastream(get_principal):
    """Datastream must belong to the task's thing."""
    with pytest.raises(LookupError) as exc_info:
        rule_service.create(
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
            datastream_id=uuid.UUID(OTHER_THING_DATASTREAM),  # belongs to different thing
            rule_type="range",
            min_value=0.0,
        )
    assert "does not exist" in str(exc_info.value)


def test_create_monitoring_rule_duplicate_rejected(get_principal):
    """(task, datastream, rule_type) must be unique."""
    with pytest.raises(ValueError) as exc_info:
        rule_service.create(
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
            datastream_id=uuid.UUID(TASK1_DATASTREAM),
            rule_type="range",  # RULE1 already exists with this type
            min_value=10.0,
        )
    assert "already exists" in str(exc_info.value)


# --- Rule type creation ---

def test_create_range_rule(get_principal):
    result = rule_service.create(
        task=uuid.UUID(TASK2),
        principal=get_principal("owner"),
        datastream_id=uuid.UUID(OTHER_THING_DATASTREAM),
        rule_type="range",
        min_value=0.0,
        max_value=50.0,
    )
    assert result.rule_type == "range"
    assert result.min_value == 0.0
    assert result.max_value == 50.0


def test_create_rate_of_change_rule(get_principal):
    result = rule_service.create(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        datastream_id=uuid.UUID(TASK1_DATASTREAM),
        rule_type="rate_of_change",
        max_value=2.5,
        window_interval=30,
        window_interval_units="minutes",
    )
    assert result.rule_type == "rate_of_change"
    assert result.max_value == 2.5
    assert result.window_interval == 30
    assert result.window_interval_units == "minutes"


def test_create_persistence_rule(get_principal):
    result = rule_service.create(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        datastream_id=uuid.UUID(TASK1_DATASTREAM),
        rule_type="persistence",
        window_interval=2,
        window_interval_units="hours",
    )
    assert result.rule_type == "persistence"
    assert result.window_interval == 2


def test_create_persistence_rule_with_range(get_principal):
    result = rule_service.create(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        datastream_id=uuid.UUID(TASK1_DATASTREAM),
        rule_type="persistence",
        min_value=0.0,
        max_value=10.0,
        window_interval=1,
        window_interval_units="days",
    )
    assert result.min_value == 0.0
    assert result.max_value == 10.0


def test_create_missing_data_rule(get_principal):
    result = rule_service.create(
        task=uuid.UUID(TASK1),
        principal=get_principal("owner"),
        datastream_id=uuid.UUID(TASK1_DATASTREAM),
        rule_type="missing_data",
        window_interval=4,
        window_interval_units="hours",
    )
    assert result.rule_type == "missing_data"
    assert result.window_interval == 4


# --- Validation ---

def test_range_rule_requires_min_or_max(get_principal):
    with pytest.raises(ValueError) as exc_info:
        rule_service.create(
            task=uuid.UUID(TASK2),
            principal=get_principal("owner"),
            datastream_id=uuid.UUID(OTHER_THING_DATASTREAM),
            rule_type="range",
        )
    assert "min_value or max_value" in str(exc_info.value)


def test_range_rule_min_must_be_less_than_max(get_principal):
    with pytest.raises(ValueError) as exc_info:
        rule_service.create(
            task=uuid.UUID(TASK2),
            principal=get_principal("owner"),
            datastream_id=uuid.UUID(OTHER_THING_DATASTREAM),
            rule_type="range",
            min_value=100.0,
            max_value=0.0,
        )
    assert "min_value must be less than max_value" in str(exc_info.value)


def test_rate_of_change_requires_max_value(get_principal):
    with pytest.raises(ValueError) as exc_info:
        rule_service.create(
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
            datastream_id=uuid.UUID(TASK1_DATASTREAM),
            rule_type="rate_of_change",
            window_interval=1,
            window_interval_units="hours",
        )
    assert "max_value" in str(exc_info.value)


def test_rate_of_change_requires_window(get_principal):
    with pytest.raises(ValueError) as exc_info:
        rule_service.create(
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
            datastream_id=uuid.UUID(TASK1_DATASTREAM),
            rule_type="rate_of_change",
            max_value=1.0,
        )
    assert "window_interval" in str(exc_info.value)


def test_window_units_required_with_window(get_principal):
    with pytest.raises(ValueError) as exc_info:
        rule_service.create(
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
            datastream_id=uuid.UUID(TASK1_DATASTREAM),
            rule_type="persistence",
            window_interval=1,
            # window_interval_units omitted
        )
    assert "window_interval_units" in str(exc_info.value)


@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("admin", None, None),
        # View-only
        ("viewer", PermissionError, "do not have permission"),
        # Not visible
        ("apikey", LookupError, "does not exist"),
        ("unaffiliated", LookupError, "does not exist"),
    ],
)
def test_update_monitoring_rule(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            rule_service.update(
                rule=uuid.UUID(RULE1),
                task=uuid.UUID(TASK1),
                principal=get_principal(principal),
                max_value=200.0,
            )
        assert error_fragment in str(exc_info.value)
    else:
        result = rule_service.update(
            rule=uuid.UUID(RULE1),
            task=uuid.UUID(TASK1),
            principal=get_principal(principal),
            max_value=200.0,
        )
        assert result.max_value == 200.0


def test_update_monitoring_rule_nonexistent(get_principal):
    with pytest.raises(LookupError) as exc_info:
        rule_service.update(
            rule=uuid.UUID(NONEXISTENT),
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
            max_value=200.0,
        )
    assert "does not exist" in str(exc_info.value)


def test_update_monitoring_rule_validation_applied(get_principal):
    """Update must still pass validation — clearing max_value when min_value is also null fails."""
    with pytest.raises(ValueError) as exc_info:
        rule_service.update(
            rule=uuid.UUID(RULE1),
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
            min_value=None,
            max_value=None,
        )
    assert "min_value or max_value" in str(exc_info.value)


@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("admin", None, None),
        # View-only
        ("viewer", PermissionError, "do not have permission"),
        # Not visible
        ("apikey", LookupError, "does not exist"),
        ("unaffiliated", LookupError, "does not exist"),
    ],
)
def test_delete_monitoring_rule(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            rule_service.delete(
                rule=uuid.UUID(RULE1),
                task=uuid.UUID(TASK1),
                principal=get_principal(principal),
            )
        assert error_fragment in str(exc_info.value)
    else:
        rule_service.delete(
            rule=uuid.UUID(RULE1),
            task=uuid.UUID(TASK1),
            principal=get_principal(principal),
        )
        assert not MonitoringRule.objects.filter(pk=uuid.UUID(RULE1)).exists()


def test_delete_monitoring_rule_nonexistent(get_principal):
    with pytest.raises(LookupError) as exc_info:
        rule_service.delete(
            rule=uuid.UUID(NONEXISTENT),
            task=uuid.UUID(TASK1),
            principal=get_principal("owner"),
        )
    assert "does not exist" in str(exc_info.value)


# --- check_rule: empty dataframe ---

def _empty_df():
    return pd.DataFrame({
        TIMESTAMP_COL: pd.Series([], dtype="datetime64[us, UTC]"),
        RESULT_COL: pd.Series([], dtype=np.float64),
    })


def test_check_rule_range_empty_df():
    rule = SimpleNamespace(rule_type="range", min_value=0.0, max_value=100.0)
    datastream = SimpleNamespace(no_data_value=None)
    result = MonitoringRuleService.check_rule(rule, _empty_df(), datastream)
    assert result["violated"] is False
    assert result["violation_count"] == 0


def test_check_rule_rate_of_change_empty_df():
    rule = SimpleNamespace(rule_type="rate_of_change", max_value=5.0, window_interval=1, window_interval_units="hours")
    datastream = SimpleNamespace(no_data_value=None)
    result = MonitoringRuleService.check_rule(rule, _empty_df(), datastream)
    assert result["violated"] is False
    assert result["violation_count"] == 0


def test_check_rule_persistence_empty_df():
    rule = SimpleNamespace(rule_type="persistence", min_value=None, max_value=None, window_interval=1, window_interval_units="hours")
    datastream = SimpleNamespace(no_data_value=None)
    result = MonitoringRuleService.check_rule(rule, _empty_df(), datastream)
    assert result["violated"] is False
    assert result["violation_count"] == 0


def test_check_rule_missing_data_no_observations():
    """missing_data rule on a datastream with no observations should fire."""
    rule = SimpleNamespace(rule_type="missing_data", window_interval=1, window_interval_units="hours")
    datastream = SimpleNamespace(no_data_value=None, phenomenon_end_time=None)
    result = MonitoringRuleService.check_rule(rule, _empty_df(), datastream)
    assert result["violated"] is True
    assert result["violation_count"] == 1


def test_check_rule_missing_data_recent_observation():
    rule = SimpleNamespace(rule_type="missing_data", window_interval=1, window_interval_units="hours")
    datastream = SimpleNamespace(no_data_value=None, phenomenon_end_time=timezone.now())
    result = MonitoringRuleService.check_rule(rule, _empty_df(), datastream)
    assert result["violated"] is False
    assert result["violation_count"] == 0
