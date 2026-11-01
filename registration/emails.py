"""Submission confirmation and signed, time-limited PDF links."""
from io import BytesIO
from email.mime.image import MIMEImage
from pathlib import Path
import secrets

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .pdf import build_application_pdf
from .integration_records import send_recorded_email
from .models import IntegrationRecord


def email_context(request, *, title, preheader):
    site_url = settings.SITE_URL or request.build_absolute_uri('/').rstrip('/')
    contact = settings.BIIN_CONTACT_EMAIL
    return {
        'email_title': title, 'preheader': preheader,
        'site_url': site_url,
        'about_url': site_url + reverse('about'),
        'contact_url': site_url + reverse('contact'),
        'terms_url': settings.BIIN_TERMS_URL or f'mailto:{contact}?subject=Campus%20Ambassador%20Program%20Terms',
        'contact_email': contact, 'contact_phone': settings.BIIN_CONTACT_PHONE,
        'office_address': settings.BIIN_OFFICE_ADDRESS,
        'year': timezone.localdate().year,
    }


def attach_inline_image(message, content, cid, filename):
    image = MIMEImage(content, _subtype='png')
    image.add_header('Content-ID', f'<{cid}>')
    image.add_header('Content-Disposition', 'inline', filename=filename)
    message.attach(image)


def attach_email_logo(message):
    logo = finders.find('BIIN_Logo.png')
    if not logo:
        logo = Path(settings.STATIC_ROOT or settings.BASE_DIR / 'static') / 'BIIN_Logo.png'
        if not logo.is_file():
            logo = settings.BASE_DIR / 'static' / 'BIIN_Logo.png'
    attach_inline_image(message, Path(logo).read_bytes(), 'biin-logo', 'biin-logo.png')


def application_pdf_url(application, request):
    token = signing.dumps(
        {'application_id': application.pk, 'nonce': secrets.token_urlsafe(24)},
        salt='registration.pdf',
    )
    path = reverse('application_pdf_download', kwargs={'token': token})
    return f'{settings.SITE_URL}{path}' if settings.SITE_URL else request.build_absolute_uri(path)


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
    message = EmailMultiAlternatives(
        subject=('[TEST] ' if test_email else '') + 'Congratulations! You’re selected as a BIIN Campus Ambassador',
        body=render_to_string('emails/ambassador_selection.txt', context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient or application.email],
        reply_to=[settings.BIIN_CONTACT_EMAIL],
    )
    message.attach_alternative(render_to_string('emails/ambassador_selection.html', context), 'text/html')
    attach_inline_image(message, build_ambassador_card_png(application),
                        'ambassador-card', 'biin_ambassador_card.png')
    attach_email_logo(message)
    return send_recorded_email(message, application, request,
                               kind=IntegrationRecord.Kind.SELECTION, test_email=test_email)
