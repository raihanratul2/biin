"""Synthetic email preview data. Never reads or writes application records."""
from django.utils import timezone

from registration.models import CampusAmbassadorApplication


def sample_application(*, email='preview@example.com'):
    return CampusAmbassadorApplication(
        full_name='BIIN Demo Ambassador', email=email,
        campus_name='Science & Technology University', department='Computer Science',
        student_id='DEMO-001', academic_year='3rd Year', created_at=timezone.now(),
        motivation='Sample application for development previews.',
    )
