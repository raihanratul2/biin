from django.db import models
from django.core.validators import MaxLengthValidator

from .pdf_layout import FIELD_LIMITS


class CampusAmbassadorApplication(models.Model):
    YES_NO_CHOICES = [
        ('Yes', 'Yes'),
        ('No', 'No'),
    ]

    SKILL_CHOICES = [
        ('Communication', 'Communication'),
        ('Leadership', 'Leadership'),
        ('Marketing', 'Marketing'),
        ('Content Creation', 'Content Creation'),
        ('Event Management', 'Event Management'),
    ]

    picture = models.ImageField(upload_to='applications/photos/', default='')
    full_name = models.CharField(max_length=FIELD_LIMITS['full_name'])
    email = models.EmailField(max_length=FIELD_LIMITS['email'], unique=True)
    phone_number = models.CharField(max_length=FIELD_LIMITS['phone_number'])
    address = models.CharField(max_length=FIELD_LIMITS['address'], blank=True)
    campus_name = models.CharField(max_length=FIELD_LIMITS['campus_name'])
    department = models.CharField(max_length=FIELD_LIMITS['department'])
    student_id = models.CharField(max_length=FIELD_LIMITS['student_id'])
    academic_year = models.CharField(max_length=FIELD_LIMITS['academic_year'])
    facebook_link = models.URLField(max_length=FIELD_LIMITS['facebook_link'], blank=True, default='')
    linkedin_link = models.URLField(max_length=FIELD_LIMITS['linkedin_link'], blank=True, default='')
    website = models.URLField(max_length=FIELD_LIMITS['website'], blank=True, default='')

    has_previous_campus_ambassador = models.CharField(max_length=3, choices=YES_NO_CHOICES, default='No')
    previous_experience_details = models.TextField(max_length=FIELD_LIMITS['previous_experience_details'], validators=[MaxLengthValidator(FIELD_LIMITS['previous_experience_details'])], blank=True)
    skills = models.CharField(max_length=255, blank=True)
    has_organized_campus_events = models.CharField(max_length=3, choices=YES_NO_CHOICES, default='No')

    motivation = models.TextField(max_length=FIELD_LIMITS['motivation'], validators=[MaxLengthValidator(FIELD_LIMITS['motivation'])], blank=True, default='')
    promotion_plan = models.TextField(max_length=FIELD_LIMITS['promotion_plan'], validators=[MaxLengthValidator(FIELD_LIMITS['promotion_plan'])], blank=True, default='')
    weekly_hours = models.CharField(max_length=FIELD_LIMITS['weekly_hours'], blank=True)
    has_active_student_network = models.CharField(max_length=3, choices=YES_NO_CHOICES, default='No')
    activities_to_organize = models.TextField(max_length=FIELD_LIMITS['activities_to_organize'], validators=[MaxLengthValidator(FIELD_LIMITS['activities_to_organize'])], blank=True)

    declaration_accuracy = models.BooleanField(default=False)
    declaration_terms = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.full_name


class RegistrationSetting(models.Model):
    registration_open = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return 'Registration Open' if self.registration_open else 'Registration Closed'
