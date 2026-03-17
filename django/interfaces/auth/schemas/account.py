from ninja import Schema, Field
from pydantic import EmailStr
from typing import Optional, Literal
from django.contrib.auth import get_user_model
from interfaces.api.schemas import BaseGetResponse, BasePostBody, BasePatchBody

User = get_user_model()


class OrganizationFields(Schema):
    code: str = Field(..., max_length=255)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    link: Optional[str] = Field(None, max_length=2000)
    organization_type: str = Field(..., max_length=255, alias="type")


class OrganizationDetailResponse(BaseGetResponse, OrganizationFields):
    pass


class OrganizationPostBody(BasePostBody, OrganizationFields):
    pass


class OrganizationPatchBody(BasePatchBody, OrganizationFields):
    pass


class UserFields(Schema):
    first_name: str = Field(..., max_length=30)
    middle_name: Optional[str] = Field(None, max_length=30)
    last_name: str = Field(..., max_length=150)
    phone: Optional[str] = Field(None, max_length=15)
    address: Optional[str] = Field(None, max_length=255)
    link: Optional[str] = Field(None, max_length=2000)
    user_type: str = Field(..., max_length=255, alias="type")
    organization: Optional[OrganizationDetailResponse] = None


class AccountDetailResponse(BaseGetResponse, UserFields):
    email: EmailStr
    account_type: Literal["admin", "standard", "limited"]


class AccountPostBody(BasePostBody, UserFields):
    email: EmailStr
    password: str
    organization: Optional[OrganizationPostBody] = None


class AccountPatchBody(BasePatchBody, UserFields):
    organization: Optional[OrganizationPatchBody] = None


class TypeDetailResponse(BaseGetResponse):
    user_types: list[str]
    organization_types: list[str]
