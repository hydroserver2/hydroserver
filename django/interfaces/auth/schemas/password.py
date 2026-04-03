from ninja import Schema
from pydantic import EmailStr


class RequestResetPasswordPostBody(Schema):
    email: EmailStr


class ResetPasswordPostBody(Schema):
    key: str
    password: str
