"""Persist outbound mail attempts without storing message bodies or credentials."""
from django.conf import settings
from django.utils import timezone

from .models import IntegrationRecord


def request_actor(request):
    user = getattr(request, 'user', None)
    return user if user and user.is_authenticated and user.pk else None


def send_recorded_email(message, application, request, *, kind, test_email=False):
    record = IntegrationRecord.objects.create(
        kind=kind, application_id=application.pk, actor=request_actor(request),
        recipient=message.to[0], subject=message.subject,
        backend=settings.EMAIL_BACKEND, test_email=test_email,
    )
    try:
        sent = message.send(fail_silently=False)
    except Exception as exc:
        record.status = IntegrationRecord.Status.FAILED
        record.error_type = type(exc).__name__
        raise
    else:
        record.status = IntegrationRecord.Status.SUCCESS if sent == 1 else IntegrationRecord.Status.FAILED
        if sent != 1:
            record.error_type = 'MessageNotAccepted'
        return sent
    finally:
        record.completed_at = timezone.now()
        record.save(update_fields=['status', 'error_type', 'completed_at'])
