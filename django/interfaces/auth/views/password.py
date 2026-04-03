from ninja import Router, Path
from typing import Literal
from allauth.headless.account.views import RequestPasswordResetView, ResetPasswordView
from allauth.headless.constants import Client
from interfaces.auth.schemas import RequestResetPasswordPostBody, ResetPasswordPostBody

password_router = Router(tags=["Password"])

password_reset_request_view = {
    "browser": RequestPasswordResetView.as_api_view(client=Client.BROWSER),
    "app": RequestPasswordResetView.as_api_view(client=Client.APP),
}

password_reset_view = {
    "browser": ResetPasswordView.as_api_view(client=Client.BROWSER),
    "app": ResetPasswordView.as_api_view(client=Client.APP),
}


@password_router.post(
    "request",
    response={
        200: str,
        400: str,
    },
    by_alias=True,
)
def request_password_reset(
    request, client: Path[Literal["browser", "app"]], body: RequestResetPasswordPostBody
):
    """
    Request password reset email.
    """

    response = password_reset_request_view[client](request)

    return response


@password_router.post(
    "reset",
    response={
        200: str,
        400: str,
        401: str,
    },
    by_alias=True,
)
def reset_password(
    request, client: Path[Literal["browser", "app"]], body: ResetPasswordPostBody
):
    """
    Reset account password.
    """

    response = password_reset_view[client](request)

    return response
