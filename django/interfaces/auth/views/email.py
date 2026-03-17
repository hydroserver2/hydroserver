import json
from ninja import Router, Path
from ninja.errors import HttpError
from typing import Literal
from django.contrib.auth import get_user_model
from django_ratelimit.core import get_usage
from allauth.headless.account.views import VerifyEmailView
from allauth.account.utils import send_email_confirmation, has_verified_email
from allauth.headless.constants import Client
from interfaces.auth.schemas import (
    VerificationEmailPutBody,
    VerifyEmailPostBody,
    AccountDetailResponse,
)


User = get_user_model()

email_router = Router(tags=["Email"])

verification_view = {
    "browser": VerifyEmailView.as_api_view(client=Client.BROWSER),
    "app": VerifyEmailView.as_api_view(client=Client.APP),
}


@email_router.put(
    "verify",
    response={
        200: str,
        429: str,
    },
    by_alias=True,
)
def send_verification_email(
    request, client: Path[Literal["browser", "app"]], body: VerificationEmailPutBody
):
    """
    Send an account verification email.
    """

    rate = get_usage(
        request,
        "send_verification_email",
        key=lambda g, r: body.email,
        rate="3/h",
        increment=True,
    )

    if rate["should_limit"] is True:
        raise HttpError(429, "Too many requests")

    try:
        user = User.objects.get(email=body.email)
    except User.DoesNotExist:
        user = None

    if user and not has_verified_email(user):
        send_email_confirmation(request, user, user.email)

    return 200, "Account verification email sent"


@email_router.post(
    "verify",
    response={
        200: str,
        400: str,
        401: str,
        409: str,
    },
    by_alias=True,
)
def verify_email(
    request, client: Path[Literal["browser", "app"]], body: VerifyEmailPostBody
):
    """
    Verify an account email.
    """

    response = verification_view[client](request)

    if response.status_code == 200:
        response_content = json.loads(response.content)
        response_content["data"]["account"] = AccountDetailResponse.from_orm(
            request.user
        ).dict(by_alias=True)
        response.content = json.dumps(response_content)

    return response
