from ninja.security import HttpBasicAuth
from ninja.errors import HttpError
from django.contrib.auth import authenticate


class BasicAuth(HttpBasicAuth):
    def authenticate(self, request, username, password, *args, **kwargs):
        user = authenticate(email=username, password=password)
        if user and user.is_authenticated and user.is_active:
            request.principal = user
            return user
        elif username or password:
            raise HttpError(401, "Invalid username or password")
