import json
import uuid
from unittest.mock import MagicMock

from hydroserverpy.api.services.monitoring.rule import MonitoringRuleService


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        if self._payload is None:
            raise ValueError("No JSON content (empty response body)")
        return self._payload


def make_client():
    client = MagicMock()
    client.base_route = "/api/data"
    return client


def test_create_rule_posts_to_flat_route_with_task_id_in_body():
    client = make_client()
    task_id = uuid.uuid4()
    rule_id = str(uuid.uuid4())
    datastream_id = str(uuid.uuid4())

    client.request.side_effect = [
        FakeResponse({"id": rule_id}, status_code=201),
        FakeResponse(
            {
                "data": {
                    "id": rule_id,
                    "taskId": str(task_id),
                    "datastreamId": datastream_id,
                    "ruleType": "missing_data",
                    "windowInterval": 1,
                    "windowIntervalUnits": "days",
                }
            }
        ),
    ]

    service = MonitoringRuleService(client)
    rule = service.create(
        task_id=task_id,
        datastream=datastream_id,
        rule_type="missing_data",
        window_interval=1,
        window_interval_units="days",
    )

    post_call = client.request.call_args_list[0]
    assert post_call.args[0] == "post"
    assert post_call.args[1] == "//api/data/monitoring-rules"
    sent_body = json.loads(post_call.kwargs["data"])
    assert sent_body["taskId"] == str(task_id)

    get_call = client.request.call_args_list[1]
    assert get_call.args[1] == f"//api/data/monitoring-rules/{rule_id}"

    assert str(rule.uid) == rule_id
    assert rule.task_id == task_id
    assert str(rule.datastream_id) == datastream_id
    assert rule.rule_type == "missing_data"


def test_update_rule_patches_flat_route_and_refetches_after_204():
    client = make_client()
    task_id = uuid.uuid4()
    rule_id = str(uuid.uuid4())
    datastream_id = str(uuid.uuid4())

    client.request.side_effect = [
        FakeResponse(None, status_code=204),
        FakeResponse(
            {
                "data": {
                    "id": rule_id,
                    "taskId": str(task_id),
                    "datastreamId": datastream_id,
                    "ruleType": "missing_data",
                    "windowInterval": 2,
                    "windowIntervalUnits": "days",
                }
            }
        ),
    ]

    service = MonitoringRuleService(client)
    rule = service.update(uid=rule_id, window_interval=2)

    patch_call = client.request.call_args_list[0]
    assert patch_call.args[0] == "patch"
    assert patch_call.args[1] == f"//api/data/monitoring-rules/{rule_id}"
    sent_body = json.loads(patch_call.kwargs["data"])
    assert sent_body == {"windowInterval": 2}

    assert rule.window_interval == 2
