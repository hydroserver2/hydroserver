import json
from ninja import Router, Path
from typing import Literal
from django.contrib.auth import get_user_model
from allauth.headless.account.views import LoginView, SessionView
from allauth.headless.constants import Client
from interfaces.auth.schemas import AccountDetailResponse, SessionPostBody

User = get_user_model()

session_router = Router(tags=["Session"])

session_view = {
    "browser": SessionView.as_api_view(client=Client.BROWSER),
    "app": SessionView.as_api_view(client=Client.APP),
}

login_view = {
    "browser": LoginView.as_api_view(client=Client.BROWSER),
    "app": LoginView.as_api_view(client=Client.APP),
}


@session_router.get(
    "",
    url_name="current_session",
    response={
        200: str,
        400: str,
        401: str,
    },
    by_alias=True,
)
def get_session(request, client: Path[Literal["browser", "app"]]):
    """
    Get an active user session.
    """

    response = session_view[client](request)

    if response.status_code == 200:
        response_content = json.loads(response.content)
        response_content["data"]["account"] = AccountDetailResponse.from_orm(
            request.user
        ).dict(by_alias=True)
        response_content["meta"]["expires"] = str(request.session.get_expiry_date())
        response.content = json.dumps(response_content)

    if response.status_code == 401 and request.session.exists(
        request.session.session_key
    ):
        user = dict(request.session).get("socialaccount_sociallogin", {}).get("user")
        if user:
            response_content = json.loads(response.content)
            response_content["data"]["account"] = AccountDetailResponse.construct(
                **user
            ).dict(by_alias=True)
            response.content = json.dumps(response_content)

    return response


@session_router.post(
    "",
    url_name="login",
    response={
        200: str,
        400: str,
        401: str,
        409: str,
    },
    by_alias=True,
)
def create_session(
    request, client: Path[Literal["browser", "app"]], data: SessionPostBody
):
    """
    Create a new user session.
    """

    response = login_view[client](request)

    if response.status_code == 200:
        response_content = json.loads(response.content)
        if not request.user.is_authenticated:
            user = User.objects.get(pk=response_content["data"]["user"]["id"])
        else:
            user = request.user
        response_content["data"]["account"] = AccountDetailResponse.from_orm(user).dict(
            by_alias=True
        )
        response.content = json.dumps(response_content)

    return response


@session_router.delete(
    "",
    url_name="current_session",
    response={
        200: str,
        400: str,
        401: str,
    },
    by_alias=True,
)
def delete_session(request, client: Path[Literal["browser", "app"]]):
    """
    Delete an active user session.
    """

    response = session_view[client](request)

    return response
