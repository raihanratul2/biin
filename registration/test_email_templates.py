from email import policy
from email.parser import BytesParser

from django.core import mail
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from .emails import send_ambassador_selection, send_application_confirmation
from .models import CampusAmbassadorApplication


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   SITE_URL='https://biin.example', BIIN_TERMS_URL='https://biin.example/terms/',
                   REGISTRATION_RESPONSE_EMAIL='override@example.com')
class BrandedEmailTests(TestCase):
    def setUp(self):
        self.application = CampusAmbassadorApplication(
            full_name='Applicant <Example>', email='applicant@example.com',
            campus_name='Science & Technology University', department='ICT', created_at=timezone.now())
        self.application.save()
        self.request = RequestFactory().get('/')

    def test_selection_contains_inline_card_logo_and_shared_footer(self):
        self.assertEqual(send_ambassador_selection(self.application, self.request), 1)
        message = mail.outbox[-1]
        self.assertEqual(message.to, ['applicant@example.com'])
        html = message.alternatives[0].content
        self.assertIn('Congratulations!', html)
        self.assertIn('Applicant &lt;Example&gt;', html)
        self.assertIn('cid:ambassador-card', html)
        self.assertIn('cid:biin-logo', html)
        self.assertIn('https://biin.example/terms/', html)
        self.assertIn('https://biin.example/contact/', html)
        parsed = BytesParser(policy=policy.default).parsebytes(message.message().as_bytes())
        images = {part['Content-ID']: part for part in parsed.walk() if part.get_content_type() == 'image/png'}
        self.assertEqual(set(images), {'<biin-logo>', '<ambassador-card>'})
        for image in images.values():
            self.assertTrue(image.get_payload(decode=True).startswith(b'\x89PNG'))
            self.assertEqual(image.get_content_disposition(), 'inline')

    def test_confirmation_preserves_pdf_and_uses_branded_header(self):
        send_application_confirmation(self.application, self.request)
        message = mail.outbox[-1]
        self.assertEqual(message.to, ['override@example.com'])
        self.assertEqual(message.attachments[0].mimetype, 'application/pdf')
        html = message.alternatives[0].content
        self.assertIn('cid:biin-logo', html)
        self.assertIn('Application received', html)
        self.assertIn('Download application PDF', html)
        self.assertIn('https://biin.example/terms/', html)
