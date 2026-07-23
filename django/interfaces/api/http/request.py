from typing import Union, TYPE_CHECKING
from django.http import HttpRequest
from django.conf import settings

if TYPE_CHECKING:
    from core.iam.models import ServiceAccount
    from core.iam.permissions.anonymous import AnonymousPrincipal


class HydroServerHttpRequest(HttpRequest):
    principal: Union[settings.AUTH_USER_MODEL, "ServiceAccount", "AnonymousPrincipal"]
