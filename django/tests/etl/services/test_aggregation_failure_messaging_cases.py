import json
import uuid
from pathlib import Path

import pytest
from ninja.errors import HttpError

from domains.etl.models import Task, TaskMappingPath, TaskRun
from domains.etl.services import TaskService
from interfaces.api.schemas import TaskPostBody


task_service = TaskService()


def _load_cases() -> list[dict]:
    case_file = Path(__file__).resolve().parents[3] / "tmp" / "aggregation-messaging-cases.json"
    if not case_file.exists():
        pytest.skip(
            "Missing tmp/aggregation-messaging-cases.json. Generate cases before running this test module.",
            allow_module_level=True,
        )
    return json.loads(case_file.read_text())


ALL_CASES = _load_cases()
CREATE_VALIDATION_CASES = [case for case in ALL_CASES if case["phase"] == "create_validation"]
RUNTIME_CASES = [case for case in ALL_CASES if case["phase"] == "run_time"]


def _create_task_for_case(case: dict, get_principal) -> dict:
    task_data = TaskPostBody.model_validate(case["taskCreateBody"])
    return task_service.create(
        principal=get_principal("owner"),
        data=task_data,
    )


def _mutate_runtime_case(task_id: uuid.UUID, slug: str):
    task = Task.objects.get(pk=task_id)
    mapping = task.mappings.first()

    if slug == "17-run-no-mappings-after-create":
        task.mappings.all().delete()
        return

    if mapping is None:
        raise AssertionError(f"Expected at least one mapping for runtime case '{slug}'.")

    first_path = mapping.paths.first()
    if first_path is None:
        raise AssertionError(f"Expected at least one mapping path for runtime case '{slug}'.")

    if slug == "18-run-branched-mapping-after-create":
        TaskMappingPath.objects.create(
            task_mapping=mapping,
            target_identifier=first_path.target_identifier,
            data_transformations=first_path.data_transformations,
        )
        return

    if slug == "19-run-invalid-target-identifier-after-create":
        first_path.target_identifier = "not-a-uuid"
        first_path.save(update_fields=["target_identifier"])
        return

    if slug == "20-run-target-datastream-deleted-after-create":
        # Keep this non-destructive: emulate "missing target in workspace scope"
        # with a valid UUID that is not present in the workspace.
        first_path.target_identifier = str(uuid.uuid4())
        first_path.save(update_fields=["target_identifier"])
        return

    raise AssertionError(f"Unknown runtime case slug: {slug}")


def _latest_run_payload(task_id: uuid.UUID) -> dict:
    latest_run = TaskRun.objects.filter(task_id=task_id).order_by("-started_at").first()
    assert latest_run is not None
    return {
        "id": latest_run.id,
        "status": latest_run.status,
        "result": latest_run.result,
    }


@pytest.mark.parametrize("case", CREATE_VALIDATION_CASES, ids=lambda case: case["slug"])
def test_aggregation_create_validation_messages(case, get_principal):
    with pytest.raises(HttpError) as exc_info:
        _create_task_for_case(case, get_principal)

    assert exc_info.value.status_code == 400
    assert exc_info.value.message == case["expected"]["message"]


@pytest.mark.parametrize("case", RUNTIME_CASES, ids=lambda case: case["slug"])
def test_aggregation_runtime_failure_messages(case, get_principal, settings):
    settings.CELERY_ENABLED = False
    created_task = _create_task_for_case(case, get_principal)
    task_id = created_task["id"]

    _mutate_runtime_case(task_id, case["slug"])

    run_result = task_service.run(
        principal=get_principal("owner"),
        task_id=task_id,
    )
    if not run_result.get("status") or not isinstance(run_result.get("result"), dict):
        run_result = _latest_run_payload(task_id)

    assert run_result["status"] == case["expected"]["status"]
    assert run_result["result"]["message"] == case["expected"]["message"]
