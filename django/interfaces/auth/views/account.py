from ninja import Router, Path, Query
from typing import Literal
from django.http import HttpResponse
from allauth.headless.account.views import SignupView
from allauth.headless.constants import Client
from interfaces.http.auth import bearer_auth, session_auth
from interfaces.http.request import HydroServerHttpRequest
from interfaces.api.schemas import VocabularyQueryParameters
from interfaces.auth.schemas import AccountDetailResponse, AccountPostBody, AccountPatchBody
from domains.iam.services import AccountService

account_router = Router(tags=["Account"])
account_service = AccountService()

signup_view = {
    "browser": SignupView.as_api_view(client=Client.BROWSER),
    "app": SignupView.as_api_view(client=Client.APP),
}


@account_router.get(
    "",
    auth=[session_auth, bearer_auth],
    response={
        200: AccountDetailResponse,
        401: str,
    },
    by_alias=True,
)
def get_account(
    request: HydroServerHttpRequest, client: Path[Literal["browser", "app"]]
):
    """
    Get user account details.
    """

    return 200, account_service.get(principal=request.principal)


@account_router.post(
    "",
    url_name="signup",
    response={
        200: AccountDetailResponse,
        400: str,
        401: str,
        403: str,
        409: str,
        422: str,
    },
    by_alias=True,
)
def create_account(
    request, client: Path[Literal["browser", "app"]], data: AccountPostBody
):
    """
    Create a new user account.
    """

    response = signup_view[client](request)

    return response


@account_router.patch(
    "",
    auth=[session_auth, bearer_auth],
    response={200: AccountDetailResponse, 401: str, 422: str},
    by_alias=True,
)
def update_account(
    request: HydroServerHttpRequest,
    client: Path[Literal["browser", "app"]],
    data: AccountPatchBody,
):
    """
    Update user account details.
    """

    return 200, account_service.update(principal=request.principal, data=data)


@account_router.delete(
    "", auth=[session_auth, bearer_auth], response={204: None, 401: str}
)
def delete_account(
    request: HydroServerHttpRequest, client: Path[Literal["browser", "app"]]
):
    """
    Delete a user account.
    """

    return 204, account_service.delete(
        principal=request.principal,
    )


@account_router.get("/user-types", response={200: list[str]}, by_alias=True)
def get_user_types(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[VocabularyQueryParameters],
):
    """
    Get user types.
    """

    return 200, account_service.list_user_types(
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_desc=query.order_desc,
    )


@account_router.get("/organization-types", response={200: list[str]}, by_alias=True)
def get_user_types(
    request: HydroServerHttpRequest,
    response: HttpResponse,
    query: Query[VocabularyQueryParameters],
):
    """
    Get organization types.
    """

    return 200, account_service.list_organization_types(
        response=response,
        page=query.page,
        page_size=query.page_size,
        order_desc=query.order_desc,
    )
