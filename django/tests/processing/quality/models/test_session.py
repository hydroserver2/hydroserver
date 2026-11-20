from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from processing.quality.models import QCSession
from tests.core.sta.factories import DatastreamFactory
from tests.processing.quality.factories import QCHistoryFactory, QCSessionFactory

pytestmark = pytest.mark.django_db


def test_full_clean_rejects_end_before_start():
    now = timezone.now()
    history = QCHistoryFactory()
    session = QCSession(
        history=history, phenomenon_time_start=now, phenomenon_time_end=now - timedelta(days=1),
        source_checksum="0" * 16,
    )

    with pytest.raises(ValidationError):
        session.full_clean()


def test_full_clean_rejects_end_equal_start():
    now = timezone.now()
    history = QCHistoryFactory()
    session = QCSession(
        history=history, phenomenon_time_start=now, phenomenon_time_end=now, source_checksum="0" * 16,
    )

    with pytest.raises(ValidationError):
        session.full_clean()


def test_full_clean_rejects_history_without_source_datastream():
    history = QCHistoryFactory(source_datastream=None)
    now = timezone.now()
    session = QCSession(
        history=history, phenomenon_time_start=now - timedelta(days=1), phenomenon_time_end=now,
        source_checksum="0" * 16,
    )

    with pytest.raises(ValidationError):
        session.full_clean()


def test_full_clean_rejects_end_time_past_source_end_time():
    now = timezone.now()
    source = DatastreamFactory(phenomenon_end_time=now - timedelta(days=2))
    history = QCHistoryFactory(source_datastream=source)
    session = QCSession(
        history=history, phenomenon_time_start=now - timedelta(days=1), phenomenon_time_end=now,
        source_checksum="0" * 16,
    )

    with pytest.raises(ValidationError):
        session.full_clean()


def test_full_clean_allows_valid_new_session():
    now = timezone.now()
    source = DatastreamFactory(phenomenon_end_time=now)
    history = QCHistoryFactory(source_datastream=source)
    session = QCSession(
        history=history, phenomenon_time_start=now - timedelta(days=1), phenomenon_time_end=now,
        source_checksum="0" * 16,
    )

    session.full_clean()  # does not raise


def test_full_clean_rejects_modifying_committed_session():
    session = QCSessionFactory(committed=True)
    session.description = "changed"

    with pytest.raises(ValidationError):
        session.full_clean()


def test_full_clean_allows_modifying_in_progress_session():
    session = QCSessionFactory()
    session.description = "changed"

    session.full_clean()  # does not raise


def test_full_clean_rejects_second_in_progress_session_for_same_history():
    existing = QCSessionFactory()
    now = timezone.now()
    duplicate = QCSession(
        history=existing.history, phenomenon_time_start=now - timedelta(days=1), phenomenon_time_end=now,
        source_checksum="0" * 16,
    )

    with pytest.raises(ValidationError):
        duplicate.full_clean()
