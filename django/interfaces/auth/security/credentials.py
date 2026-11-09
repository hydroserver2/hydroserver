from interfaces.auth.security.apikey import APIKeyAuth

CREDENTIAL_HEADERS = ("Authorization", APIKeyAuth.param_name)


def has_credential_header(request) -> bool:
    return any(request.headers.get(header) for header in CREDENTIAL_HEADERS)
