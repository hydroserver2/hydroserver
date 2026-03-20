from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class Account(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr
    organization_name: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=15)
    address: Optional[str] = Field(None, max_length=255)
    link: Optional[str] = Field(None, max_length=2000)
    user_type: str = Field(..., max_length=255, alias="type")
