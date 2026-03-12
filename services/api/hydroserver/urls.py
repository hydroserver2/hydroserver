from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path, include
from django.views.static import serve
from interfaces.web.views import index


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/auth/", include("interfaces.auth.urls")),
    path("api/", include("interfaces.api.urls")),
]

urlpatterns += [
    re_path(r"^(?!admin/|accounts/|api/|static/|media/).*$", index),
]

urlpatterns += static(
    settings.STATIC_URL,
    document_root=settings.STORAGES["staticfiles"]["OPTIONS"]["location"],
)
urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.STORAGES["default"]["OPTIONS"]["location"],
)

# In local/dev environments we want file attachments to remain accessible from the
# Django process even when DEBUG is false.
if settings.DEPLOYMENT_BACKEND in {"dev", "local"} and not settings.DEBUG:
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": settings.STORAGES["default"]["OPTIONS"]["location"]},
        ),
        re_path(
            r"^static/(?P<path>.*)$",
            serve,
            {"document_root": settings.STORAGES["staticfiles"]["OPTIONS"]["location"]},
        ),
    ]
