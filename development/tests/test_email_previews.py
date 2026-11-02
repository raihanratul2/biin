from contextlib import contextmanager
import importlib
import subprocess
import sys
from unittest.mock import patch

from django.conf import settings
from django.http import Http404
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import Resolver404, clear_url_caches, resolve, reverse


@override_settings(SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['testserver'])
class DevelopmentEmailPreviewTests(SimpleTestCase):
    @contextmanager
    def debug_urls(self, enabled):
        import BIIN.urls

        try:
            with override_settings(DEBUG=enabled):
                importlib.reload(BIIN.urls)
                clear_url_caches()
                yield
        finally:
            importlib.reload(BIIN.urls)
            clear_url_caches()

    def test_index_and_templates_render_without_database_access_or_sending_mail(self):
        with self.debug_urls(True), patch('django.core.mail.EmailMultiAlternatives.send') as send:
            self.assertContains(self.client.get(reverse('development:email_index')), 'Email previews')
            for name in ['confirmation', 'selection']:
                response = self.client.get(reverse('development:' + name))
                self.assertContains(response, 'BIIN Demo Ambassador')
                self.assertContains(response, 'data:image/png;base64,')
                self.assertContains(response, 'This is an automated email.')
                self.assertNotContains(response, 'cid:')
                self.assertNotContains(response, 'This is a test email')
                self.assertEqual(response['Cache-Control'], 'no-store')
                self.assertContains(self.client.get(reverse('development:' + name) + '?test=1'), 'This is a test email')
                text = self.client.get(reverse('development:' + name) + '?format=txt')
                self.assertTrue(text['Content-Type'].startswith('text/plain'))
                self.assertContains(text, 'BIIN Demo Ambassador')
            send.assert_not_called()

    def test_sample_card_pdf_and_share_page_work_without_saved_applications(self):
        with self.debug_urls(True):
            response = self.client.get(reverse('development:card_image') + '?download=1')
            self.assertEqual(response['Content-Type'], 'image/png')
            self.assertTrue(response.content.startswith(b'\x89PNG'))
            self.assertIn('attachment;', response['Content-Disposition'])
            response = self.client.get(reverse('development:application_pdf'))
            self.assertTrue(response.content.startswith(b'%PDF'))
            share = self.client.get(reverse('development:card_share'))
            self.assertContains(share, 'LinkedIn')
            self.assertContains(share, '/__dev__/emails/card.png')

    def test_production_has_no_development_routes(self):
        with self.debug_urls(False):
            for path in ['/__dev__/emails/', '/__dev__/emails/ambassador-selection/',
                         '/__dev__/emails/card.png', '/__dev__/emails/application.pdf']:
                with self.assertRaises(Resolver404):
                    resolve(path)
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_debug_guard_blocks_a_cached_view_before_loading_preview_data(self):
        from development.views import email_preview

        with override_settings(DEBUG=False), patch('development.views.preview_context') as context:
            with self.assertRaises(Http404):
                email_preview(RequestFactory().get('/'), 'selection')
            context.assert_not_called()

    def test_fresh_production_process_does_not_import_development_modules(self):
        script = '''
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'BIIN.settings'
import django
django.setup()
from django.test import override_settings
with override_settings(DEBUG=False):
    import BIIN.urls
    import sys
    assert not any(name == 'development' or name.startswith('development.') for name in sys.modules)
'''
        result = subprocess.run([sys.executable, '-c', script], cwd=settings.BASE_DIR,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
