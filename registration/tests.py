from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from registration.models import CampusAmbassadorApplication, RegistrationSetting
from registration.forms import CampusAmbassadorApplicationForm


class CampusAmbassadorFlowTests(TestCase):
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

    def test_registration_submission_creates_record_and_redirects_to_success(self):
        payload = {
            'full_name': 'Ayesha Rahman',
            'email': 'ayesha@example.com',
            'phone_number': '+8801700000000',
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
        self.assertTrue(CampusAmbassadorApplication.objects.filter(email='ayesha@example.com').exists())


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
