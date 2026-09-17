import pytest
from django.core.exceptions import ValidationError

from processing.monitoring.models import MonitoringRule
from tests.core.iam.factories import WorkspaceFactory
from tests.core.sta.factories import DatastreamFactory, MonitoringSiteFactory
from tests.processing.monitoring.factories import MonitoringRuleFactory, MonitoringTaskFactory

pytestmark = pytest.mark.django_db


def _task_and_site(workspace=None):
    workspace = workspace or WorkspaceFactory()
    monitoring_site = MonitoringSiteFactory(workspace=workspace)
    task = MonitoringTaskFactory(monitoring_site=monitoring_site)
    return task, monitoring_site


# --- datastream site scoping -----------------------------------------------------------


def test_full_clean_rejects_datastream_from_another_monitoring_site():
    task, monitoring_site = _task_and_site()
    other_datastream = DatastreamFactory(monitoring_site=MonitoringSiteFactory(workspace=monitoring_site.workspace))
    rule = MonitoringRule(
        task=task, datastream=other_datastream, rule_type="missing_data",
        window_interval=1, window_interval_units="days",
    )

    with pytest.raises(ValidationError):
        rule.full_clean()


def test_full_clean_allows_datastream_in_same_monitoring_site():
    task, monitoring_site = _task_and_site()
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    rule = MonitoringRule(
        task=task, datastream=datastream, rule_type="missing_data",
        window_interval=1, window_interval_units="days",
    )

    rule.full_clean()  # does not raise


# --- window_interval / window_interval_units pairing -----------------------------------


def test_full_clean_rejects_window_interval_without_units():
    task, monitoring_site = _task_and_site()
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    rule = MonitoringRule(
        task=task, datastream=datastream, rule_type="missing_data",
        window_interval=1, window_interval_units=None,
    )

    with pytest.raises(ValidationError):
        rule.full_clean()


# --- range rule_type ---------------------------------------------------------------------


def test_full_clean_rejects_range_rule_missing_bounds():
    task, monitoring_site = _task_and_site()
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    rule = MonitoringRule(task=task, datastream=datastream, rule_type="range")

    with pytest.raises(ValidationError):
        rule.full_clean()


def test_full_clean_rejects_range_rule_min_not_less_than_max():
    task, monitoring_site = _task_and_site()
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    rule = MonitoringRule(task=task, datastream=datastream, rule_type="range", min_value=10, max_value=5)

    with pytest.raises(ValidationError):
        rule.full_clean()


def test_full_clean_rejects_range_rule_with_window():
    task, monitoring_site = _task_and_site()
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    rule = MonitoringRule(
        task=task, datastream=datastream, rule_type="range",
        min_value=1, max_value=5, window_interval=1, window_interval_units="days",
    )

    with pytest.raises(ValidationError):
        rule.full_clean()


def test_full_clean_allows_valid_range_rule():
    task, monitoring_site = _task_and_site()
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    rule = MonitoringRule(task=task, datastream=datastream, rule_type="range", min_value=1, max_value=5)

    rule.full_clean()  # does not raise


# --- rate_of_change rule_type -------------------------------------------------------------


def test_full_clean_rejects_rate_of_change_rule_missing_max_value():
    task, monitoring_site = _task_and_site()
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    rule = MonitoringRule(
        task=task, datastream=datastream, rule_type="rate_of_change",
        window_interval=1, window_interval_units="days",
    )

    with pytest.raises(ValidationError):
        rule.full_clean()


def test_full_clean_rejects_rate_of_change_rule_missing_window():
    task, monitoring_site = _task_and_site()
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    rule = MonitoringRule(task=task, datastream=datastream, rule_type="rate_of_change", max_value=5)

    with pytest.raises(ValidationError):
        rule.full_clean()


def test_full_clean_rejects_rate_of_change_rule_with_min_value():
    task, monitoring_site = _task_and_site()
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    rule = MonitoringRule(
        task=task, datastream=datastream, rule_type="rate_of_change",
        min_value=1, max_value=5, window_interval=1, window_interval_units="days",
    )

    with pytest.raises(ValidationError):
        rule.full_clean()


def test_full_clean_allows_valid_rate_of_change_rule():
    task, monitoring_site = _task_and_site()
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    rule = MonitoringRule(
        task=task, datastream=datastream, rule_type="rate_of_change",
        max_value=5, window_interval=1, window_interval_units="days",
    )

    rule.full_clean()  # does not raise


# --- persistence rule_type ----------------------------------------------------------------


def test_full_clean_rejects_persistence_rule_missing_window():
    task, monitoring_site = _task_and_site()
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    rule = MonitoringRule(task=task, datastream=datastream, rule_type="persistence")

    with pytest.raises(ValidationError):
        rule.full_clean()


def test_full_clean_allows_valid_persistence_rule():
    task, monitoring_site = _task_and_site()
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    rule = MonitoringRule(
        task=task, datastream=datastream, rule_type="persistence",
        window_interval=1, window_interval_units="days",
    )

    rule.full_clean()  # does not raise


# --- missing_data rule_type ----------------------------------------------------------------


def test_full_clean_rejects_missing_data_rule_missing_window():
    task, monitoring_site = _task_and_site()
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    rule = MonitoringRule(task=task, datastream=datastream, rule_type="missing_data")

    with pytest.raises(ValidationError):
        rule.full_clean()


def test_full_clean_rejects_missing_data_rule_with_min_value():
    task, monitoring_site = _task_and_site()
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    rule = MonitoringRule(
        task=task, datastream=datastream, rule_type="missing_data",
        min_value=1, window_interval=1, window_interval_units="days",
    )

    with pytest.raises(ValidationError):
        rule.full_clean()


def test_full_clean_allows_valid_missing_data_rule():
    task, monitoring_site = _task_and_site()
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    rule = MonitoringRule(
        task=task, datastream=datastream, rule_type="missing_data",
        window_interval=1, window_interval_units="days",
    )

    rule.full_clean()  # does not raise


# --- unique_monitoring_rule_type_per_datastream_task constraint ---------------------------


def test_full_clean_rejects_duplicate_rule_type_for_datastream_task():
    task, monitoring_site = _task_and_site()
    datastream = DatastreamFactory(monitoring_site=monitoring_site)
    MonitoringRuleFactory(task=task, datastream=datastream, rule_type="missing_data")
    duplicate = MonitoringRule(
        task=task, datastream=datastream, rule_type="missing_data",
        window_interval=1, window_interval_units="days",
    )

    with pytest.raises(ValidationError):
        duplicate.full_clean()
