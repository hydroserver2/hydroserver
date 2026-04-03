from ninja.security import HttpBearer
from ninja.errors import HttpError
from allauth.headless.internal.sessionkit import authenticate_by_x_session_token


class BearerAuth(HttpBearer):
    def authenticate(self, request, token):
        user = authenticate_by_x_session_token(token)
        if user and user[0] and user[0].is_authenticated and user[0].is_active:
            request.principal = user[0]
            return user[0]
        elif token:
            raise HttpError(401, "Invalid token")
