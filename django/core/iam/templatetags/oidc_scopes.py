from django import template

from core.iam.auth.scopes import SCOPES


register = template.Library()


@register.simple_tag
def oidc_scope_warning(scope):
    """Return the consent-screen warning for a scope, or None if it has none."""

    definition = SCOPES.get(scope)
    if definition is None or definition.warning is None:
        return None

    return {"text": definition.warning, "level": definition.warning_level}
