from ninja.security import HttpBasicAuth
from django.contrib.auth import authenticate
from interfaces.api.http.errors import UnauthorizedError


class BasicAuth(HttpBasicAuth):
    def authenticate(self, request, username, password, *args, **kwargs):
        user = authenticate(email=username, password=password)
        if user and user.is_authenticated and user.is_active:
            request.user = user
            request.principal = user
            return user
        elif username or password:
            raise UnauthorizedError("Invalid username or password")

        return None
