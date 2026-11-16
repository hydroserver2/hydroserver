from django.conf import settings


def account_settings(request):
    return {"SOCIALACCOUNT_SIGNUP_ONLY": settings.SOCIALACCOUNT_SIGNUP_ONLY}
