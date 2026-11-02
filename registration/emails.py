"""Submission confirmation and signed, time-limited PDF links."""
from io import BytesIO
from email.mime.image import MIMEImage
from pathlib import Path
import secrets
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .card_sharing import ambassador_card_links
from .pdf import build_application_pdf
from .integration_records import send_recorded_email
from .models import IntegrationRecord
from .links import request_site_url


SOCIAL_ICONS = ('facebook', 'whatsapp', 'instagram', 'x', 'linkedin')


def email_context(request, *, title, preheader):
    site_url = request_site_url(request)
    contact = settings.BIIN_CONTACT_EMAIL
    terms = urlsplit(settings.BIIN_TERMS_URL)
    terms_url = (site_url + '/' + urlunsplit(('', '', terms.path, terms.query, terms.fragment)).lstrip('/')
                 if settings.BIIN_TERMS_URL else f'mailto:{contact}?subject=Campus%20Ambassador%20Program%20Terms')
    return {
        'email_title': title, 'preheader': preheader,
        'site_url': site_url,
        'about_url': site_url + reverse('about'),
        'contact_url': site_url + reverse('contact'),
        'terms_url': terms_url,
        'contact_email': contact, 'contact_phone': settings.BIIN_CONTACT_PHONE,
        'office_address': settings.BIIN_OFFICE_ADDRESS,
        'maps_url': 'https://maps.app.goo.gl/D1tABFtRPJzuLayMA',
        'year': timezone.localdate().year,
    }


def attach_inline_image(message, content, cid, filename):
    image = MIMEImage(content, _subtype='png')
    image.add_header('Content-ID', f'<{cid}>')
    image.add_header('Content-Disposition', 'inline', filename=filename)
    message.attach(image)


def email_static_file(name):
    asset = finders.find(name)
    if not asset:
        asset = Path(settings.STATIC_ROOT or settings.BASE_DIR / 'static') / name
        if not asset.is_file():
            asset = settings.BASE_DIR / 'static' / name
    return Path(asset)


def attach_email_logo(message):
    attach_inline_image(message, email_static_file('BIIN_Logo.png').read_bytes(), 'biin-logo', 'biin-logo.png')


def attach_social_icons(message):
    for icon in SOCIAL_ICONS:
        attach_inline_image(message, email_static_file(f'social/{icon}.png').read_bytes(),
                            f'social-{icon}', f'{icon}.png')


def application_pdf_url(application, request):
    token = signing.dumps(
        {'application_id': application.pk, 'nonce': secrets.token_urlsafe(24)},
        salt='registration.pdf',
    )
    path = reverse('application_pdf_download', kwargs={'token': token})
    return request_site_url(request) + path


def send_application_confirmation(application, request, *, recipient=None, test_email=False):
    context = email_context(request, title='Application received',
                            preheader='Your BIIN Campus Ambassador application has been received.')
    context.update({
        'application': application,
        'pdf_url': '' if test_email else application_pdf_url(application, request),
        'test_email': test_email,
        'link_hours': settings.REGISTRATION_PDF_LINK_MAX_AGE / 3600,
        'contact_email': settings.BIIN_CONTACT_EMAIL,
    })
    message = EmailMultiAlternatives(
        subject=('[TEST] ' if test_email else '') + 'BIIN Campus Ambassador — Application received',
        body=render_to_string('emails/application_confirmation.txt', context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient or settings.REGISTRATION_RESPONSE_EMAIL or application.email],
        reply_to=[settings.BIIN_CONTACT_EMAIL], 
    )
    message.attach_alternative(render_to_string('emails/application_confirmation.html', context), 'text/html')
    pdf = BytesIO()
    build_application_pdf(pdf, [application])
    message.attach('biin_application.pdf', pdf.getvalue(), 'application/pdf')
    attach_email_logo(message)
    return send_recorded_email(message, application, request,
                               kind=IntegrationRecord.Kind.CONFIRMATION, test_email=test_email)


def send_ambassador_selection(application, request, *, recipient=None, test_email=False):
    """Send a selection announcement only when explicitly invoked by staff."""
    from .cards import build_ambassador_card_png

    context = email_context(request, title="You're selected!",
                            preheader='Congratulations! Welcome to the BIIN Campus Ambassador Program.')
    context.update({'application': application, 'test_email': test_email})
    if application.pk and not test_email:
        context.update(ambassador_card_links(application, request))
    message = EmailMultiAlternatives(
        subject=('[TEST] ' if test_email else '') + 'Congratulations! You’re selected as a BIIN Campus Ambassador',
        body=render_to_string('emails/ambassador_selection.txt', context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient or application.email],
        reply_to=[settings.BIIN_CONTACT_EMAIL],
    )
    message.attach_alternative(render_to_string('emails/ambassador_selection.html', context), 'text/html')
    card = build_ambassador_card_png(application)
    message.attach('biin_ambassador_card.png', card, 'image/png')
    preview = BytesIO()
    with Image.open(BytesIO(card)) as image:
        image.thumbnail((440, 440), Image.Resampling.LANCZOS)
        image.save(preview, format='PNG')
    attach_inline_image(message, preview.getvalue(),
                        'ambassador-card', 'biin_ambassador_card_preview.png')
    attach_email_logo(message)
    if context.get('card_download_url'):
        attach_social_icons(message)
    return send_recorded_email(message, application, request,
                               kind=IntegrationRecord.Kind.SELECTION, test_email=test_email)
