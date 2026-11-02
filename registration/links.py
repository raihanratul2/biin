"""Build absolute links using the host handling the current request."""
from django.conf import settings


def request_site_url(request):
    if request.META.get('HTTP_HOST') or request.META.get('SERVER_NAME'):
        return request.build_absolute_uri('/').rstrip('/')
    # Management commands have no incoming HTTP request.
    return settings.SITE_URL or request.build_absolute_uri('/').rstrip('/')
