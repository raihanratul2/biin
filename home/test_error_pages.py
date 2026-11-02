from django.test import SimpleTestCase, override_settings
from django.urls import reverse


@override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['testserver'])
class NotFoundPageTests(SimpleTestCase):
    def test_unknown_url_uses_branded_page_with_404_status(self):
        response = self.client.get('/this-page-does-not-exist/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')
        self.assertContains(response, 'Page not found', status_code=404)
        self.assertContains(response, 'Back to Home', status_code=404)
        self.assertContains(response, f'href="{reverse("contact")}"', status_code=404)
        self.assertContains(response, 'SoftsyncBD', status_code=404)

    def test_view_raised_404_also_uses_the_custom_page(self):
        response = self.client.get(reverse('ambassador_card_image', args=['invalid-token']))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')
