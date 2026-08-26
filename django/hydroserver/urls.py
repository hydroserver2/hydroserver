from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import URLPattern, URLResolver, path, re_path, include
from django.views.static import serve
from interfaces.web.views import main_spa_view, qc_spa_view


urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("accounts/", include("interfaces.account.urls")),
    path("", include("allauth.idp.urls")),
    path("api/", include("interfaces.api.urls")),
]

if settings.E2E_TESTING:
    from interfaces.actions.e2e import scenario_view

    urlpatterns.insert(0, path("api/e2e/scenarios", scenario_view))

urlpatterns += [
    re_path(r"^qc/.*$", qc_spa_view),
    re_path(
        r"^(?!admin/|accounts/|identity/|\.well-known/|api/|static/|media/).*$",
        main_spa_view,
    ),
]

if settings.MEDIA_STORAGE_ENABLED and settings.MEDIA_STORAGE_IS_LOCAL:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.STORAGES["default"]["OPTIONS"]["location"],
    )

# When using local filesystem storage, we want hosted resources to remain
# accessible from the Django process even when DEBUG is false.
if settings.MEDIA_STORAGE_ENABLED and settings.MEDIA_STORAGE_IS_LOCAL and not settings.DEBUG:
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": settings.STORAGES["default"]["OPTIONS"]["location"]},
        ),
    ]
