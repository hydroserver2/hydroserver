import pytest
from django.core.exceptions import ValidationError

from processing.etl.models import DataConnection, DataConnectionNotification, Payload, PlaceholderVariable
from tests.processing.etl.factories import DataConnectionFactory, PayloadFactory, PlaceholderVariableFactory

pytestmark = pytest.mark.django_db


# --- DataConnection.clean(): auth header name/value must both be present or both absent -----


def test_full_clean_rejects_auth_header_name_without_value():
    data_connection = DataConnectionFactory.build(auth_header_name="X-Api-Key", auth_header_value=None)

    with pytest.raises(ValidationError):
        data_connection.full_clean()


def test_full_clean_rejects_auth_header_value_without_name():
    data_connection = DataConnectionFactory.build(auth_header_name=None, auth_header_value="secret")

    with pytest.raises(ValidationError):
        data_connection.full_clean()


def test_full_clean_allows_both_auth_header_fields_present():
    data_connection = DataConnectionFactory(auth_header_name="X-Api-Key", auth_header_value="secret")

    data_connection.full_clean()  # does not raise


def test_full_clean_allows_both_auth_header_fields_absent():
    data_connection = DataConnectionFactory(auth_header_name=None, auth_header_value=None)

    data_connection.full_clean()  # does not raise


# --- DataConnection.clean(): timezone_type/timezone consistency + offset/IANA validity -------


def test_full_clean_allows_valid_offset_timezone():
    data_connection = DataConnectionFactory(timezone_type="offset", timezone="-07:00")

    data_connection.full_clean()  # does not raise


def test_full_clean_allows_valid_offset_timezone_without_colon():
    data_connection = DataConnectionFactory(timezone_type="offset", timezone="-0700")

    data_connection.full_clean()  # does not raise


def test_full_clean_rejects_malformed_offset_timezone():
    data_connection = DataConnectionFactory.build(timezone_type="offset", timezone="not-an-offset")

    with pytest.raises(ValidationError):
        data_connection.full_clean()


def test_full_clean_rejects_out_of_range_offset_timezone():
    data_connection = DataConnectionFactory.build(timezone_type="offset", timezone="-15:00")

    with pytest.raises(ValidationError):
        data_connection.full_clean()


def test_full_clean_allows_valid_iana_timezone():
    data_connection = DataConnectionFactory(timezone_type="iana", timezone="America/Denver")

    data_connection.full_clean()  # does not raise


def test_full_clean_rejects_unknown_iana_timezone():
    data_connection = DataConnectionFactory.build(timezone_type="iana", timezone="Not/Real")

    with pytest.raises(ValidationError):
        data_connection.full_clean()


def test_full_clean_rejects_timezone_type_without_timezone():
    data_connection = DataConnectionFactory.build(timezone_type="iana", timezone=None)

    with pytest.raises(ValidationError):
        data_connection.full_clean()


def test_full_clean_rejects_timezone_without_timezone_type():
    data_connection = DataConnectionFactory.build(timezone_type=None, timezone="America/Denver")

    with pytest.raises(ValidationError):
        data_connection.full_clean()


def test_full_clean_allows_no_timezone_configured():
    data_connection = DataConnectionFactory(timezone_type=None, timezone=None)

    data_connection.full_clean()  # does not raise


# --- Payload.clean(): required fields per payload type + JMESPath validity ------------------


def test_full_clean_rejects_csv_payload_missing_required_fields():
    payload = PayloadFactory.build(delimiter=None)

    with pytest.raises(ValidationError):
        payload.full_clean()


def test_full_clean_allows_valid_csv_payload():
    payload = PayloadFactory()

    payload.full_clean()  # does not raise


def test_full_clean_rejects_json_payload_missing_jmespath():
    payload = PayloadFactory.build(json=True, jmespath=None)

    with pytest.raises(ValidationError):
        payload.full_clean()


def test_full_clean_rejects_invalid_jmespath_expression():
    payload = PayloadFactory.build(json=True, jmespath="[invalid(")

    with pytest.raises(ValidationError):
        payload.full_clean()


def test_full_clean_allows_valid_json_payload():
    payload = PayloadFactory(json=True)

    payload.full_clean()  # does not raise


def test_full_clean_allows_valid_timestamp_format():
    payload = PayloadFactory(timestamp_format="%Y-%m-%d %H:%M:%S")

    payload.full_clean()  # does not raise


# --- PlaceholderVariable.clean(): timestamp_format cross-field + strftime validity ----------


def test_full_clean_rejects_timestamp_format_on_disallowed_variable_type():
    placeholder = PlaceholderVariableFactory.build(variable_type="per_task", timestamp_format="%Y-%m-%d")

    with pytest.raises(ValidationError):
        placeholder.full_clean()


def test_full_clean_allows_timestamp_format_on_run_time():
    placeholder = PlaceholderVariableFactory(variable_type="run_time", timestamp_format="%Y-%m-%d")

    placeholder.full_clean()  # does not raise


def test_full_clean_rejects_invalid_strftime_format():
    placeholder = PlaceholderVariableFactory.build(
        variable_type="latest_observation_timestamp", timestamp_format="%q"
    )

    with pytest.raises(ValidationError):
        placeholder.full_clean()


def test_full_clean_allows_valid_strftime_format():
    placeholder = PlaceholderVariableFactory(
        variable_type="latest_observation_timestamp", timestamp_format="%Y-%m-%d %H:%M:%S"
    )

    placeholder.full_clean()  # does not raise


def test_full_clean_rejects_duplicate_name_and_type_per_data_connection():
    data_connection = DataConnectionFactory()
    PlaceholderVariableFactory(data_connection=data_connection, name="site_code", variable_type="per_task")
    duplicate = PlaceholderVariable(
        data_connection=data_connection, name="site_code", variable_type="per_task"
    )

    with pytest.raises(ValidationError):
        duplicate.full_clean()


# --- DataConnectionNotification.clean(): schedule + at least one recipient required ---------


def test_full_clean_rejects_notification_without_schedule():
    data_connection = DataConnectionFactory()
    notification = DataConnectionNotification.objects.create(data_connection=data_connection, periodic_task=None)

    with pytest.raises(ValidationError):
        notification.full_clean()


def test_full_clean_rejects_notification_without_recipients():
    from django_celery_beat.models import CrontabSchedule, PeriodicTask

    data_connection = DataConnectionFactory()
    crontab = CrontabSchedule.objects.create()
    periodic_task = PeriodicTask.objects.create(
        name=str(data_connection.pk), task="processing.etl.tasks.send_etl_notification_email", crontab=crontab
    )
    notification = DataConnectionNotification.objects.create(
        data_connection=data_connection, periodic_task=periodic_task
    )

    with pytest.raises(ValidationError):
        notification.full_clean()


def test_full_clean_allows_notification_with_schedule_and_recipient():
    from django_celery_beat.models import CrontabSchedule, PeriodicTask

    data_connection = DataConnectionFactory()
    crontab = CrontabSchedule.objects.create()
    periodic_task = PeriodicTask.objects.create(
        name=str(data_connection.pk), task="processing.etl.tasks.send_etl_notification_email", crontab=crontab
    )
    notification = DataConnectionNotification.objects.create(
        data_connection=data_connection, periodic_task=periodic_task
    )
    notification.recipients.create(email="alerts@example.com")

    notification.full_clean()  # does not raise
