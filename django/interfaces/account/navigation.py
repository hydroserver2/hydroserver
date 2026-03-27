from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from allauth.account.adapter import get_adapter as get_account_adapter
from django.contrib.auth import REDIRECT_FIELD_NAME


ACCOUNT_RETURN_TO_SESSION_KEY = "account_return_to"
ACCOUNT_POST_AUTH_HANDOFF_SESSION_KEY = "account_post_auth_handoff"
ACCOUNT_HANDOFF_FIELD_NAME = "handoff"


def normalize_account_return_to(request, value):
    if not isinstance(value, str):
        return None

    normalized = value.strip()
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


def get_stored_account_post_auth_handoff(request):
    session = getattr(request, "session", None)
    if session is None:
        return None
    return normalize_account_return_to(
        request,
        session.get(ACCOUNT_POST_AUTH_HANDOFF_SESSION_KEY),
    )


def _store_account_navigation(request, query_dict, preserve_handoff_when_missing=False):
    if not query_dict:
        return False

    has_return_to = REDIRECT_FIELD_NAME in query_dict
    has_handoff = ACCOUNT_HANDOFF_FIELD_NAME in query_dict
    if not has_return_to and not has_handoff:
        return False

    session = getattr(request, "session", None)
    if session is None:
        return True

    if has_return_to:
        return_to = normalize_account_return_to(
            request,
            query_dict.get(REDIRECT_FIELD_NAME),
        )
        if return_to:
            session[ACCOUNT_RETURN_TO_SESSION_KEY] = return_to
        else:
            session.pop(ACCOUNT_RETURN_TO_SESSION_KEY, None)

        if has_handoff:
            handoff = normalize_account_return_to(
                request,
                query_dict.get(ACCOUNT_HANDOFF_FIELD_NAME),
            )
            if handoff:
                session[ACCOUNT_POST_AUTH_HANDOFF_SESSION_KEY] = handoff
            else:
                session.pop(ACCOUNT_POST_AUTH_HANDOFF_SESSION_KEY, None)
        elif not preserve_handoff_when_missing:
            session.pop(ACCOUNT_POST_AUTH_HANDOFF_SESSION_KEY, None)
    elif has_handoff:
        handoff = normalize_account_return_to(
            request,
            query_dict.get(ACCOUNT_HANDOFF_FIELD_NAME),
        )
        if handoff:
            session[ACCOUNT_POST_AUTH_HANDOFF_SESSION_KEY] = handoff
        else:
            session.pop(ACCOUNT_POST_AUTH_HANDOFF_SESSION_KEY, None)

    return True


def get_account_return_to(request):
    query_dicts = [
        (getattr(request, "POST", None), True),
        (request.GET, False),
    ]
    for query_dict, preserve_handoff_when_missing in query_dicts:
        if _store_account_navigation(
            request,
            query_dict,
            preserve_handoff_when_missing=preserve_handoff_when_missing,
        ):
            break

    return get_stored_account_return_to(request)


def get_post_auth_account_return_to(request):
    get_account_return_to(request)
    return (
        get_stored_account_post_auth_handoff(request)
        or get_stored_account_return_to(request)
    )


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
