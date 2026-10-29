from base64 import b64decode
from io import BytesIO, StringIO
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import xml.etree.ElementTree as ET

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import HttpRequest
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .cards import build_ambassador_card, build_ambassador_card_png
from .emails import send_application_confirmation
from .models import CampusAmbassadorApplication
from .views import ambassador_card_download


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


class AmbassadorCardTests(SimpleTestCase):
    def test_details_are_xml_escaped_and_long_text_fits(self):
        application = CampusAmbassadorApplication(
            full_name='A <B> & ' + 'Long Name ' * 4,
            campus_name='Science & Technology Institute ' * 2,
        )
        card = build_ambassador_card(application)
        root = ET.fromstring(card)
        for field, value in [('name', application.full_name), ('campus', application.campus_name)]:
            element = root.find(f".//*[@id='ambassador-{field}']")
            self.assertEqual(element.text, ' '.join(value.split()))
            self.assertEqual(element.attrib['textLength'], element.attrib['data-max-width'])
        self.assertNotIn(b'Hamim Khan', card)
        self.assertNotIn(b'Govt. Graphics Arts Institute', card)
        self.assertIn(b'&lt;B&gt; &amp;', card)

    def test_portrait_is_embedded_and_clipped_in_the_original_diagonal(self):
        photo = BytesIO()
        Image.new('RGB', (2000, 1000), 'red').save(photo, 'JPEG')
        application = CampusAmbassadorApplication(
            full_name='Test Applicant', campus_name='Test Campus',
            picture=SimpleUploadedFile('photo.jpg', photo.getvalue(), content_type='image/jpeg'),
        )
        root = ET.fromstring(build_ambassador_card(application))
        portrait = root.find(".//*[@id='ambassador-photo']")
        self.assertEqual(portrait.attrib['preserveAspectRatio'], 'xMidYMin slice')
        self.assertEqual(portrait.attrib['x'], '441.24')
        self.assertEqual(portrait.attrib['y'], '172.58')
        self.assertIsNotNone(root.find(".//*[@clip-path='url(#ambassador-photo-mask)']"))
        uri = portrait.attrib['{http://www.w3.org/1999/xlink}href']
        with Image.open(BytesIO(b64decode(uri.split(',', 1)[1]))) as image:
            self.assertEqual(image.size, (1200, 600))
        self.assertEqual(root.find(".//*[@id='ambassador-photo-placeholder']").attrib['display'], 'none')

    def test_missing_photo_uses_placeholder(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            application = CampusAmbassadorApplication(
                full_name='Applicant', campus_name='Campus', picture='missing.jpg')
            root = ET.fromstring(build_ambassador_card(application))
        self.assertNotIn('display', root.find(".//*[@id='ambassador-photo-placeholder']").attrib)
        self.assertNotIn('{http://www.w3.org/1999/xlink}href',
                         root.find(".//*[@id='ambassador-photo']").attrib)

    def test_download_requires_staff(self):
        url = reverse('ambassador_card_download', args=[42])
        for user in [AnonymousUser(), SimpleNamespace(is_authenticated=True, is_staff=False)]:
            request = RequestFactory().get(url)
            request.user = user
            response = ambassador_card_download(request, 42)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login/', response.url)

    @patch('registration.views.get_object_or_404')
    def test_staff_download_is_private_optimized_png(self, get_application):
        get_application.return_value = CampusAmbassadorApplication(
            pk=42, full_name='Applicant', campus_name='Campus')
        request = RequestFactory().get(reverse('ambassador_card_download', args=[42]))
        request.user = SimpleNamespace(is_authenticated=True, is_staff=True)
        response = ambassador_card_download(request, 42)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertIn('biin_ambassador_42.png', response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'\x89PNG\r\n\x1a\n'))
        with Image.open(BytesIO(response.content)) as image:
            self.assertEqual(image.size, (1080, 1080))
            self.assertEqual(image.mode, 'RGB')

    def test_png_preserves_the_photo_mask_and_saved_position(self):
        photo = BytesIO()
        Image.new('RGB', (600, 760), 'red').save(photo, 'PNG')
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            application = CampusAmbassadorApplication(full_name='Applicant', campus_name='Campus')
            application.picture.save('photo.png', SimpleUploadedFile('photo.png', photo.getvalue()), save=False)
            with Image.open(BytesIO(build_ambassador_card_png(application))) as image:
                self.assertEqual(image.getpixel((900, 500)), (255, 0, 0))
                self.assertNotEqual(image.getpixel((300, 500)), (255, 0, 0))
                self.assertEqual(image.getpixel((900, 170)), (255, 255, 255))
            application.card_photo_x = 1080
            # Historical out-of-bounds positions are also corrected at render time.
            inside_mask = [(600, 176), (1077, 176), (1077, 587),
                           (1077, 998), (448, 998), (500, 587)]
            for scale, x, y in [(0.5, 1080, -1080), (1.5, 1080, 1080),
                                (1.5, -1080, -1080), (3, 1080, -1080), (3, -1080, 1080)]:
                with self.subTest(scale=scale, x=x, y=y):
                    application.card_photo_scale = scale
                    application.card_photo_x = x
                    application.card_photo_y = y
                    with Image.open(BytesIO(build_ambassador_card_png(application))) as image:
                        for point in inside_mask:
                            self.assertEqual(image.getpixel(point), (255, 0, 0), point)


@override_settings(SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['testserver'])
class AmbassadorCardEditorTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create(username='card-editor', is_staff=True)
        self.application = CampusAmbassadorApplication.objects.create(
            full_name='Test Applicant', email='card@example.com', campus_name='Test Campus')
        self.url = reverse('ambassador_card', args=[self.application.pk])
        self.client.force_login(self.staff)

    def test_saved_position_survives_reload_and_is_used_in_download(self):
        response = self.client.post(self.url, {
            'card_photo_x': '130.5', 'card_photo_y': '-74.2', 'card_photo_scale': '1.42',
            'full_name': 'Should not change',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['saved'])
        self.application.refresh_from_db()
        self.assertEqual(self.application.card_photo_x, 130.5)
        self.assertEqual(self.application.card_photo_y, -74.2)
        self.assertEqual(self.application.card_photo_scale, 1.42)
        self.assertEqual(self.application.full_name, 'Test Applicant')

        response = self.client.get(self.url)
        self.assertContains(response, 'translate(130.5 -74.2) translate(760.62 587.4) scale(1.42)')
        self.assertEqual(response.context['card_position'], {'x': 130.5, 'y': -74.2, 'scale': 1.42})
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertContains(response, 'Download PNG')
        self.assertNotContains(response, 'Download SVG')

        response = self.client.get(reverse('ambassador_card_download', args=[self.application.pk]))
        self.assertEqual(response['Content-Type'], 'image/png')
        with Image.open(BytesIO(response.content)) as image:
            self.assertEqual(image.size, (1080, 1080))

    def test_download_stays_png_even_if_svg_is_requested(self):
        url = reverse('ambassador_card_download', args=[self.application.pk])
        response = self.client.get(url, {'format': 'svg'}, HTTP_ACCEPT='image/svg+xml')
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertIn('.png', response['Content-Disposition'])
        self.assertNotIn('.svg', response['Content-Disposition'])

    def test_invalid_or_incomplete_positions_are_rejected_without_saving(self):
        invalid_values = [
            {'card_photo_x': '1081'}, {'card_photo_y': '-1081'},
            {'card_photo_scale': '0.49'}, {'card_photo_scale': '3.01'},
            {'card_photo_scale': '0.99'},
            {'card_photo_x': '0.1'}, {'card_photo_y': '-0.1'},
            {'card_photo_scale': '1.01', 'card_photo_x': '3.2'},
            {'card_photo_scale': '1.01', 'card_photo_y': '-4.2'},
            {'card_photo_x': 'nan'}, {'card_photo_y': 'inf'},
            {'card_photo_scale': 'NaN'}, {'card_photo_x': 'bad'},
        ]
        for invalid in invalid_values:
            with self.subTest(invalid=invalid):
                response = self.client.post(self.url, {
                    'card_photo_x': 0, 'card_photo_y': 0, 'card_photo_scale': 1, **invalid,
                })
                self.assertEqual(response.status_code, 400)
                self.assertIn('errors', response.json())
        self.assertEqual(self.client.post(self.url, {}).status_code, 400)
        self.application.refresh_from_db()
        self.assertEqual((self.application.card_photo_x, self.application.card_photo_y,
                          self.application.card_photo_scale), (0, 0, 1))

    def test_zoomed_boundary_positions_can_be_saved_and_reset(self):
        for x in [-638.7, 638.7]:
            for y in [-829.6, 829.6]:
                response = self.client.post(self.url, {
                    'card_photo_x': x, 'card_photo_y': y, 'card_photo_scale': 3,
                })
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['position'], {'x': x, 'y': y, 'scale': 3})
        response = self.client.post(self.url, {
            'card_photo_x': 0, 'card_photo_y': 0, 'card_photo_scale': 1,
        })
        self.assertEqual(response.status_code, 200)
        self.application.refresh_from_db()
        self.assertEqual(self.application.card_photo_scale, 1)
        self.assertEqual(self.application.card_photo_x, 0)
        self.assertEqual(self.application.card_photo_y, 0)

    def test_legacy_positions_are_kept_within_the_mask_when_viewed(self):
        CampusAmbassadorApplication.objects.filter(pk=self.application.pk).update(
            card_photo_x=500, card_photo_y=-500, card_photo_scale=0.5)
        response = self.client.get(self.url)
        self.assertEqual(response.context['card_position'], {'x': 0, 'y': 0, 'scale': 1})
        self.assertContains(response, 'translate(0 0) translate(760.62 587.4) scale(1)')

    def test_editor_and_position_save_require_staff_and_csrf(self):
        self.client.logout()
        for method in [self.client.get, self.client.post]:
            self.assertEqual(method(self.url).status_code, 302)
        self.staff.is_staff = False
        self.staff.save(update_fields=['is_staff'])
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.assertEqual(self.client.post(self.url).status_code, 302)

        self.staff.is_staff = True
        self.staff.save(update_fields=['is_staff'])
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.staff)
        self.assertEqual(csrf_client.post(self.url, {}).status_code, 403)

    def test_submissions_offer_view_card_instead_of_direct_download(self):
        response = self.client.get(reverse('applications'))
        self.assertContains(response, 'View Card')
        self.assertContains(response, f'data-card-url="{self.url}"')
        self.assertNotContains(response, 'Download Card (SVG)')
