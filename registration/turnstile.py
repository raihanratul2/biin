"""Validate registration challenges exclusively on the server."""
import json
import logging
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)


def verify_registration_turnstile(token, hostname):
    if not settings.TURNSTILE_SITE_KEY or not settings.TURNSTILE_SECRET_KEY:
        logger.error('Registration Turnstile keys are not configured')
        return False
    if not token or len(token) > 2048:
        return False
    request = Request(
        'https://challenges.cloudflare.com/turnstile/v0/siteverify',
        data=urlencode({'secret': settings.TURNSTILE_SECRET_KEY, 'response': token}).encode(),
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        method='POST',
    )
    try:
        with urlopen(request, timeout=10) as response:
            result = json.load(response)
    except (URLError, OSError, ValueError):
        logger.warning('Turnstile verification service unavailable')
        return False
    return (
        isinstance(result, dict)
        and result.get('success') is True
        and result.get('action') == 'registration'
        and result.get('hostname') == hostname
    )
