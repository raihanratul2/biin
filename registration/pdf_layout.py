"""Fixed A4 field geometry and character limits at the PDF's 8.5pt font.

Personal-information limits use typical name, contact and address text widths.
Wider text is shrunk only inside its own field. Whitespace is collapsed for PDF rendering.
"""
FIELD_LIMITS = {
    'full_name': 50, 'email': 60, 'phone_number': 13, 'address': 60,
    'campus_name': 60, 'department': 30, 'student_id': 30,
    'academic_year': 30, 'weekly_hours': 30,
    'facebook_link': 30, 'linkedin_link': 30, 'website': 60,
    'previous_experience_details': 120,
    'motivation': 240, 'promotion_plan': 240, 'activities_to_organize': 240,
}
LONG_FIELDS = {'motivation', 'promotion_plan', 'activities_to_organize'}


def field_height(key):
    if key in {'previous_experience_details', 'skills'}:
        return 60
    return 54 if key in LONG_FIELDS else 30
