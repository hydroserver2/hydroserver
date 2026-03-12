from typing import Optional, Union, TYPE_CHECKING
from django.http import HttpRequest
from django.conf import settings

if TYPE_CHECKING:
    from domains.iam.models import APIKey


class HydroServerHttpRequest(HttpRequest):
    principal: Optional[Union[settings.AUTH_USER_MODEL, "APIKey"]]
