import pytest
from ninja.errors import ValidationError as NinjaValidationError
from pydantic import validate_call

from interfaces.api.http.handlers import ninja_validation_error_handler


class _FakeApi:
    def create_response(self, request, data, status):
        return {"request": request, "data": data, "status": status}


def test_validation_error_handler_returns_400_for_pydantic_validation_error():
    @validate_call
    def add(a: int, b: int) -> int:
        return a + b

    with pytest.raises(Exception) as exc_info:
        add(a="not-an-int", b=1)

    response = ninja_validation_error_handler(request=None, exc=exc_info.value, api=_FakeApi())

    assert response["status"] == 400
    assert "message" in response["data"]
    assert response["data"]["message"]


def test_validation_error_handler_returns_400_for_ninja_validation_error():
    exc = NinjaValidationError([{"msg": "field required", "loc": ["query", "id"]}])

    response = ninja_validation_error_handler(request=None, exc=exc, api=_FakeApi())

    assert response["status"] == 400
    assert response["data"]["message"] == "field required"
