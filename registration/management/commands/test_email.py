from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.http import HttpRequest
from django.utils import timezone

from registration.emails import send_application_confirmation
from registration.models import CampusAmbassadorApplication


class Command(BaseCommand):
    help = 'Send a real test confirmation email with a sample PDF to the entered recipient.'

    def add_arguments(self, parser):
        parser.add_argument('--to', help='Recipient email; prompts when omitted.')

    def handle(self, *args, **options):
        recipient = (options['to'] or input('To email: ')).strip()
        try:
            validate_email(recipient)
        except ValidationError:
            raise CommandError('Enter a valid recipient email address.')
        if settings.EMAIL_BACKEND != 'django.core.mail.backends.smtp.EmailBackend':
            raise CommandError('Set DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend to send real mail.')
        application = CampusAmbassadorApplication(
            full_name='BIIN Test Applicant', email=recipient,
            campus_name='Test University', department='Computer Science',
            student_id='TEST-001', academic_year='3rd Year',
            created_at=timezone.now(),
            motivation='Sample application for email delivery testing.',
        )
        try:
            sent = send_application_confirmation(
                application, HttpRequest(), recipient=recipient, test_email=True,
            )
        except Exception as exc:
            raise CommandError(f'Email sending failed ({type(exc).__name__}). Check SES credentials and sender/recipient verification.') from exc
        if sent != 1:
            raise CommandError('The email backend did not accept the message.')
        self.stdout.write(self.style.SUCCESS(f'Test email accepted by SMTP for {recipient}. Check inbox/spam.'))
