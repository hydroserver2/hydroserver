from typing import Optional
from ninja import Schema, Field
from pydantic import EmailStr
from interfaces.api.schemas import BaseGetResponse


class UserContactFields(Schema):
    phone: Optional[str] = Field(None, max_length=15)
    address: Optional[str] = Field(None, max_length=255)
    link: Optional[str] = Field(None, max_length=2000)
    user_type: str = Field(..., max_length=255, alias="type")


class UserContactResponse(BaseGetResponse, UserContactFields):
    name: str = Field(..., max_length=255)
    email: EmailStr
    organization_name: Optional[str] = None
