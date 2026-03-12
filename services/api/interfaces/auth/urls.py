from ninja import NinjaAPI
from ninja.throttling import AnonRateThrottle, AuthRateThrottle
from django.urls import path
from django.views.decorators.csrf import ensure_csrf_cookie
from hydroserver import __version__
from interfaces.api.renderer import ORJSONRenderer
from interfaces.auth.views import (
    account_router,
    session_router,
    email_router,
    password_router,
    provider_router,
)


auth_api = NinjaAPI(
    title="HydroServer User Authentication API",
    version=__version__,
    urls_namespace="iam",
    docs_decorator=ensure_csrf_cookie,
    renderer=ORJSONRenderer(),
    throttle=[
        AnonRateThrottle("20/s"),
        AuthRateThrottle("20/s"),
    ],
)

account_router.add_router("email", email_router)
account_router.add_router("password", password_router)

auth_api.add_router("{client}/account", account_router)
auth_api.add_router("{client}/session", session_router)
auth_api.add_router("{client}/provider", provider_router)

urlpatterns = [
    path("", auth_api.urls),
]
