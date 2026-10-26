from io import StringIO
from unittest.mock import patch

from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import HttpRequest
from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from .emails import send_application_confirmation
from .models import CampusAmbassadorApplication


class TestEmailCommandTests(SimpleTestCase):
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend')
    @patch('registration.management.commands.test_email.send_application_confirmation', return_value=1)
    @patch('builtins.input', return_value='recipient@example.com')
    def test_prompt_sends_to_entered_recipient(self, prompt, send):
        call_command('test_email', stdout=StringIO())
        self.assertEqual(send.call_args.kwargs['recipient'], 'recipient@example.com')
        self.assertTrue(send.call_args.kwargs['test_email'])
        self.assertIsNone(send.call_args.args[0].pk)

    def test_invalid_address_is_rejected(self):
        with self.assertRaises(CommandError):
            call_command('test_email', to='invalid')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend')
    def test_console_backend_does_not_report_real_delivery(self):
        with self.assertRaises(CommandError):
            call_command('test_email', to='recipient@example.com')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', REGISTRATION_RESPONSE_EMAIL='other@example.com')
    def test_sample_email_has_pdf_and_overrides_fixed_recipient(self):
        application = CampusAmbassadorApplication(full_name='Test Applicant', email='sample@example.com', created_at=timezone.now())
        sent = send_application_confirmation(application, HttpRequest(), recipient='recipient@example.com', test_email=True)
        self.assertEqual(sent, 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['recipient@example.com'])
        self.assertTrue(message.subject.startswith('[TEST]'))
        self.assertTrue(message.attachments[0].content.startswith(b'%PDF'))
        self.assertIn('No application was submitted', message.body)
        self.assertNotIn('Download application PDF', message.alternatives[0].content)
