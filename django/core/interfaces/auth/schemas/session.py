from ninja import Schema
from pydantic import EmailStr


class SessionPostBody(Schema):
    email: EmailStr
    password: str
