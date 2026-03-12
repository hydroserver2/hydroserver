import pytest
from interfaces.auth.schemas import (
    AccountPostBody,
    AccountPatchBody,
    OrganizationPostBody,
    OrganizationPatchBody,
    AccountDetailResponse,
)
from domains.iam.services.account import AccountService

account_service = AccountService()


@pytest.mark.parametrize("principal", ["owner", "admin", "limited", "inactive"])
def test_get_account(get_principal, principal):
    account = account_service.get(principal=get_principal(principal))
    assert account.email.startswith(principal)
    assert AccountDetailResponse.from_orm(account)


@pytest.mark.parametrize(
    "account_data",
    [
        AccountPostBody(
            email="new@example.com",
            password="test1234!",
            first_name="New",
            last_name="User",
            user_type="Other",
            organization=OrganizationPostBody(
                code="TEST", name="Test Org", organization_type="Other"
            ),
        ),
    ],
)
def test_create_account(account_data):
    account = account_service.create(data=account_data)
    assert account.email == account_data.email
    assert account.first_name == account_data.first_name
    assert account.last_name == account_data.last_name
    assert account.user_type == account_data.user_type
    assert account.organization.name == account_data.organization.name
    assert account.organization.code == account_data.organization.code
    assert AccountDetailResponse.from_orm(account)


@pytest.mark.parametrize(
    "principal, account_data",
    [
        (
            "owner",
            AccountPatchBody(
                first_name="New",
                last_name="User",
                user_type="Other",
                organization=OrganizationPatchBody(
                    code="TEST", name="Test Org", organization_type="Other"
                ),
            ),
        ),
    ],
)
def test_update_account(get_principal, principal, account_data):
    account = account_service.update(
        principal=get_principal(principal), data=account_data
    )
    assert account.first_name == account_data.first_name
    assert account.last_name == account_data.last_name
    assert account.user_type == account_data.user_type
    assert account.organization.name == account_data.organization.name
    assert account.organization.code == account_data.organization.code
    assert AccountDetailResponse.from_orm(account)


@pytest.mark.parametrize(
    "principal, max_queries",
    [
        ("owner", 76),
        ("admin", 45),
        ("limited", 45),
    ],
)
def test_delete_account(
    django_assert_max_num_queries, get_principal, principal, max_queries
):
    with django_assert_max_num_queries(max_queries):
        message = account_service.delete(get_principal(principal))
        assert message == "User account has been deleted"
