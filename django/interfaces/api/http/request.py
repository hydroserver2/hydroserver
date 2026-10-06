from typing import Optional, Union, TYPE_CHECKING
from django.http import HttpRequest
from django.conf import settings

if TYPE_CHECKING:
    from core.iam.models import ServiceAccount
    from core.iam.permissions.anonymous import AnonymousPrincipal
    from interfaces.api.collections import CollectionDefinition
    from interfaces.api.formats import Format
    from interfaces.api.formats.profiles import Profile


class HydroServerHttpRequest(HttpRequest):
    principal: Union[settings.AUTH_USER_MODEL, "ServiceAccount", "AnonymousPrincipal"]
    response_collection: "CollectionDefinition"
    negotiated_params: frozenset[str]
    response_format: "Format"
    response_profile: Optional["Profile"]
