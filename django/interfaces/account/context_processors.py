from interfaces.account.navigation import get_account_return_to


def account_navigation(request):
    return {
        "account_return_url": get_account_return_to(request),
    }
