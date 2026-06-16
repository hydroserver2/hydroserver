import uuid
import pytest

from processing.quality.services.operation import QCOperationService, OperationInput
from processing.quality.models import QCOperation

qc_operation_service = QCOperationService()

H1 = "019e0002-0000-7000-8000-000000000001"  # has SESSION_COMMITTED_1
H3 = "019e0002-0000-7000-8000-000000000003"  # operations test fixture

SESSION_COMMITTED_1 = "019e0003-0000-7000-8000-000000000001"
SESSION_IN_PROGRESS_OPS = "019e0003-0000-7000-8000-000000000002"

OPERATION_1 = "019e0004-0000-7000-8000-000000000001"  # SELECTION, order=1
OPERATION_2 = "019e0004-0000-7000-8000-000000000002"  # VALUE_THRESHOLD, order=2

NONEXISTENT = "00000000-0000-0000-0000-000000000000"


# --- get() ---

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
def test_get_operation(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            qc_operation_service.get(
                history=uuid.UUID(H3),
                session=uuid.UUID(SESSION_IN_PROGRESS_OPS),
                operation=uuid.UUID(OPERATION_1),
                principal=get_principal(principal),
            )
        assert error_fragment in str(exc_info.value)
    else:
        result = qc_operation_service.get(
            history=uuid.UUID(H3),
            session=uuid.UUID(SESSION_IN_PROGRESS_OPS),
            operation=uuid.UUID(OPERATION_1),
            principal=get_principal(principal),
        )
        assert result.order == 1
        assert result.operation_type == "SELECTION"
        assert result.comment == "Select range for QC"


def test_get_operation_wrong_session(get_principal):
    """OPERATION_1 belongs to SESSION_IN_PROGRESS_OPS, not SESSION_COMMITTED_1."""
    with pytest.raises(LookupError) as exc_info:
        qc_operation_service.get(
            history=uuid.UUID(H1),
            session=uuid.UUID(SESSION_COMMITTED_1),
            operation=uuid.UUID(OPERATION_1),
            principal=get_principal("owner"),
        )
    assert "does not exist" in str(exc_info.value)


def test_get_operation_nonexistent(get_principal):
    with pytest.raises(LookupError) as exc_info:
        qc_operation_service.get(
            history=uuid.UUID(H3),
            session=uuid.UUID(SESSION_IN_PROGRESS_OPS),
            operation=uuid.UUID(NONEXISTENT),
            principal=get_principal("owner"),
        )
    assert "does not exist" in str(exc_info.value)


# --- get_collection() ---

@pytest.mark.parametrize(
    "principal, expected_count",
    [
        ("owner", 2),
        ("editor", 2),
        ("viewer", 2),
        ("admin", 2),
    ],
)
def test_list_operations(get_principal, principal, expected_count):
    count, operations = qc_operation_service.get_collection(
        history=uuid.UUID(H3), session=uuid.UUID(SESSION_IN_PROGRESS_OPS), principal=get_principal(principal)
    )
    assert count == expected_count
    operations = list(operations)
    assert [operation.order for operation in operations] == [1, 2]


@pytest.mark.parametrize(
    "principal, error_fragment",
    [
        ("apikey", "does not exist"),
        ("unaffiliated", "does not exist"),
    ],
)
def test_list_operations_no_access(get_principal, principal, error_fragment):
    with pytest.raises(LookupError) as exc_info:
        qc_operation_service.get_collection(
            history=uuid.UUID(H3), session=uuid.UUID(SESSION_IN_PROGRESS_OPS), principal=get_principal(principal)
        )
    assert error_fragment in str(exc_info.value)


def test_list_operations_invalid_order_by(get_principal):
    with pytest.raises(ValueError) as exc_info:
        qc_operation_service.get_collection(
            history=uuid.UUID(H3),
            session=uuid.UUID(SESSION_IN_PROGRESS_OPS),
            principal=get_principal("owner"),
            order_by=["not_a_field"],
        )
    assert "Invalid order_by" in str(exc_info.value)


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
def test_create_operation(get_principal, principal, error, error_fragment):
    operations = [
        OperationInput(order=3, operation_type="DATETIME_RANGE", comment="Trim range", arguments={"start": 0, "end": 1})
    ]

    if error:
        with pytest.raises(error) as exc_info:
            qc_operation_service.create(
                principal=get_principal(principal),
                history=uuid.UUID(H3),
                session=uuid.UUID(SESSION_IN_PROGRESS_OPS),
                operations=operations,
            )
        assert error_fragment in str(exc_info.value)
    else:
        result = qc_operation_service.create(
            principal=get_principal(principal),
            history=uuid.UUID(H3),
            session=uuid.UUID(SESSION_IN_PROGRESS_OPS),
            operations=operations,
        )
        assert len(result) == 1
        created = result[0]
        assert created.order == 3
        assert created.operation_type == "DATETIME_RANGE"
        assert created.comment == "Trim range"
        assert created.arguments == {"start": 0, "end": 1}

        # operation_type is stored as the enum's `.value` string in the database.
        stored = QCOperation.objects.get(pk=created.pk)
        assert stored.operation_type == "DATETIME_RANGE"


def test_create_operation_committed_session(get_principal):
    with pytest.raises(ValueError) as exc_info:
        qc_operation_service.create(
            principal=get_principal("owner"),
            history=uuid.UUID(H1),
            session=uuid.UUID(SESSION_COMMITTED_1),
            operations=[OperationInput(order=1, operation_type="SELECTION", arguments={})],
        )
    assert "Operations can only be added to an in-progress session" in str(exc_info.value)


def test_create_operation_defaults(get_principal):
    """comment and arguments default to None/{} when not provided."""
    result = qc_operation_service.create(
        principal=get_principal("owner"),
        history=uuid.UUID(H3),
        session=uuid.UUID(SESSION_IN_PROGRESS_OPS),
        operations=[OperationInput(order=3, operation_type="FIND_GAPS")],
    )
    created = result[0]
    assert created.comment is None
    assert created.arguments == {}


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
def test_update_operation(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            qc_operation_service.update(
                principal=get_principal(principal),
                history=uuid.UUID(H3),
                session=uuid.UUID(SESSION_IN_PROGRESS_OPS),
                operation=uuid.UUID(OPERATION_2),
                comment="Updated comment",
            )
        assert error_fragment in str(exc_info.value)
    else:
        result = qc_operation_service.update(
            principal=get_principal(principal),
            history=uuid.UUID(H3),
            session=uuid.UUID(SESSION_IN_PROGRESS_OPS),
            operation=uuid.UUID(OPERATION_2),
            comment="Updated comment",
        )
        assert result.comment == "Updated comment"
        # Unspecified fields are unchanged.
        assert result.order == 2
        assert result.arguments == {"min": 0, "max": 10}


def test_update_operation_order_and_arguments(get_principal):
    result = qc_operation_service.update(
        principal=get_principal("owner"),
        history=uuid.UUID(H3),
        session=uuid.UUID(SESSION_IN_PROGRESS_OPS),
        operation=uuid.UUID(OPERATION_1),
        order=10,
        arguments={"start": "2025-01-01T02:00:00-07:00", "end": "2025-01-01T04:00:00-07:00"},
    )
    assert result.order == 10
    assert result.arguments == {"start": "2025-01-01T02:00:00-07:00", "end": "2025-01-01T04:00:00-07:00"}
    # comment is unchanged
    assert result.comment == "Select range for QC"


def test_update_operation_committed_session(get_principal):
    """SESSION_COMMITTED_1 has no operations; create one directly via the ORM
    (bypassing the in-progress check in create()) to verify update() rejects it."""
    operation = QCOperation.objects.create(
        pk=uuid.uuid4(),
        session_id=uuid.UUID(SESSION_COMMITTED_1),
        order=1,
        operation_type="SELECTION",
        arguments={},
    )

    with pytest.raises(ValueError) as exc_info:
        qc_operation_service.update(
            principal=get_principal("owner"),
            history=uuid.UUID(H1),
            session=uuid.UUID(SESSION_COMMITTED_1),
            operation=operation.pk,
            comment="New comment",
        )
    assert "Operations can only be updated in an in-progress session" in str(exc_info.value)


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
def test_delete_operation(get_principal, principal, error, error_fragment):
    created = qc_operation_service.create(
        principal=get_principal("owner"),
        history=uuid.UUID(H3),
        session=uuid.UUID(SESSION_IN_PROGRESS_OPS),
        operations=[OperationInput(order=3, operation_type="FIND_GAPS")],
    )[0]

    if error:
        with pytest.raises(error) as exc_info:
            qc_operation_service.delete(
                principal=get_principal(principal),
                history=uuid.UUID(H3),
                session=uuid.UUID(SESSION_IN_PROGRESS_OPS),
                operation=created.pk,
            )
        assert error_fragment in str(exc_info.value)
    else:
        qc_operation_service.delete(
            principal=get_principal(principal),
            history=uuid.UUID(H3),
            session=uuid.UUID(SESSION_IN_PROGRESS_OPS),
            operation=created.pk,
        )
        assert not QCOperation.objects.filter(pk=created.pk).exists()


def test_delete_operation_wrong_history_session(get_principal):
    """OPERATION_1 belongs to H3's session, not H1's committed session."""
    with pytest.raises(LookupError) as exc_info:
        qc_operation_service.delete(
            principal=get_principal("owner"),
            history=uuid.UUID(H1),
            session=uuid.UUID(SESSION_COMMITTED_1),
            operation=uuid.UUID(OPERATION_1),
        )
    assert "does not exist" in str(exc_info.value)


def test_delete_operation_committed_session(get_principal):
    """SESSION_COMMITTED_1 has no operations; create one directly via the ORM
    (bypassing the in-progress check in create()) to verify delete() rejects it."""
    operation = QCOperation.objects.create(
        pk=uuid.uuid4(),
        session_id=uuid.UUID(SESSION_COMMITTED_1),
        order=1,
        operation_type="SELECTION",
        arguments={},
    )

    with pytest.raises(ValueError) as exc_info:
        qc_operation_service.delete(
            principal=get_principal("owner"),
            history=uuid.UUID(H1),
            session=uuid.UUID(SESSION_COMMITTED_1),
            operation=operation.pk,
        )
    assert "Operations can only be deleted from an in-progress session" in str(exc_info.value)