import json

from django.conf import settings
from django.db import transaction
from django.http import HttpResponseNotAllowed, JsonResponse
from django.views.decorators.csrf import csrf_exempt


def _authorized(request):
    expected = settings.E2E_CONTROL_TOKEN
    supplied = request.headers.get("X-E2E-Control-Token", "")
    return bool(expected) and supplied == expected


@csrf_exempt
def scenario_view(request):
    if not _authorized(request):
        return JsonResponse({"detail": "Not found."}, status=404)

    if request.method not in {"POST", "DELETE"}:
        return HttpResponseNotAllowed(["POST", "DELETE"])

    try:
        payload = json.loads(request.body or b"{}")
        scenario_key = payload["scenarioKey"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return JsonResponse({"detail": "scenarioKey is required."}, status=400)

    # Import test-only dependencies lazily so normal deployments never need
    # or load Factory Boy.
    from tests.e2e.scenarios import cleanup_scenario, create_scenario

    with transaction.atomic():
        if request.method == "DELETE":
            cleanup_scenario(scenario_key)
            return JsonResponse({}, status=200)

        cleanup_scenario(scenario_key)
        return JsonResponse(create_scenario(scenario_key), status=201)
