from django import forms

from .models import CampusAmbassadorApplication
from .photos import ApplicationPhotoField, optimize_photo
from .card_layout import constrain_photo_position


class CardPhotoPositionForm(forms.ModelForm):
    class Meta:
        model = CampusAmbassadorApplication
        fields = ['card_photo_x', 'card_photo_y', 'card_photo_scale']

    def clean(self):
        data = super().clean()
        if all(field in data for field in self.Meta.fields):
            position = {key: data[f'card_photo_{key}'] for key in ('x', 'y', 'scale')}
            if constrain_photo_position(**position) != position:
                raise forms.ValidationError('Keep the photo within the frame so no empty space is exposed.')
        return data


class CampusAmbassadorApplicationForm(forms.ModelForm):
    required_css_class = 'required'

    picture = ApplicationPhotoField(
        label='Passport photograph',
        widget=forms.FileInput(attrs={
            'accept': '.jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp',
            'aria-describedby': 'picture-help picture-status',
        }),
    )

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
            'picture',
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .pdf_layout import FIELD_LIMITS
        for name, limit in FIELD_LIMITS.items():
            self.fields[name].widget.attrs['maxlength'] = limit
            self.fields[name].help_text = f'Maximum {limit} characters.'

    def clean_picture(self):
        return optimize_photo(self.cleaned_data['picture'])

    def clean_skills(self):
        skills = self.cleaned_data.get('skills')
        if skills:
            return ', '.join(skills)
        return ''
