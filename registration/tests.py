from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch
import io
import tempfile
from PIL import Image


def uploaded_picture():
    output = io.BytesIO()
    Image.new("RGB", (300, 380), "navy").save(output, format="PNG")
    return SimpleUploadedFile("portrait.png", output.getvalue(), content_type="image/png")

from django.urls import reverse

from registration.models import CampusAmbassadorApplication, RegistrationSetting
from registration.forms import CampusAmbassadorApplicationForm


class CampusAmbassadorFlowTests(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        override = override_settings(MEDIA_ROOT=media.name)
        override.enable()
        self.addCleanup(override.disable)

    def test_picture_is_required_and_must_be_an_image(self):
        form = CampusAmbassadorApplicationForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('picture', form.errors)
        form = CampusAmbassadorApplicationForm(data={}, files={
            'picture': SimpleUploadedFile('fake.png', b'not an image', content_type='image/png'),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('picture', form.errors)

    def test_declarations_must_be_accepted(self):
        form = CampusAmbassadorApplicationForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('declaration_accuracy', form.errors)
        self.assertIn('declaration_terms', form.errors)

    def test_home_page_loads(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_registration_form_loads(self):
        response = self.client.get(reverse('registration_form'))
        self.assertEqual(response.status_code, 200)

    def test_applications_list_requires_staff_login(self):
        response = self.client.get(reverse('applications'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_staff_user_can_access_applications_list(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username='staffuser', password='secret123', is_staff=True)
        self.client.login(username='staffuser', password='secret123')

        response = self.client.get(reverse('applications'))

        self.assertEqual(response.status_code, 200)

    def test_registration_form_is_hidden_when_closed(self):
        RegistrationSetting.objects.update_or_create(pk=1, defaults={'registration_open': False})

        response = self.client.get(reverse('registration_form'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Registration Closed')

    @patch('registration.views.verify_registration_turnstile', return_value=True)
    def test_registration_submission_creates_record_and_redirects_to_success(self, verification):
        payload = {
            'picture': uploaded_picture(),
            'full_name': 'Ayesha Rahman',
            'email': 'ayesha@example.com',
            'phone_number': '8801700000000',
            'address': 'Dhaka',
            'campus_name': 'University of Dhaka',
            'department': 'Computer Science',
            'student_id': 'CS-2024-01',
            'academic_year': '3rd Year',
            'facebook_link': 'https://facebook.com/ayesha',
            'linkedin_link': 'https://linkedin.com/in/ayesha',
            'website': 'https://ayesha.dev',
            'has_previous_campus_ambassador': 'No',
            'previous_experience_details': 'No prior campus ambassador experience.',
            'skills': ['Communication', 'Leadership'],
            'has_organized_campus_events': 'Yes',
            'motivation': 'I want to help students connect with opportunities.',
            'promotion_plan': 'I will run campaigns and connect with departments.',
            'weekly_hours': '6-8 hours/week',
            'has_active_student_network': 'Yes',
            'activities_to_organize': 'Orientation, workshops, social media campaigns',
            'declaration_accuracy': 'on',
            'declaration_terms': 'on',
        }

        response = self.client.post(reverse('registration_form'), payload)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('registration_success'))
        application = CampusAmbassadorApplication.objects.get(email='ayesha@example.com')
        self.assertTrue(application.picture.storage.exists(application.picture.name))
        with application.picture.open('rb') as stored:
            with Image.open(stored) as image:
                self.assertEqual(image.format, 'JPEG')
                self.assertEqual(image.size, (600, 760))


class ApplicationPDFTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(username='pdf-staff', is_staff=True)
        self.client.force_login(self.staff)
        self.first = CampusAmbassadorApplication.objects.create(
            full_name='First <Applicant>', email='first@example.com',
            motivation='A long answer & details. ' * 300,
        )
        self.second = CampusAmbassadorApplication.objects.create(
            full_name='Second Applicant', email='second@example.com',
        )

    def page_count(self, response):
        import re
        return len(re.findall(rb'/Type\s*/Page\b', response.content))

    def test_single_print_is_inline_and_one_page(self):
        response = self.client.get(reverse('export_pdf'), {'ids': self.first.pk, 'print': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Disposition'].startswith('inline;'))
        self.assertEqual(self.page_count(response), 1)

    def test_selected_export_has_one_page_per_unique_submission(self):
        response = self.client.get(reverse('export_pdf'), {'ids': [self.first.pk, self.second.pk, self.first.pk]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.page_count(response), 2)
        self.assertTrue(response['Content-Disposition'].startswith('attachment;'))

    def test_export_all_uses_same_pagination(self):
        response = self.client.get(reverse('export_pdf'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.page_count(response), 2)

    def test_invalid_selection_does_not_export_everyone(self):
        for ids in ['', 'invalid', '-1', '9' * 30]:
            response = self.client.get(reverse('export_pdf'), {'ids': ids})
            self.assertEqual(response.status_code, 400)
        response = self.client.get(reverse('export_pdf'), {'ids': 999999})
        self.assertEqual(response.status_code, 404)

    def test_nonstaff_cannot_export(self):
        self.staff.is_staff = False
        self.staff.save()
        response = self.client.get(reverse('export_pdf'), {'ids': self.first.pk})
        self.assertEqual(response.status_code, 302)

    def test_list_has_selection_and_single_print_links(self):
        response = self.client.get(reverse('applications'))
        self.assertContains(response, 'id="selectAll"')
        self.assertContains(response, f'name="ids" value="{self.first.pk}"')
        self.assertContains(response, f'?ids={self.first.pk}&amp;print=1')

    def test_blank_form_is_one_page_without_submissions(self):
        CampusAmbassadorApplication.objects.all().delete()
        response = self.client.get(reverse('export_pdf'), {'blank': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.page_count(response), 1)
        self.assertTrue(response['Content-Disposition'].startswith('inline;'))


class PDFFieldLimitTests(TestCase):
    def test_form_shows_limits_and_character_counters(self):
        from django.test import override_settings
        from registration.pdf_layout import FIELD_LIMITS

        with override_settings(SECURE_SSL_REDIRECT=False):
            response = self.client.get(reverse('registration_form'))
        for name, limit in FIELD_LIMITS.items():
            with self.subTest(field=name):
                self.assertContains(response, f'data-character-count="id_{name}"')
                self.assertContains(response, f'maxlength="{limit}"')
                self.assertContains(response, f'data-character-count="id_{name}" hidden></small>')

    def test_pdf_limits_are_enforced_by_models_and_forms(self):
        from django.core.exceptions import ValidationError
        from registration.pdf_layout import FIELD_LIMITS

        form = CampusAmbassadorApplicationForm()
        for name, limit in FIELD_LIMITS.items():
            with self.subTest(field=name):
                model_field = CampusAmbassadorApplication._meta.get_field(name)
                self.assertEqual(model_field.max_length, limit)
                self.assertEqual(form.fields[name].widget.attrs['maxlength'], limit)
                # Run length validators directly so URL/email syntax is independent.
                for field in (model_field, form.fields[name]):
                    field.run_validators('W' * limit) if name not in {
                        'email', 'facebook_link', 'linkedin_link', 'website'
                    } else None
                    with self.assertRaises(ValidationError):
                        field.run_validators('W' * (limit + 1))

    def test_maximum_length_answers_stay_on_one_a4_page(self):
        import io
        import re
        from django.utils import timezone
        from registration.pdf import build_application_pdf
        from registration.pdf_layout import FIELD_LIMITS

        application = CampusAmbassadorApplication(
            **{name: 'W' * limit for name, limit in FIELD_LIMITS.items()},
            created_at=timezone.now(),
        )
        output = io.BytesIO()
        build_application_pdf(output, [None, application])
        pdf = output.getvalue()
        self.assertEqual(len(re.findall(rb'/Type\s*/Page\b', pdf)), 2)
        boxes = re.findall(rb'/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]', pdf)
        self.assertEqual(len(boxes), 2)
        for box in boxes:
            self.assertAlmostEqual(float(box[2]), 595.276, places=2)
            self.assertAlmostEqual(float(box[3]), 841.890, places=2)


class PDFWritingLineTests(TestCase):
    def test_blank_and_filled_writing_lines_have_identical_positions(self):
        import io
        from unittest.mock import patch
        from django.utils import timezone
        from registration.pdf import AnswerLine, TwoLineAnswer, build_application_pdf
        from registration.pdf_layout import FIELD_LIMITS

        application = CampusAmbassadorApplication(
            **{name: 'W' * limit for name, limit in FIELD_LIMITS.items()},
            created_at=timezone.now(),
        )
        positions = []
        original_line = AnswerLine.draw
        original_two_lines = TwoLineAnswer.draw

        def record_line(flowable):
            positions.append(flowable.canv.absolutePosition(0, 1))
            original_line(flowable)

        def record_two_lines(flowable):
            for y in range(0, flowable.height, flowable.line_height):
                positions.append(flowable.canv.absolutePosition(0, y))
            original_two_lines(flowable)

        with patch.object(AnswerLine, 'draw', record_line), patch.object(TwoLineAnswer, 'draw', record_two_lines):
            build_application_pdf(io.BytesIO(), [None])
            blank_positions = positions[:]
            positions.clear()
            build_application_pdf(io.BytesIO(), [application])
        self.assertTrue(blank_positions)
        self.assertEqual(len(blank_positions), len(positions))
        for blank, filled in zip(blank_positions, positions):
            self.assertAlmostEqual(blank[0], filled[0], places=5)
            self.assertAlmostEqual(blank[1], filled[1], places=5)


class PhotoPDFTests(TestCase):
    def test_uploaded_photo_is_embedded_and_keeps_one_page(self):
        import re
        from django.utils import timezone
        from registration.pdf import build_application_pdf
        from registration.pdf_layout import FIELD_LIMITS
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            application = CampusAmbassadorApplication(
                **{name: 'W' * limit for name, limit in FIELD_LIMITS.items()},
                created_at=timezone.now(),
            )
            application.picture.save('portrait.png', uploaded_picture(), save=False)
            output = io.BytesIO()
            build_application_pdf(output, [application])
            pdf = output.getvalue()
            self.assertEqual(len(re.findall(rb'/Type\s*/Page\b', pdf)), 1)
            self.assertIn(b'/Width 600', pdf)
            self.assertIn(b'/Height 760', pdf)


class PhotoOptimizationTests(TestCase):
    def picture_errors(self, upload):
        form = CampusAmbassadorApplicationForm(data={}, files={'picture': upload})
        form.is_valid()
        return form

    def test_oversized_photo_is_rejected(self):
        photo = uploaded_picture()
        photo.size = 3 * 1024 * 1024 + 1
        form = self.picture_errors(photo)
        self.assertIn('3 MB', str(form.errors['picture']))

    def test_only_jpeg_png_and_webp_are_allowed(self):
        for fmt in ('GIF', 'BMP'):
            with self.subTest(format=fmt):
                output = io.BytesIO()
                Image.new('RGB', (100, 100), 'red').save(output, fmt)
                form = self.picture_errors(SimpleUploadedFile('photo.' + fmt.lower(), output.getvalue()))
                self.assertIn('JPG, PNG or WebP', str(form.errors['picture']))

    def test_supported_formats_become_small_portrait_jpegs(self):
        for fmt in ('JPEG', 'PNG', 'WEBP'):
            with self.subTest(format=fmt):
                output = io.BytesIO()
                Image.new('RGB', (1600, 900), 'navy').save(output, fmt)
                form = self.picture_errors(SimpleUploadedFile('photo.' + fmt.lower(), output.getvalue()))
                self.assertNotIn('picture', form.errors)
                result = form.cleaned_data['picture']
                self.assertEqual(result.content_type, 'image/jpeg')
                self.assertTrue(result.name.endswith('.jpg'))
                self.assertLess(result.size, 200 * 1024)
                with Image.open(result) as image:
                    self.assertEqual(image.size, (600, 760))
                    self.assertEqual(image.format, 'JPEG')
                    self.assertNotIn('exif', image.info)

    def test_transparency_is_flattened_on_white(self):
        output = io.BytesIO()
        Image.new('RGBA', (600, 760), (0, 0, 0, 0)).save(output, 'PNG')
        form = self.picture_errors(SimpleUploadedFile('transparent.png', output.getvalue()))
        self.assertNotIn('picture', form.errors)
        with Image.open(form.cleaned_data['picture']) as image:
            self.assertEqual(image.getpixel((300, 380)), (255, 255, 255))

    def test_upload_ui_exposes_format_limit_and_crop_controls(self):
        with override_settings(SECURE_SSL_REDIRECT=False):
            response = self.client.get(reverse('registration_form'))
        self.assertContains(response, 'Maximum 3 MB')
        self.assertContains(response, 'image/jpeg,image/png,image/webp')
        self.assertContains(response, 'id="picture-canvas"')
        self.assertContains(response, 'Use this crop')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', SITE_URL='https://biin.example', REGISTRATION_RESPONSE_EMAIL='')
class ConfirmationEmailTests(TestCase):
    def setUp(self):
        self.application = CampusAmbassadorApplication.objects.create(
            full_name='Email <Applicant>', email='applicant@example.com',
            campus_name='Example University', department='Science',
        )

    def test_confirmation_contains_attachment_and_private_download(self):
        from django.core import mail
        from django.test import RequestFactory
        from registration.emails import send_application_confirmation
        import re

        send_application_confirmation(self.application, RequestFactory().get('/'))
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['applicant@example.com'])
        self.assertEqual(message.attachments[0].mimetype, 'application/pdf')
        self.assertTrue(message.attachments[0].content.startswith(b'%PDF'))
        self.assertIn('Email &lt;Applicant&gt;', message.alternatives[0].content)
        url = re.search(r'https://biin.example/\S+', message.body).group()
        response = self.client.get(url.replace('https://biin.example', ''))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b'%PDF'))
        self.assertEqual(response['Cache-Control'], 'private, no-store')

    @override_settings(REGISTRATION_RESPONSE_EMAIL='team@example.com')
    def test_fixed_recipient(self):
        from django.core import mail
        from django.test import RequestFactory
        from registration.emails import send_application_confirmation
        send_application_confirmation(self.application, RequestFactory().get('/'))
        self.assertEqual(mail.outbox[0].to, ['team@example.com'])

    def test_random_links_reject_tampering_and_expiration(self):
        from django.test import RequestFactory
        from registration.emails import application_pdf_url
        request = RequestFactory().get('/')
        url = application_pdf_url(self.application, request).replace('https://biin.example', '')
        self.assertNotEqual(url, application_pdf_url(self.application, request).replace('https://biin.example', ''))
        self.assertEqual(self.client.get(url.replace('/pdf/', '/pdf/tampered')).status_code, 404)
        with override_settings(REGISTRATION_PDF_LINK_MAX_AGE=-1):
            self.assertEqual(self.client.get(url).status_code, 404)


@override_settings(TURNSTILE_REQUIRE=True, TURNSTILE_SITE_KEY='site-key', TURNSTILE_SECRET_KEY='secret-key')
class RegistrationTurnstileTests(TestCase):
    @override_settings(TURNSTILE_REQUIRE=False)
    @patch('registration.views.verify_registration_turnstile')
    def test_disabled_turnstile_skips_verification_and_widget(self, verify):
        response = self.client.get(reverse('registration_form'))
        self.assertNotContains(response, 'challenges.cloudflare.com')
        self.assertNotContains(response, 'cf-turnstile')
        with patch('registration.views.CampusAmbassadorApplicationForm') as form_class:
            form_class.return_value.is_valid.return_value = False
            self.client.post(reverse('registration_form'), {})
            form_class.return_value.add_error.assert_not_called()
        verify.assert_not_called()

    def verify_response(self, payload):
        from unittest.mock import MagicMock
        response = MagicMock()
        response.__enter__.return_value.read.return_value = __import__('json').dumps(payload).encode()
        return response

    @patch('registration.turnstile.urlopen')
    def test_valid_response_requires_expected_action_and_hostname(self, urlopen):
        from registration.turnstile import verify_registration_turnstile
        for payload, expected in [
            ({'success': True, 'action': 'registration', 'hostname': 'testserver'}, True),
            ({'success': False, 'action': 'registration', 'hostname': 'testserver'}, False),
            ({'success': True, 'action': 'login', 'hostname': 'testserver'}, False),
            ({'success': True, 'action': 'registration', 'hostname': 'other.example'}, False),
            ([], False),
        ]:
            with self.subTest(payload=payload):
                urlopen.return_value = self.verify_response(payload)
                self.assertEqual(verify_registration_turnstile('token', 'testserver'), expected)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.method, 'POST')
        self.assertIn(b'secret=secret-key', request.data)
        self.assertEqual(urlopen.call_args.kwargs['timeout'], 10)

    @patch('registration.turnstile.urlopen')
    def test_missing_oversize_tokens_and_missing_keys_are_rejected(self, urlopen):
        from registration.turnstile import verify_registration_turnstile
        self.assertFalse(verify_registration_turnstile('', 'testserver'))
        self.assertFalse(verify_registration_turnstile('x' * 2049, 'testserver'))
        with override_settings(TURNSTILE_SECRET_KEY=''):
            with self.assertLogs('registration.turnstile', level='ERROR'):
                self.assertFalse(verify_registration_turnstile('token', 'testserver'))
        urlopen.assert_not_called()

    @patch('registration.turnstile.urlopen')
    def test_network_failure_and_invalid_json_are_rejected(self, urlopen):
        from registration.turnstile import verify_registration_turnstile
        from urllib.error import URLError
        for error in (URLError('offline'), ValueError('invalid JSON')):
            urlopen.side_effect = error
            with self.assertLogs('registration.turnstile', level='WARNING'):
                self.assertFalse(verify_registration_turnstile('token', 'testserver'))

    @patch('registration.views.send_application_confirmation')
    @patch('registration.views.CampusAmbassadorApplicationForm')
    @patch('registration.views.verify_registration_turnstile', return_value=False)
    def test_failed_verification_never_saves_or_sends(self, verify, form_class, send):
        form = form_class.return_value
        form.is_valid.return_value = True
        response = self.client.post(reverse('registration_form'), {'cf-turnstile-response': 'invalid'})
        self.assertEqual(response.status_code, 200)
        verify.assert_called_once_with('invalid', 'testserver')
        form.save.assert_not_called()
        send.assert_not_called()
        form.add_error.assert_called_once()
        self.assertFalse(CampusAmbassadorApplication.objects.exists())

    def test_form_includes_widget_without_exposing_secret(self):
        response = self.client.get(reverse('registration_form'))
        self.assertContains(response, 'data-sitekey="site-key"')
        self.assertContains(response, 'data-action="registration"')
        self.assertNotContains(response, 'secret-key')
