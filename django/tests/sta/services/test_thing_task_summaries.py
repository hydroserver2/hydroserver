import uuid
import pytest
from core.sta.services import ThingService

thing_service = ThingService()

PRIVATE_WORKSPACE = "b27c51a0-7374-462d-8a53-d97d47176c10"
PUBLIC_WORKSPACE = "6e0deaf2-a92b-421b-9ece-86783265596f"

EXPECTED_FIELDS = {"id", "name", "site_type", "product_task_count", "product_task_attention_count",
                   "monitoring_task_count", "monitoring_task_attention_count"}


@pytest.mark.parametrize("principal", ["owner", "editor", "viewer", "admin", "apikey", "unaffiliated", None])
def test_list_task_summaries_returns_without_error(get_principal, principal):
    results = list(thing_service.list_task_summaries(principal=get_principal(principal)))
    assert all(hasattr(t, f) for t in results for f in EXPECTED_FIELDS)


def test_list_task_summaries_count_fields_are_non_negative_integers(get_principal):
    results = list(thing_service.list_task_summaries(principal=get_principal("owner")))
    for t in results:
        assert isinstance(t.product_task_count, int) and t.product_task_count >= 0
        assert isinstance(t.product_task_attention_count, int) and t.product_task_attention_count >= 0
        assert isinstance(t.monitoring_task_count, int) and t.monitoring_task_count >= 0
        assert isinstance(t.monitoring_task_attention_count, int) and t.monitoring_task_attention_count >= 0


def test_list_task_summaries_workspace_filter(get_principal):
    results = list(thing_service.list_task_summaries(
        principal=get_principal("owner"),
        workspace_id=[uuid.UUID(PRIVATE_WORKSPACE)],
    ))
    assert all(str(t.workspace_id) == PRIVATE_WORKSPACE for t in results)


def test_list_task_summaries_site_type_filter(get_principal):
    results = list(thing_service.list_task_summaries(
        principal=get_principal("owner"),
        site_type=["Public"],
    ))
    assert all(t.site_type == "Public" for t in results)
