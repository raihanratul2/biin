from base64 import b64decode
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError
import xml.etree.ElementTree as ET

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .background_removal import BackgroundRemovalError, remove_card_background
from .cards import build_ambassador_card
from .models import CampusAmbassadorApplication, IntegrationRecord


@override_settings(REMOVE_BG_API_KEY='test-key', SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['testserver'])
class BackgroundRemovalTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        settings_override = override_settings(MEDIA_ROOT=self.directory.name)
        settings_override.enable()
        self.addCleanup(settings_override.disable)
        image = BytesIO()
        Image.new('RGB', (60, 76), 'red').save(image, 'PNG')
        self.application = CampusAmbassadorApplication.objects.create(
            full_name='Test Applicant', campus_name='Test Campus', email='test@example.com',
            picture=SimpleUploadedFile('portrait.png', image.getvalue(), content_type='image/png'))
        cutout = BytesIO()
        Image.new('RGBA', (60, 76), (255, 0, 0, 0)).save(cutout, 'PNG')
        self.cutout_bytes = cutout.getvalue()
        self.url = reverse('ambassador_card', args=[self.application.pk])

    def mock_response(self, urlopen):
        response = MagicMock()
        response.read.return_value = self.cutout_bytes
        urlopen.return_value.__enter__.return_value = response

    @patch('registration.background_removal.urlopen')
    def test_stores_transparent_cutout_and_reuses_without_another_call(self, urlopen):
        self.mock_response(urlopen)
        original = self.application.picture.name
        remove_card_background(self.application)
        remove_card_background(self.application)
        urlopen.assert_called_once()
        self.assertEqual(IntegrationRecord.objects.filter(kind='remove_bg', status='success').count(), 1)
        api_request = urlopen.call_args.args[0]
        self.assertEqual(api_request.full_url, 'https://api.remove.bg/v1.0/removebg')
        self.assertEqual(api_request.get_header('X-api-key'), 'test-key')
        self.assertIn(b'name="image_file"', api_request.data)
        self.application.refresh_from_db()
        self.assertEqual(self.application.picture.name, original)
        root = ET.fromstring(build_ambassador_card(self.application))
        uri = root.find(".//*[@id='ambassador-photo']").get('{http://www.w3.org/1999/xlink}href')
        with Image.open(BytesIO(b64decode(uri.split(',')[1]))) as image:
            self.assertEqual(image.getpixel((0, 0))[3], 0)
        self.application.picture.save('replacement.png', SimpleUploadedFile('new.png', self.cutout_bytes))
        remove_card_background(self.application)
        self.assertEqual(urlopen.call_count, 2)

    @patch('registration.background_removal.urlopen')
    def test_failures_keep_original_and_do_not_cache(self, urlopen):
        for failure in [HTTPError('https://api.remove.bg', 402, 'credits', {}, None), URLError('timeout')]:
            with self.subTest(failure=failure):
                urlopen.side_effect = failure
                with self.assertRaises(BackgroundRemovalError):
                    remove_card_background(self.application)
                self.application.refresh_from_db()
                self.assertFalse(self.application.card_cutout)
                self.assertTrue(self.application.picture.storage.exists(self.application.picture.name))
                record = IntegrationRecord.objects.first()
                self.assertEqual(record.status, IntegrationRecord.Status.FAILED)
        self.assertEqual(IntegrationRecord.objects.count(), 2)

    @override_settings(REMOVE_BG_API_KEY='')
    @patch('registration.background_removal.urlopen')
    def test_missing_key_never_calls_api(self, urlopen):
        with self.assertRaisesMessage(BackgroundRemovalError, 'REMOVE_BG_API_KEY'):
            remove_card_background(self.application)
        urlopen.assert_not_called()
        self.assertEqual(IntegrationRecord.objects.count(), 0)

    @patch('registration.background_removal.urlopen')
    def test_only_staff_post_processes_image_and_get_is_read_only(self, urlopen):
        self.mock_response(urlopen)
        self.client.post(self.url, {'action': 'remove_background'})
        urlopen.assert_not_called()
        user = get_user_model().objects.create_user('editor', is_staff=True)
        self.client.force_login(user)
        self.assertContains(self.client.get(self.url), 'value="remove_background"')
        urlopen.assert_not_called()
        response = self.client.post(self.url, {'action': 'remove_background'})
        self.assertRedirects(response, self.url)
        urlopen.assert_called_once()
        self.assertContains(self.client.get(self.url), 'Remove Background Again')
        self.client.get(reverse('ambassador_card_download', args=[self.application.pk]))
        urlopen.assert_called_once()
        self.client.post(self.url, {'action': 'remove_background'})
        urlopen.assert_called_once()
        response = self.client.post(self.url, {'action': 'remove_background_again'})
        self.assertRedirects(response, self.url)
        self.assertEqual(urlopen.call_count, 2)

    @patch('registration.background_removal.urlopen')
    def test_failed_retry_preserves_previous_cutout(self, urlopen):
        self.mock_response(urlopen)
        remove_card_background(self.application)
        self.application.refresh_from_db()
        saved_cutout = self.application.card_cutout.name
        urlopen.side_effect = URLError('timeout')
        with self.assertRaises(BackgroundRemovalError):
            remove_card_background(self.application, force=True)
        self.application.refresh_from_db()
        self.assertEqual(self.application.card_cutout.name, saved_cutout)
        self.assertTrue(self.application.card_cutout.storage.exists(saved_cutout))
