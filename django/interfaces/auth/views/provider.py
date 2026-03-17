import json
from ninja import Router, Path, Form
from typing import Literal
from allauth.headless.socialaccount.views import (
    RedirectToProviderView,
    ProviderSignupView,
    ManageProvidersView,
)
from allauth.headless.constants import Client
from interfaces.auth.schemas import (
    ProviderRedirectPostForm,
    ProviderSignupPostBody,
    AccountDetailResponse,
)

provider_router = Router(tags=["Provider"])

provider_manage_view = {
    "browser": ManageProvidersView.as_api_view(client=Client.BROWSER),
    "app": ManageProvidersView.as_api_view(client=Client.APP),
}

provider_redirect_view = {
    "browser": RedirectToProviderView.as_api_view(client=Client.BROWSER),
    "app": RedirectToProviderView.as_api_view(client=Client.APP),
}

provider_signup_view = {
    "browser": ProviderSignupView.as_api_view(client=Client.BROWSER),
    "app": ProviderSignupView.as_api_view(client=Client.APP),
}


@provider_router.get(
    "connections", url_name="get_connections", response={200: str}, by_alias=True
)
def get_providers(request, client: Path[Literal["browser", "app"]]):
    """
    Get connected provider accounts.
    """

    response = provider_manage_view[client](request)

    return response


@provider_router.delete(
    "connections", url_name="delete_connections", response={200: str}, by_alias=True
)
def delete_provider(request, client: Path[Literal["browser", "app"]]):
    """
    Disconnect a provider account.
    """

    response = provider_manage_view[client](request)

    return response


@provider_router.post(
    "redirect",
    url_name="redirect_to_provider",
    response={
        302: None,
    },
    by_alias=True,
)
def redirect_to_provider(
    request,
    client: Path[Literal["browser", "app"]],
    form: Form[ProviderRedirectPostForm],
):
    """
    Redirect to provider login window.
    """

    response = provider_redirect_view[client](request)

    return response


@provider_router.post(
    "signup",
    url_name="provider_signup",
    response={
        200: str,
        400: str,
        401: str,
        403: str,
        409: str,
    },
    by_alias=True,
)
def provider_signup(
    request, client: Path[Literal["browser", "app"]], body: ProviderSignupPostBody
):
    """
    Finish signing up with a provider account.
    """

    response = provider_signup_view[client](request)

    if response.status_code == 200:
        response_content = json.loads(response.content)
        response_content["data"]["account"] = AccountDetailResponse.from_orm(
            request.user
        ).dict(by_alias=True)
        response.content = json.dumps(response_content)

    return response
