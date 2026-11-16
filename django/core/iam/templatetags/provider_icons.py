from django import template
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.cache import cache
from django.templatetags.static import static

register = template.Library()


@register.filter
def provider_icon(app):
    """
    Static URL of an OpenID Connect provider's sign-in icon, or None if the
    file isn't there. The path is the app's "icon" setting, defaulting to
    provider-icons/<provider ID>.png. Bundled icons are found on disk; icons
    deployed to static storage (e.g. a bucket) are checked there, and the
    result is cached so the check runs at most every few minutes.
    """

    if app.provider != "openid_connect":
        return None

    path = (app.settings.get("icon") or f"provider-icons/{app.provider_id}.png").lstrip("/")
    exists = cache.get_or_set(
        f"provider-icon:{path}",
        lambda: bool(finders.find(path)) or staticfiles_storage.exists(path),
        300,
    )

    return static(path) if exists else None
