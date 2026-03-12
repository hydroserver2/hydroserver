import pytz
from datetime import datetime
from typing import Annotated, Union
from dateutil.parser import isoparse
from pydantic import AfterValidator, WithJsonSchema


def validate_iso_datetime(value: Union[str, datetime]) -> datetime:
    if isinstance(value, str):
        try:
            parsed_value = isoparse(value)
        except (TypeError, ValueError):
            raise ValueError("Invalid ISO time format")
    elif isinstance(value, datetime):
        parsed_value = value
    else:
        raise TypeError("Expected string or datetime")

    if parsed_value.tzinfo is None:
        parsed_value = parsed_value.replace(tzinfo=pytz.UTC)
    else:
        parsed_value = parsed_value.astimezone(pytz.UTC)

    return parsed_value


ISODatetime = Annotated[
    Union[str, datetime],
    AfterValidator(validate_iso_datetime),
    WithJsonSchema({"type": "string", "format": "date-time"}, mode="serialization"),
]
