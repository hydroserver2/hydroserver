import pytest

from interfaces.api.service import APIService
from tests.core.iam.factories import WorkspaceFactory
from core.iam.models import Workspace

pytestmark = pytest.mark.django_db


# --- estimate_count -------------------------------------------------------------------


def test_estimate_count_returns_non_negative_int_for_empty_queryset():
    estimate = APIService.estimate_count(Workspace.objects.none())

    assert isinstance(estimate, int)
    assert estimate >= 0


def test_estimate_count_returns_non_negative_int_for_populated_queryset():
    WorkspaceFactory.create_batch(3)

    estimate = APIService.estimate_count(Workspace.objects.all())

    assert isinstance(estimate, int)
    assert estimate >= 0


# --- resolve_count ---------------------------------------------------------------------


def test_resolve_count_returns_exact_count_at_default_threshold():
    WorkspaceFactory.create_batch(3)

    count = APIService.resolve_count(Workspace.objects.all())

    assert count == Workspace.objects.count() == 3


def test_resolve_count_returns_estimate_when_threshold_is_forced_low():
    """threshold=-1 deterministically forces the estimate branch -- the only way to
    exercise it in tests without needing a genuinely huge table."""

    WorkspaceFactory.create_batch(3)

    count = APIService.resolve_count(Workspace.objects.all(), threshold=-1)

    assert count == APIService.estimate_count(Workspace.objects.all())


def test_resolve_count_estimate_branch_does_not_execute_a_real_count(monkeypatch):
    """Forcing the estimate branch should never call queryset.count() -- that's the
    whole point of the fast path."""

    WorkspaceFactory.create_batch(3)
    queryset = Workspace.objects.all()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("queryset.count() should not be called on this path")

    monkeypatch.setattr(type(queryset), "count", fail_if_called)

    APIService.resolve_count(queryset, threshold=-1)
