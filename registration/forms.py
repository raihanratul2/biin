from django import forms

from .models import CampusAmbassadorApplication


class CampusAmbassadorApplicationForm(forms.ModelForm):
    required_css_class = 'required'

    declaration_accuracy = forms.BooleanField(required=True)
    declaration_terms = forms.BooleanField(required=True)

    skills = forms.MultipleChoiceField(
        choices=CampusAmbassadorApplication.SKILL_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = CampusAmbassadorApplication
        fields = [
            'full_name',
            'email',
            'phone_number',
            'address',
            'campus_name',
            'department',
            'student_id',
            'academic_year',
            'facebook_link',
            'linkedin_link',
            'website',
            'has_previous_campus_ambassador',
            'previous_experience_details',
            'skills',
            'has_organized_campus_events',
            'motivation',
            'promotion_plan',
            'weekly_hours',
            'has_active_student_network',
            'activities_to_organize',
            'declaration_accuracy',
            'declaration_terms',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Enter your full name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'example@email.com'}),
            'phone_number': forms.TextInput(attrs={'placeholder': '+8801XXXXXXXXX'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Your current address'}),
            'campus_name': forms.TextInput(attrs={'placeholder': 'Campus or university name'}),
            'department': forms.TextInput(attrs={'placeholder': 'Department / subject'}),
            'student_id': forms.TextInput(attrs={'placeholder': 'Student ID / registration number'}),
            'academic_year': forms.TextInput(attrs={'placeholder': 'e.g. 3rd Year or 6th Semester'}),
            'facebook_link': forms.URLInput(attrs={'placeholder': 'https://facebook.com/yourprofile'}),
            'linkedin_link': forms.URLInput(attrs={'placeholder': 'https://linkedin.com/in/yourprofile'}),
            'website': forms.URLInput(attrs={'placeholder': 'https://yourportfolio.com'}),
            'has_previous_campus_ambassador': forms.Select(choices=CampusAmbassadorApplication.YES_NO_CHOICES),
            'previous_experience_details': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Tell us about your previous campus ambassador or leadership experience'}),
            'has_organized_campus_events': forms.Select(choices=CampusAmbassadorApplication.YES_NO_CHOICES),
            'motivation': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Why do you want to become a BIIN Campus Ambassador?'}),
            'promotion_plan': forms.Textarea(attrs={'rows': 5, 'placeholder': 'How would you promote BIIN on your campus?'}),
            'weekly_hours': forms.TextInput(attrs={'placeholder': 'e.g. 5-10 hours per week'}),
            'has_active_student_network': forms.Select(choices=CampusAmbassadorApplication.YES_NO_CHOICES),
            'activities_to_organize': forms.Textarea(attrs={'rows': 4, 'placeholder': 'What activities would you like to organize for BIIN?'}),
            'declaration_accuracy': forms.CheckboxInput(),
            'declaration_terms': forms.CheckboxInput(),
        }

    def clean_skills(self):
        skills = self.cleaned_data.get('skills')
        if skills:
            return ', '.join(skills)
        return ''
