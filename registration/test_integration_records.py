import importlib
from smtplib import SMTPException
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import clear_url_caches, resolve, Resolver404, reverse

from .models import CampusAmbassadorApplication, IntegrationRecord


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['testserver'], SITE_URL='https://biin.example')
class CardEmailRecordsTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user('staff', is_staff=True)
        self.application = CampusAmbassadorApplication.objects.create(
            full_name='Test Applicant', email='applicant@example.com', campus_name='Test University')
        self.url = reverse('ambassador_card', args=[self.application.pk])
        self.client.force_login(self.staff)

    def test_send_and_resend_are_explicit_and_recorded(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Send Card Email')
        self.assertEqual(IntegrationRecord.objects.count(), 0)
        self.client.post(self.url, {'action': 'send_card_email'})
        self.assertEqual(len(mail.outbox), 1)
        record = IntegrationRecord.objects.get()
        self.assertEqual(record.kind, IntegrationRecord.Kind.SELECTION)
        self.assertEqual(record.status, IntegrationRecord.Status.SUCCESS)
        self.assertEqual(record.actor, self.staff)
        self.assertEqual(record.recipient, self.application.email)
        self.assertIsNotNone(record.completed_at)
        self.assertContains(self.client.get(self.url), 'Send Again')
        self.assertEqual(len(mail.outbox), 1)
        # A repeated initial request does not send again without the resend action.
        self.client.post(self.url, {'action': 'send_card_email'})
        self.assertEqual(len(mail.outbox), 1)
        self.client.post(self.url, {'action': 'send_card_email_again'})
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(IntegrationRecord.objects.count(), 2)

    @patch('registration.emails.EmailMultiAlternatives.send', side_effect=SMTPException('secret diagnostic'))
    def test_failure_is_recorded_and_keeps_initial_send_button(self, send):
        with self.assertLogs('registration.views', level='ERROR'):
            response = self.client.post(self.url, {'action': 'send_card_email'})
        self.assertRedirects(response, self.url)
        record = IntegrationRecord.objects.get()
        self.assertEqual(record.status, IntegrationRecord.Status.FAILED)
        self.assertEqual(record.error_type, 'SMTPException')
        self.assertNotIn('secret diagnostic', str(record.__dict__))
        self.assertContains(self.client.get(self.url), 'Send Card Email')

    def test_non_staff_cannot_send(self):
        user = get_user_model().objects.create_user('ordinary')
        self.client.force_login(user)
        self.assertEqual(self.client.post(self.url, {'action': 'send_card_email'}).status_code, 302)
        self.assertEqual(IntegrationRecord.objects.count(), 0)


@override_settings(SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['testserver'])
class AdminRecordPermissionsTests(TestCase):
    def setUp(self):
        self.record = IntegrationRecord.objects.create(kind=IntegrationRecord.Kind.REMOVE_BG)
        self.staff = get_user_model().objects.create_user('staff', is_staff=True)
        self.staff.user_permissions.add(*Permission.objects.filter(content_type__model='integrationrecord'))
        self.superuser = get_user_model().objects.create_superuser('super', 'super@example.com', 'test-password')

    def test_staff_with_all_model_permissions_cannot_access_records(self):
        self.client.force_login(self.staff)
        index = self.client.get(reverse('admin:index'))
        self.assertNotContains(index, 'Integration records')
        for route, args in [('changelist', []), ('change', [self.record.pk]),
                            ('add', []), ('delete', [self.record.pk])]:
            response = self.client.get(reverse(f'admin:registration_integrationrecord_{route}', args=args))
            self.assertEqual(response.status_code, 403)

    def test_superuser_can_review_records_and_totals_but_cannot_edit(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('admin:registration_integrationrecord_changelist'))
        self.assertContains(response, 'All-time totals:')
        self.assertEqual(response.context['integration_totals']['api_calls'], 1)
        detail = reverse('admin:registration_integrationrecord_change', args=[self.record.pk])
        self.assertEqual(self.client.get(detail).status_code, 200)
        self.assertEqual(self.client.post(detail, {'status': 'success'}).status_code, 403)
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, IntegrationRecord.Status.PENDING)

    def test_admin_toggle_removes_routes(self):
        import BIIN.urls
        try:
            with override_settings(DJANGO_ADMIN_ENABLED=False):
                importlib.reload(BIIN.urls)
                clear_url_caches()
                with self.assertRaises(Resolver404):
                    resolve('/admin/')
                self.assertEqual(resolve('/login/').url_name, 'login')
            with override_settings(DJANGO_ADMIN_ENABLED=True):
                importlib.reload(BIIN.urls)
                clear_url_caches()
                self.assertEqual(resolve('/admin/').url_name, 'index')
        finally:
            importlib.reload(BIIN.urls)
            clear_url_caches()
