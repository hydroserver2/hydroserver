from django.http import HttpResponse


class CloudHealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.rstrip("/") == "/health-check":
            return HttpResponse("OK", status=200)

        return self.get_response(request)
