from django.db import models


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

    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    campus_name = models.CharField(max_length=200)
    department = models.CharField(max_length=200)
    student_id = models.CharField(max_length=100)
    academic_year = models.CharField(max_length=50)
    facebook_link = models.URLField(blank=True, default='')
    linkedin_link = models.URLField(blank=True, default='')
    website = models.URLField(blank=True, default='')

    has_previous_campus_ambassador = models.CharField(max_length=3, choices=YES_NO_CHOICES, default='No')
    previous_experience_details = models.TextField(blank=True)
    skills = models.CharField(max_length=255, blank=True)
    has_organized_campus_events = models.CharField(max_length=3, choices=YES_NO_CHOICES, default='No')

    motivation = models.TextField(blank=True, default='')
    promotion_plan = models.TextField(blank=True, default='')
    weekly_hours = models.CharField(max_length=50, blank=True)
    has_active_student_network = models.CharField(max_length=3, choices=YES_NO_CHOICES, default='No')
    activities_to_organize = models.TextField(blank=True)

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
