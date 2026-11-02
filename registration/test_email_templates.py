from email import policy
from email.parser import BytesParser
from io import BytesIO
from urllib.parse import parse_qs, urlsplit

from django.core import mail
from django.core import signing
from django.conf import settings
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from PIL import Image

from .card_sharing import CARD_SHARE_SALT, ambassador_card_links
from .emails import SOCIAL_ICONS, email_context, send_ambassador_selection, send_application_confirmation
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
        self.assertIn('http://testserver/terms/', html)
        self.assertIn('http://testserver/contact/', html)
        parsed = BytesParser(policy=policy.default).parsebytes(message.message().as_bytes())
        images = {part['Content-ID']: part for part in parsed.walk()
                  if part.get_content_type() == 'image/png' and part['Content-ID']}
        self.assertEqual(set(images), {'<biin-logo>', '<ambassador-card>',
                                       *{f'<social-{icon}>' for icon in SOCIAL_ICONS}})
        for image in images.values():
            self.assertTrue(image.get_payload(decode=True).startswith(b'\x89PNG'))
            self.assertEqual(image.get_content_disposition(), 'inline')
        attachments = list(parsed.iter_attachments())
        card = next(part for part in attachments if part.get_filename() == 'biin_ambassador_card.png')
        self.assertEqual(card.get_content_disposition(), 'attachment')
        with Image.open(BytesIO(card.get_payload(decode=True))) as image:
            self.assertEqual(image.size, (1080, 1080))
        with Image.open(BytesIO(images['<ambassador-card>'].get_payload(decode=True))) as image:
            self.assertEqual(image.size, (440, 440))
        for label in ['Download card', 'Facebook', 'WhatsApp', 'Instagram', 'X', 'LinkedIn', 'Download photo']:
            self.assertIn(f'>{label}</a>', html)
        self.assertIn('Download card / photo:', message.body)
        self.assertIn('background:#636BB0;color:#ffffff', html)
        self.assertIn('>Maps</a>', html)
        self.assertIn('>' + escape(settings.BIIN_OFFICE_ADDRESS) + ' &nbsp;<a href=', html)
        self.assertIn('This is an automated email. You do not need to reply to this email.', html)
        self.assertIn('href="https://softsync.bd"', html)
        self.assertIn('>SoftsyncBD</a>', html)

    def test_sample_selection_attaches_card_without_live_share_links(self):
        self.application.pk = None
        send_ambassador_selection(self.application, self.request, test_email=True)
        message = mail.outbox[-1]
        self.assertTrue(message.subject.startswith('[TEST]'))
        self.assertIn('biin_ambassador_card.png', message.alternatives[0].content)
        self.assertNotIn('/registration/card/', message.alternatives[0].content)

    def test_confirmation_preserves_pdf_and_uses_branded_header(self):
        send_application_confirmation(self.application, self.request)
        message = mail.outbox[-1]
        self.assertEqual(message.to, ['override@example.com'])
        self.assertEqual(message.attachments[0].mimetype, 'application/pdf')
        html = message.alternatives[0].content
        self.assertIn('cid:biin-logo', html)
        self.assertIn('Application received', html)
        self.assertIn('Download application PDF', html)
        self.assertIn('http://testserver/terms/', html)

    def test_links_use_request_host_instead_of_configured_site_domain(self):
        with override_settings(ALLOWED_HOSTS=['preview.local']):
            request = RequestFactory().get('/', secure=True, HTTP_HOST='preview.local:8443')
            context = email_context(request, title='Preview', preheader='Preview')
            for key in ['site_url', 'about_url', 'contact_url', 'terms_url']:
                self.assertTrue(context[key].startswith('https://preview.local:8443'))
            send_application_confirmation(self.application, request)
            self.assertIn('https://preview.local:8443/registration/pdf/', mail.outbox[-1].body)
            links = ambassador_card_links(self.application, request)
            self.assertTrue(links['card_download_url'].startswith('https://preview.local:8443/'))


@override_settings(SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['testserver'], SITE_URL='https://biin.example')
class AmbassadorCardSharingTests(TestCase):
    def setUp(self):
        self.application = CampusAmbassadorApplication.objects.create(
            full_name='Selected <Ambassador>', campus_name='Science & Technology Campus',
            email='private@example.com', phone_number='01712345678', student_id='PRIVATE-ID')
        self.links = ambassador_card_links(self.application, RequestFactory().get('/'))
        self.share_path = urlsplit(self.links['card_share_url']).path
        self.image_path = urlsplit(self.links['card_image_url']).path

    def test_public_share_page_has_card_metadata_but_no_private_application_details(self):
        response = self.client.get(self.share_path)
        self.assertContains(response, 'Selected &lt;Ambassador&gt;')
        self.assertContains(response, 'property="og:image" content="' + self.links['card_image_url'] + '"')
        for private_value in [self.application.email, self.application.phone_number, self.application.student_id]:
            self.assertNotContains(response, private_value)
        self.assertContains(response, 'developer/favicon.png')
        self.assertContains(response, 'SoftsyncBD')
        self.assertEqual(response['Referrer-Policy'], 'no-referrer')
        self.assertEqual(response['X-Robots-Tag'], 'noindex, nofollow')

    def test_public_image_and_download_work_without_staff_login(self):
        for suffix, disposition in [('', 'inline'), ('?download=1', 'attachment')]:
            response = self.client.get(self.image_path + suffix)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'image/png')
            self.assertTrue(response['Content-Disposition'].startswith(disposition + ';'))
            self.assertEqual(response['Cache-Control'], 'private, no-store')
            with Image.open(BytesIO(response.content)) as image:
                self.assertEqual(image.size, (1080, 1080))

    def test_invalid_tokens_cannot_access_a_card_or_application_pdf(self):
        for route in ['ambassador_card_share', 'ambassador_card_image', 'application_pdf_download']:
            token = self.share_path.rstrip('/').rsplit('/', 1)[-1]
            if route != 'application_pdf_download':
                token += 'tampered'
            self.assertEqual(self.client.get(reverse(route, args=[token])).status_code, 404)
        for payload in [{}, {'application_id': None}, {'application_id': 'invalid'}, {'application_id': 999999}]:
            token = signing.dumps(payload, salt=CARD_SHARE_SALT)
            self.assertEqual(self.client.get(reverse('ambassador_card_share', args=[token])).status_code, 404)

    def test_social_urls_preserve_the_complete_signed_link(self):
        facebook = parse_qs(urlsplit(self.links['facebook_share_url']).query)
        whatsapp = parse_qs(urlsplit(self.links['whatsapp_share_url']).query)
        x = parse_qs(urlsplit(self.links['x_share_url']).query)
        self.assertEqual(facebook['u'], [self.links['card_share_url']])
        self.assertIn(self.links['card_share_url'], whatsapp['text'][0])
        self.assertIn(self.application.campus_name, whatsapp['text'][0])
        self.assertEqual(x['url'], [self.links['card_share_url']])
        linkedin = parse_qs(urlsplit(self.links['linkedin_share_url']).query)
        self.assertEqual(linkedin['url'], [self.links['card_share_url']])
