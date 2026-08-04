from .mixins import ResourcePermissionMixin


class AnonymousPrincipal(ResourcePermissionMixin):
    """
    Null-object standing in for an unauthenticated request, in place of None.

    Deliberately not falsy — like Django's own AnonymousUser, code must check
    is_authenticated explicitly rather than relying on truthiness, so a stray
    `if not principal` doesn't silently stop detecting the anonymous case.
    """

    is_authenticated = False
    is_anonymous = True
