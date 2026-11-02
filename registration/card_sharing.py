"""Signed links expose only an ambassador's shareable card, never their application."""
import secrets
from urllib.parse import urlencode

from django.core import signing
from django.urls import reverse

from .links import request_site_url

CARD_SHARE_SALT = 'registration.ambassador-card'


def ambassador_card_links(application, request, *, token=None):
    # Shared social posts should keep working; these links have no expiry.
    token = token or signing.dumps(
        {'application_id': application.pk, 'nonce': secrets.token_urlsafe(24)},
        salt=CARD_SHARE_SALT,
    )
    site_url = request_site_url(request)
    share_url = site_url + reverse('ambassador_card_share', kwargs={'token': token})
    image_url = site_url + reverse('ambassador_card_image', kwargs={'token': token})
    return card_share_links(share_url, image_url, application.campus_name)


def card_share_links(share_url, image_url, campus_name):
    text = f"I'm proud to join BIIN as a Campus Ambassador representing {campus_name}!"
    return {
        'card_share_url': share_url,
        'card_image_url': image_url,
        'card_download_url': image_url + '?download=1',
        'facebook_share_url': 'https://www.facebook.com/sharer/sharer.php?' + urlencode({'u': share_url}),
        'whatsapp_share_url': 'https://wa.me/?' + urlencode({'text': f'{text} {share_url}'}),
        'x_share_url': 'https://x.com/intent/tweet?' + urlencode({'text': text, 'url': share_url}),
        'instagram_share_url': share_url + '#instagram',
        'linkedin_share_url': 'https://www.linkedin.com/sharing/share-offsite/?' + urlencode({'url': share_url}),
    }
