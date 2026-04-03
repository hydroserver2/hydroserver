from ninja import Schema
from pydantic import EmailStr


class VerificationEmailPutBody(Schema):
    email: EmailStr


class VerifyEmailPostBody(Schema):
    key: str
