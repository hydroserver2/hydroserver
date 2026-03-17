def anonymous_auth(request):

    request.principal = None

    return True
