import uuid
import pytest
from datetime import datetime, timedelta, timezone as dt_timezone

from core.sta.services import ObservationService
from processing.quality.services.session import QCSessionService
from processing.quality.models import QCSession, SessionStatus

qc_session_service = QCSessionService()
observation_service = ObservationService()

H1 = "019e0002-0000-7000-8000-000000000001"  # has SESSION_COMMITTED_1 (00:00-06:00)
H2 = "019e0002-0000-7000-8000-000000000002"  # no source datastream
H3 = "019e0002-0000-7000-8000-000000000003"  # operations test fixture

# SOURCE_H1 reuses "Private Datastream 5" from test_datastreams.yaml
# (phenomenon_end_time: 2025-02-10 02:00:00 -0700).
SOURCE_H1 = "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2"
MANAGED_H1 = "019e0001-0000-7000-8000-000000000001"

SESSION_COMMITTED_1 = "019e0003-0000-7000-8000-000000000001"
SESSION_IN_PROGRESS_OPS = "019e0003-0000-7000-8000-000000000002"

NONEXISTENT = "00000000-0000-0000-0000-000000000000"

TZ = dt_timezone(timedelta(hours=-7))


def _dt(*args):
    return datetime(*args, tzinfo=TZ)


@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("viewer", None, None),
        ("admin", None, None),
        ("apikey", LookupError, "does not exist"),
        ("unaffiliated", LookupError, "does not exist"),
    ],
)
def test_get_session(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            qc_session_service.get(
                history=uuid.UUID(H1),
                session=uuid.UUID(SESSION_COMMITTED_1),
                principal=get_principal(principal),
            )
        assert error_fragment in str(exc_info.value)
    else:
        result = qc_session_service.get(
            history=uuid.UUID(H1),
            session=uuid.UUID(SESSION_COMMITTED_1),
            principal=get_principal(principal),
        )
        assert result.status == SessionStatus.COMMITTED
        assert result.phenomenon_time_start == _dt(2025, 1, 1, 0, 0)
        assert result.phenomenon_time_end == _dt(2025, 1, 1, 6, 0)


def test_get_session_wrong_history(get_principal):
    """SESSION_COMMITTED_1 belongs to H1, not H2."""
    with pytest.raises(LookupError) as exc_info:
        qc_session_service.get(
            history=uuid.UUID(H2),
            session=uuid.UUID(SESSION_COMMITTED_1),
            principal=get_principal("owner"),
        )
    assert "does not exist" in str(exc_info.value)


def test_get_session_nonexistent(get_principal):
    with pytest.raises(LookupError) as exc_info:
        qc_session_service.get(
            history=uuid.UUID(H1),
            session=uuid.UUID(NONEXISTENT),
            principal=get_principal("owner"),
        )
    assert "does not exist" in str(exc_info.value)


@pytest.mark.parametrize(
    "principal, params, expected_count",
    [
        ("owner", {}, 1),
        ("editor", {}, 1),
        ("viewer", {}, 1),
        ("admin", {}, 1),
        ("apikey", {}, None),
        ("unaffiliated", {}, None),
        ("owner", {"status": "committed"}, 1),
        ("owner", {"status": "in_progress"}, 0),
        ("owner", {"range_start": _dt(2025, 1, 1, 7, 0)}, 0),
        ("owner", {"range_end": _dt(2025, 1, 1, 0, 0)}, 0),
        ("owner", {"range_start": _dt(2025, 1, 1, 5, 0)}, 1),
    ],
)
def test_list_sessions(get_principal, principal, params, expected_count):
    if expected_count is None:
        with pytest.raises(LookupError) as exc_info:
            qc_session_service.get_collection(history=uuid.UUID(H1), principal=get_principal(principal), **params)
        assert "does not exist" in str(exc_info.value)
    else:
        count, sessions = qc_session_service.get_collection(
            history=uuid.UUID(H1), principal=get_principal(principal), **params
        )
        assert count == expected_count


def test_list_sessions_invalid_order_by(get_principal):
    with pytest.raises(ValueError) as exc_info:
        qc_session_service.get_collection(
            history=uuid.UUID(H1), principal=get_principal("owner"), order_by=["not_a_field"]
        )
    assert "Invalid order_by" in str(exc_info.value)


def test_list_sessions_nonexistent_history(get_principal):
    with pytest.raises(LookupError) as exc_info:
        qc_session_service.get_collection(history=uuid.UUID(NONEXISTENT), principal=get_principal("owner"))
    assert "does not exist" in str(exc_info.value)


# --- create() ---

@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("admin", None, None),
        ("viewer", PermissionError, "do not have permission"),
        ("apikey", LookupError, "does not exist"),
        ("unaffiliated", LookupError, "does not exist"),
    ],
)
def test_create_session(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            qc_session_service.create(
                principal=get_principal(principal),
                history=uuid.UUID(H1),
                phenomenon_time_start=_dt(2025, 1, 1, 6, 0),
                phenomenon_time_end=_dt(2025, 1, 1, 12, 0),
            )
        assert error_fragment in str(exc_info.value)
    else:
        result = qc_session_service.create(
            principal=get_principal(principal),
            history=uuid.UUID(H1),
            phenomenon_time_start=_dt(2025, 1, 1, 6, 0),
            phenomenon_time_end=_dt(2025, 1, 1, 12, 0),
        )
        assert result.status == SessionStatus.IN_PROGRESS
        assert result.phenomenon_time_start == _dt(2025, 1, 1, 6, 0)
        assert result.phenomenon_time_end == _dt(2025, 1, 1, 12, 0)
        assert result.source_checksum == observation_service.get_checksum(
            datastream=result.history.source_datastream,
            phenomenon_time_start=_dt(2025, 1, 1, 6, 0),
            phenomenon_time_end=_dt(2025, 1, 1, 12, 0),
        )
        # No overlap with SESSION_COMMITTED_1 (00:00-06:00), so no dependencies.
        assert result.dependencies.count() == 0


def test_create_session_invalid_time_range(get_principal):
    with pytest.raises(ValueError) as exc_info:
        qc_session_service.create(
            principal=get_principal("owner"),
            history=uuid.UUID(H1),
            phenomenon_time_start=_dt(2025, 1, 1, 12, 0),
            phenomenon_time_end=_dt(2025, 1, 1, 6, 0),
        )
    assert "phenomenon_time_end must be after phenomenon_time_start" in str(exc_info.value)


def test_create_session_no_source_datastream(get_principal):
    with pytest.raises(ValueError) as exc_info:
        qc_session_service.create(
            principal=get_principal("owner"),
            history=uuid.UUID(H2),
            phenomenon_time_start=_dt(2025, 1, 1, 0, 0),
            phenomenon_time_end=_dt(2025, 1, 1, 6, 0),
        )
    assert "no source datastream" in str(exc_info.value)


def test_create_session_exceeds_source_end_time(get_principal):
    """SOURCE_H1's phenomenon_end_time is 2025-02-10 02:00 -0700."""
    with pytest.raises(ValueError) as exc_info:
        qc_session_service.create(
            principal=get_principal("owner"),
            history=uuid.UUID(H1),
            phenomenon_time_start=_dt(2025, 1, 1, 6, 0),
            phenomenon_time_end=_dt(2025, 2, 11, 0, 0),
        )
    assert "cannot extend past the source datastream's current end time" in str(exc_info.value)


def test_create_session_already_in_progress(get_principal):
    qc_session_service.create(
        principal=get_principal("owner"),
        history=uuid.UUID(H1),
        phenomenon_time_start=_dt(2025, 1, 1, 6, 0),
        phenomenon_time_end=_dt(2025, 1, 1, 12, 0),
    )

    with pytest.raises(ValueError) as exc_info:
        qc_session_service.create(
            principal=get_principal("owner"),
            history=uuid.UUID(H1),
            phenomenon_time_start=_dt(2025, 1, 1, 12, 0),
            phenomenon_time_end=_dt(2025, 1, 1, 18, 0),
        )
    assert "already has an in-progress session" in str(exc_info.value)


# --- update() ---

@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("admin", None, None),
        ("viewer", PermissionError, "do not have permission"),
        ("apikey", LookupError, "does not exist"),
        ("unaffiliated", LookupError, "does not exist"),
    ],
)
def test_update_session(get_principal, principal, error, error_fragment):
    new_session = qc_session_service.create(
        principal=get_principal("owner"),
        history=uuid.UUID(H1),
        phenomenon_time_start=_dt(2025, 1, 1, 6, 0),
        phenomenon_time_end=_dt(2025, 1, 1, 12, 0),
    )

    if error:
        with pytest.raises(error) as exc_info:
            qc_session_service.update(
                principal=get_principal(principal),
                history=uuid.UUID(H1),
                session=new_session.pk,
                description="Updated description",
            )
        assert error_fragment in str(exc_info.value)
    else:
        result = qc_session_service.update(
            principal=get_principal(principal),
            history=uuid.UUID(H1),
            session=new_session.pk,
            description="Updated description",
        )
        assert result.description == "Updated description"


def test_update_committed_session(get_principal):
    with pytest.raises(ValueError) as exc_info:
        qc_session_service.update(
            principal=get_principal("owner"),
            history=uuid.UUID(H1),
            session=uuid.UUID(SESSION_COMMITTED_1),
            description="New description",
        )
    assert "Only in-progress sessions can be updated" in str(exc_info.value)


# --- delete() ---

@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("admin", None, None),
        ("viewer", PermissionError, "do not have permission"),
        ("apikey", LookupError, "does not exist"),
        ("unaffiliated", LookupError, "does not exist"),
    ],
)
def test_delete_session(get_principal, principal, error, error_fragment):
    new_session = qc_session_service.create(
        principal=get_principal("owner"),
        history=uuid.UUID(H1),
        phenomenon_time_start=_dt(2025, 1, 1, 6, 0),
        phenomenon_time_end=_dt(2025, 1, 1, 12, 0),
    )

    if error:
        with pytest.raises(error) as exc_info:
            qc_session_service.delete(
                principal=get_principal(principal), history=uuid.UUID(H1), session=new_session.pk
            )
        assert error_fragment in str(exc_info.value)
    else:
        qc_session_service.delete(principal=get_principal(principal), history=uuid.UUID(H1), session=new_session.pk)
        assert not QCSession.objects.filter(pk=new_session.pk).exists()


def test_delete_committed_session(get_principal):
    with pytest.raises(ValueError) as exc_info:
        qc_session_service.delete(
            principal=get_principal("owner"), history=uuid.UUID(H1), session=uuid.UUID(SESSION_COMMITTED_1)
        )
    assert "Only in-progress sessions can be deleted" in str(exc_info.value)


# --- commit() ---

@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("admin", None, None),
        ("viewer", PermissionError, "do not have permission"),
        ("apikey", LookupError, "does not exist"),
        ("unaffiliated", LookupError, "does not exist"),
    ],
)
def test_commit_session(get_principal, principal, error, error_fragment):
    new_session = qc_session_service.create(
        principal=get_principal("owner"),
        history=uuid.UUID(H1),
        phenomenon_time_start=_dt(2025, 1, 1, 6, 0),
        phenomenon_time_end=_dt(2025, 1, 1, 12, 0),
    )

    if error:
        with pytest.raises(error) as exc_info:
            qc_session_service.commit(principal=get_principal(principal), history=uuid.UUID(H1), session=new_session.pk)
        assert error_fragment in str(exc_info.value)
    else:
        result = qc_session_service.commit(
            principal=get_principal(principal), history=uuid.UUID(H1), session=new_session.pk
        )
        assert result.status == SessionStatus.COMMITTED
        assert result.committed_at is not None
        assert result.managed_checksum == observation_service.get_checksum(
            datastream=result.history.managed_datastream,
            phenomenon_time_start=_dt(2025, 1, 1, 6, 0),
            phenomenon_time_end=_dt(2025, 1, 1, 12, 0),
        )

        history = result.history
        # H1 originally covered 00:00-06:00; the new session extends it to 12:00.
        assert history.phenomenon_time_start == _dt(2025, 1, 1, 0, 0)
        assert history.phenomenon_time_end == _dt(2025, 1, 1, 12, 0)
        assert history.managed_checksum == observation_service.get_checksum(
            datastream=history.managed_datastream,
            phenomenon_time_start=_dt(2025, 1, 1, 0, 0),
            phenomenon_time_end=_dt(2025, 1, 1, 12, 0),
        )
        assert history.source_checksum == observation_service.get_checksum(
            datastream=history.source_datastream,
            phenomenon_time_start=_dt(2025, 1, 1, 0, 0),
            phenomenon_time_end=_dt(2025, 1, 1, 12, 0),
        )


def test_commit_already_committed_session(get_principal):
    with pytest.raises(ValueError) as exc_info:
        qc_session_service.commit(
            principal=get_principal("owner"), history=uuid.UUID(H1), session=uuid.UUID(SESSION_COMMITTED_1)
        )
    assert "Only in-progress sessions can be committed" in str(exc_info.value)


# --- dependency tracking ---

def test_session_dependencies_and_ancestors(get_principal):
    """A new session overlapping two committed sessions depends on both,
    and both are returned as ancestors via get_collection(ancestor_of=...).
    """
    # Commit a second session covering 06:00-12:00 (no overlap with SESSION_COMMITTED_1).
    second_session = qc_session_service.create(
        principal=get_principal("owner"),
        history=uuid.UUID(H1),
        phenomenon_time_start=_dt(2025, 1, 1, 6, 0),
        phenomenon_time_end=_dt(2025, 1, 1, 12, 0),
    )
    qc_session_service.commit(principal=get_principal("owner"), history=uuid.UUID(H1), session=second_session.pk)

    # A new session covering 03:00-09:00 overlaps both committed sessions.
    third_session = qc_session_service.create(
        principal=get_principal("owner"),
        history=uuid.UUID(H1),
        phenomenon_time_start=_dt(2025, 1, 1, 3, 0),
        phenomenon_time_end=_dt(2025, 1, 1, 9, 0),
    )

    dependency_ids = set(third_session.dependencies.values_list("dependency_id", flat=True))
    assert dependency_ids == {uuid.UUID(SESSION_COMMITTED_1), second_session.pk}

    count, ancestors = qc_session_service.get_collection(
        history=uuid.UUID(H1),
        principal=get_principal("owner"),
        ancestor_of=third_session.pk,
    )
    ancestor_ids = {session.pk for session in ancestors}
    assert ancestor_ids == {uuid.UUID(SESSION_COMMITTED_1), second_session.pk}
    assert count == 2

    # include_ancestors=True for a queryset containing only the third session
    # should also pull in its two ancestors.
    count, sessions = qc_session_service.get_collection(
        history=uuid.UUID(H1),
        principal=get_principal("owner"),
        range_start=_dt(2025, 1, 1, 8, 0),
        range_end=_dt(2025, 1, 1, 10, 0),
        include_ancestors=True,
    )
    session_ids = {session.pk for session in sessions}
    assert third_session.pk in session_ids
    assert uuid.UUID(SESSION_COMMITTED_1) in session_ids
    assert second_session.pk in session_ids
    assert count == 3