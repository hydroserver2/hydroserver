from ninja import Router, Query
from django.http import HttpResponse
from interfaces.http.auth import oidc_auth, basic_auth
from interfaces.http.request import HydroServerHttpRequest
from interfaces.api.schemas import VocabularyQueryParameters
from interfaces.auth.schemas import AccountDetailResponse, AccountPatchBody
from domains.iam.services import AccountService

account_router = Router(tags=["Account"])
account_service = AccountService()


@account_router.get(
    "",
    auth=[oidc_auth, basic_auth],
    response={
        200: AccountDetailResponse,
        401: str,
    },
    by_alias=True,
)
def get_account(request: HydroServerHttpRequest):
    """
    Get user account details.
    """

    return 200, account_service.get(principal=request.principal)


@account_router.patch(
    "",
    auth=[oidc_auth, basic_auth],
    response={200: AccountDetailResponse, 401: str, 422: str},
    by_alias=True,
)
def update_account(
    request: HydroServerHttpRequest,
    data: AccountPatchBody,
):
    """
    Update user account details.
    """

    return 200, account_service.update(principal=request.principal, data=data)


@account_router.delete(
    "", auth=[oidc_auth, basic_auth], response={204: None, 401: str}
)
def delete_account(request: HydroServerHttpRequest):
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
def get_organization_types(
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
