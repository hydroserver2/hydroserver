from core.iam.permissions.anonymous import AnonymousPrincipal


def anonymous_auth(request):

    request.principal = AnonymousPrincipal()

    return True
