from ninja import Schema
from typing import Literal, Optional, TYPE_CHECKING
from pydantic import EmailStr
from interfaces.api.schemas import BasePostBody
from interfaces.auth.schemas.account import UserFields

if TYPE_CHECKING:
    from interfaces.api.schemas import OrganizationPostBody


class ProviderRedirectPostForm(Schema):
    provider: str
    callback_url: str
    process: Literal["login", "connect"]


class ProviderSignupPostBody(BasePostBody, UserFields):
    email: EmailStr
    organization: Optional["OrganizationPostBody"]
