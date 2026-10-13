from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render

from .forms import CampusAmbassadorApplicationForm
from .models import CampusAmbassadorApplication, RegistrationSetting


def is_staff_user(user):
    return user.is_authenticated and user.is_staff


def registration_form(request):
    setting, _ = RegistrationSetting.objects.get_or_create(pk=1)

    if not setting.registration_open:
        return render(request, 'registration_closed.html', {'registration_open': setting.registration_open})

    if request.method == 'POST':
        form = CampusAmbassadorApplicationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('registration_success')
    else:
        form = CampusAmbassadorApplicationForm()

    return render(request, 'registration_form.html', {'form': form, 'registration_open': setting.registration_open})


def registration_success(request):
    return render(request, 'registration_success.html')


@login_required(login_url='login')
@user_passes_test(is_staff_user, login_url='login')
def applications(request):
    applicants = CampusAmbassadorApplication.objects.all()
    setting, _ = RegistrationSetting.objects.get_or_create(pk=1)
    return render(request, 'registration_list.html', {'applicants': applicants, 'registration_open': setting.registration_open})


@login_required(login_url='login')
@user_passes_test(is_staff_user, login_url='login')
def registration_settings(request):
    setting, _ = RegistrationSetting.objects.get_or_create(pk=1)
    if request.method == 'POST':
        setting.registration_open = request.POST.get('registration_open') == 'on'
        setting.save()
        messages.success(request, 'Registration status updated successfully.')
    return render(request, 'registration_settings.html', {'registration_open': setting.registration_open})


@login_required(login_url='login')
@user_passes_test(is_staff_user, login_url='login')
def export_excel(request):
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Campus Ambassadors'
    headers = [
        'Name', 'Email', 'Phone', 'Address', 'Campus', 'Department',
        'Student ID', 'Academic Year', 'Facebook', 'LinkedIn', 'Website',
        'Worked Before', 'Previous Experience', 'Skills', 'Organized Events',
        'Motivation', 'Promotion Plan', 'Weekly Hours', 'Active Network',
        'Activities', 'Information Accurate', 'Terms Accepted'
    ]
    sheet.append(headers)

    for application in CampusAmbassadorApplication.objects.all():
        sheet.append([
            application.full_name,
            application.email,
            application.phone_number,
            application.address,
            application.campus_name,
            application.department,
            application.student_id,
            application.academic_year,
            application.facebook_link,
            application.linkedin_link,
            application.website,
            application.has_previous_campus_ambassador,
            application.previous_experience_details,
            application.skills,
            application.has_organized_campus_events,
            application.motivation,
            application.promotion_plan,
            application.weekly_hours,
            application.has_active_student_network,
            application.activities_to_organize,
            'Yes' if application.declaration_accuracy else 'No',
            'Yes' if application.declaration_terms else 'No',
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="campus_ambassadors.xlsx"'
    workbook.save(response)
    return response


@login_required(login_url='login')
@user_passes_test(is_staff_user, login_url='login')
def export_pdf(request):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="campus_ambassadors.pdf"'

    applications = CampusAmbassadorApplication.objects.all()
    styles = getSampleStyleSheet()
    story = [
        Paragraph('BIIN Campus Ambassador Applications', styles['Title']),
        Spacer(1, 18),
    ]

    data = [[
        'Name', 'Email', 'Campus', 'Department', 'Phone', 'Academic Year'
    ]]
    for application in applications:
        data.append([
            application.full_name,
            application.email,
            application.campus_name,
            application.department,
            application.phone_number,
            application.academic_year,
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d4f9a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    story.append(table)

    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    doc.build(story)
    return response
