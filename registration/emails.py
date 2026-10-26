"""Submission confirmation and signed, time-limited PDF links."""
from io import BytesIO
import secrets

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from .pdf import build_application_pdf


def application_pdf_url(application, request):
    token = signing.dumps(
        {'application_id': application.pk, 'nonce': secrets.token_urlsafe(24)},
        salt='registration.pdf',
    )
    path = reverse('application_pdf_download', kwargs={'token': token})
    return f'{settings.SITE_URL}{path}' if settings.SITE_URL else request.build_absolute_uri(path)


def send_application_confirmation(application, request, *, recipient=None, test_email=False):
    context = {
        'application': application,
        'pdf_url': '' if test_email else application_pdf_url(application, request),
        'test_email': test_email,
        'link_hours': settings.REGISTRATION_PDF_LINK_MAX_AGE / 3600,
        'contact_email': settings.BIIN_CONTACT_EMAIL,
    }
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
    return message.send(fail_silently=False)
