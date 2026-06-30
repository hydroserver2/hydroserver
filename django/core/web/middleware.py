from django.conf import settings


class NoIndexMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if getattr(settings, "NOINDEX", False):
            response["X-Robots-Tag"] = "noindex"

        return response
