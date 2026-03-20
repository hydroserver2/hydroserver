import pytest
from ninja.errors import HttpError
from contextlib import contextmanager


@contextmanager
def test_service_method(schema=None, response=None, error_code=None, fields=None):
    result_container = {}
    if error_code:
        with pytest.raises(HttpError) as exc_info:
            yield result_container
        assert exc_info.value.status_code == error_code
        if response is not None:
            assert exc_info.value.message.startswith(response)
    else:
        yield result_container
        result = result_container.get("result")
        if isinstance(response, int):
            assert len(result) == response
            if schema is not None:
                assert all(schema.from_orm(obj) for obj in result)
        else:
            if schema:
                assert schema.from_orm(result)
            if schema and isinstance(response, dict):
                result_obj = schema.from_orm(result)
                for field, value in response.items():
                    if not fields or field in fields:
                        assert getattr(result_obj, field) == value
            if isinstance(response, str):
                assert result == response
