import pytest
from django.core.exceptions import ValidationError

from processing.quality.models import QCOperation
from tests.processing.quality.factories import QCOperationFactory, QCSessionFactory

pytestmark = pytest.mark.django_db


def test_full_clean_rejects_operation_on_committed_session():
    session = QCSessionFactory(committed=True)
    operation = QCOperation(session=session, order=1, operation_type="SELECTION", arguments={})

    with pytest.raises(ValidationError):
        operation.full_clean()


def test_full_clean_allows_operation_on_in_progress_session():
    session = QCSessionFactory()
    operation = QCOperation(session=session, order=1, operation_type="SELECTION", arguments={})

    operation.full_clean()  # does not raise


def test_full_clean_rejects_modifying_operation_after_session_committed():
    operation = QCOperationFactory()
    operation.session.status = "committed"
    operation.session.save()
    operation.comment = "changed"

    with pytest.raises(ValidationError):
        operation.full_clean()
