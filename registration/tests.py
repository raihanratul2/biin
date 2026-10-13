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
