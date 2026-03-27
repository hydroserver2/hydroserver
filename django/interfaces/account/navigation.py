from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from allauth.account.adapter import get_adapter as get_account_adapter
from django.contrib.auth import REDIRECT_FIELD_NAME


ACCOUNT_RETURN_TO_SESSION_KEY = "account_return_to"


def normalize_account_return_to(request, value):
    if not isinstance(value, str):
        return None

    normalized = unquote(value).strip()
    if not normalized:
        return None

    if not get_account_adapter(request).is_safe_url(normalized):
        return None

    return normalized


def get_stored_account_return_to(request):
    session = getattr(request, "session", None)
    if session is None:
        return None
    return normalize_account_return_to(
        request,
        session.get(ACCOUNT_RETURN_TO_SESSION_KEY)
    )


def get_account_return_to(request):
    for query_dict in [getattr(request, "POST", None), request.GET]:
        if not query_dict:
            continue
        value = normalize_account_return_to(request, query_dict.get(REDIRECT_FIELD_NAME))
        if value:
            session = getattr(request, "session", None)
            if session is not None:
                session[ACCOUNT_RETURN_TO_SESSION_KEY] = value
            return value

    return get_stored_account_return_to(request)


def with_account_return_to(url, return_to):
    normalized = return_to if isinstance(return_to, str) and return_to.strip() else None
    if not normalized:
        return url

    parts = urlsplit(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key != REDIRECT_FIELD_NAME
    ]
    query.append((REDIRECT_FIELD_NAME, normalized))
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
