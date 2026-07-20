import uuid
import pytest

from processing.quality.services.history import QCHistoryService
from processing.quality.models import QCHistory

qc_history_service = QCHistoryService()

H1 = "019e0002-0000-7000-8000-000000000001"  # managed=MANAGED_H1, source=SOURCE_H1
H2 = "019e0002-0000-7000-8000-000000000002"  # source_datastream is null
H3 = "019e0002-0000-7000-8000-000000000003"  # operations test fixture

# SOURCE_H1 reuses "Private Datastream 5" from test_datastreams.yaml.
SOURCE_H1 = "1c9a797e-6fd8-4e99-b1ae-87ab4affc0a2"
MANAGED_H1 = "019e0001-0000-7000-8000-000000000001"
MANAGED_FRESH = "019e0001-0000-7000-8000-000000000002"  # no QC history yet
# MANAGED_SAME_LEVEL reuses "Private Datastream 6"; shares SOURCE_H1's processing level.
MANAGED_SAME_LEVEL = "42e08eea-27bb-4ea3-8ced-63acff0f3334"
# MANAGED_NO_SOURCE reuses "Private Datastream 4"; H2's managed datastream.
MANAGED_NO_SOURCE = "dd1f9293-ce29-4b6a-88e6-d65110d1be65"
# MANAGED_PUBLIC reuses "Public Datastream 1"; different workspace than SOURCE_H1.
MANAGED_PUBLIC = "27c70b41-e845-40ea-8cc7-d1b40f89816b"

NONEXISTENT = "00000000-0000-0000-0000-000000000000"


@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("viewer", None, None),
        ("admin", None, None),
        # API key has no relationship to the private workspace
        ("apikey", LookupError, "does not exist"),
        ("unaffiliated", LookupError, "does not exist"),
    ],
)
def test_get_qc_history(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            qc_history_service.get(history=uuid.UUID(H1), principal=get_principal(principal))
        assert error_fragment in str(exc_info.value)
    else:
        result = qc_history_service.get(history=uuid.UUID(H1), principal=get_principal(principal))
        assert result.managed_datastream_id == uuid.UUID(MANAGED_H1)
        assert result.source_datastream_id == uuid.UUID(SOURCE_H1)


def test_get_qc_history_nonexistent(get_principal):
    with pytest.raises(LookupError) as exc_info:
        qc_history_service.get(history=uuid.UUID(NONEXISTENT), principal=get_principal("owner"))
    assert "does not exist" in str(exc_info.value)


@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("admin", None, None),
        # View-only
        ("viewer", PermissionError, "do not have permission"),
    ],
)
def test_get_qc_history_edit_action(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            qc_history_service.get(history=uuid.UUID(H1), principal=get_principal(principal), action="edit")
        assert error_fragment in str(exc_info.value)
    else:
        result = qc_history_service.get(history=uuid.UUID(H1), principal=get_principal(principal), action="edit")
        assert result.id == uuid.UUID(H1)


@pytest.mark.parametrize(
    "principal, params, expected_count",
    [
        ("owner", {}, 3),
        ("editor", {}, 3),
        ("viewer", {}, 3),
        ("admin", {}, 3),
        ("apikey", {}, 0),
        ("unaffiliated", {}, 0),
        ("anonymous", {}, 0),
        ("owner", {"managed_datastream_id": [uuid.UUID(MANAGED_H1)]}, 1),
        ("owner", {"source_datastream_id": [uuid.UUID(SOURCE_H1)]}, 1),
        ("owner", {"managed_datastream_id": [uuid.UUID(NONEXISTENT)]}, 0),
    ],
)
def test_list_qc_histories(get_principal, principal, params, expected_count):
    count, histories = qc_history_service.get_collection(principal=get_principal(principal), **params)
    assert count == expected_count


def test_list_qc_histories_invalid_order_by(get_principal):
    with pytest.raises(ValueError) as exc_info:
        qc_history_service.get_collection(principal=get_principal("owner"), order_by=["not_a_field"])
    assert "Invalid order_by" in str(exc_info.value)


@pytest.mark.parametrize(
    "principal, error, error_fragment",
    [
        ("owner", None, None),
        ("editor", None, None),
        ("admin", None, None),
        # View-only
        ("viewer", PermissionError, "do not have permission"),
        # No relationship to the private workspace
        ("apikey", PermissionError, "do not have permission"),
        ("unaffiliated", PermissionError, "do not have permission"),
    ],
)
def test_create_qc_history(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            qc_history_service.create(
                principal=get_principal(principal),
                managed_datastream=uuid.UUID(MANAGED_FRESH),
                source_datastream=uuid.UUID(SOURCE_H1),
            )
        assert error_fragment in str(exc_info.value)
    else:
        result = qc_history_service.create(
            principal=get_principal(principal),
            managed_datastream=uuid.UUID(MANAGED_FRESH),
            source_datastream=uuid.UUID(SOURCE_H1),
        )
        assert result.managed_datastream_id == uuid.UUID(MANAGED_FRESH)
        assert result.source_datastream_id == uuid.UUID(SOURCE_H1)


def test_create_qc_history_nonexistent_managed(get_principal):
    with pytest.raises(LookupError) as exc_info:
        qc_history_service.create(
            principal=get_principal("owner"),
            managed_datastream=uuid.UUID(NONEXISTENT),
            source_datastream=uuid.UUID(SOURCE_H1),
        )
    assert "Managed datastream does not exist" in str(exc_info.value)


def test_create_qc_history_nonexistent_source(get_principal):
    with pytest.raises(LookupError) as exc_info:
        qc_history_service.create(
            principal=get_principal("owner"),
            managed_datastream=uuid.UUID(MANAGED_FRESH),
            source_datastream=uuid.UUID(NONEXISTENT),
        )
    assert "Source datastream does not exist" in str(exc_info.value)


def test_create_qc_history_workspace_mismatch(get_principal):
    """The managed and source datastreams belong to different workspaces."""
    with pytest.raises(ValueError) as exc_info:
        qc_history_service.create(
            principal=get_principal("owner"),
            managed_datastream=uuid.UUID(MANAGED_PUBLIC),
            source_datastream=uuid.UUID(SOURCE_H1),
        )
    assert "same workspace" in str(exc_info.value)


def test_create_qc_history_processing_level_mismatch(get_principal):
    """The managed datastream shares its processing level with the source datastream."""
    with pytest.raises(ValueError) as exc_info:
        qc_history_service.create(
            principal=get_principal("owner"),
            managed_datastream=uuid.UUID(MANAGED_SAME_LEVEL),
            source_datastream=uuid.UUID(SOURCE_H1),
        )
    assert "different processing level" in str(exc_info.value)


def test_create_qc_history_duplicate_managed_datastream(get_principal):
    """MANAGED_H1 already has a QC history (H1)."""
    with pytest.raises(ValueError) as exc_info:
        qc_history_service.create(
            principal=get_principal("owner"),
            managed_datastream=uuid.UUID(MANAGED_H1),
            source_datastream=uuid.UUID(SOURCE_H1),
        )
    assert "already has a QC history" in str(exc_info.value)


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
def test_delete_qc_history(get_principal, principal, error, error_fragment):
    if error:
        with pytest.raises(error) as exc_info:
            qc_history_service.delete(history=uuid.UUID(H1), principal=get_principal(principal))
        assert error_fragment in str(exc_info.value)
    else:
        qc_history_service.delete(history=uuid.UUID(H1), principal=get_principal(principal))
        assert not QCHistory.objects.filter(pk=uuid.UUID(H1)).exists()


def test_delete_qc_history_nonexistent(get_principal):
    with pytest.raises(LookupError) as exc_info:
        qc_history_service.delete(history=uuid.UUID(NONEXISTENT), principal=get_principal("owner"))
    assert "does not exist" in str(exc_info.value)