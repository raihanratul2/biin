from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.conf import settings
from django.core import signing
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_http_methods
import logging

from .emails import send_application_confirmation
from .turnstile import verify_registration_turnstile

from .forms import CampusAmbassadorApplicationForm, CardPhotoPositionForm
from .card_layout import application_photo_position
from .models import CampusAmbassadorApplication, RegistrationSetting


def is_staff_user(user):
    return user.is_authenticated and user.is_staff


def registration_form(request):
    setting, _ = RegistrationSetting.objects.get_or_create(pk=1)

    if not setting.registration_open:
        return render(request, 'registration_closed.html', {'registration_open': setting.registration_open})

    if request.method == 'POST':
        form = CampusAmbassadorApplicationForm(request.POST, request.FILES)
        form_valid = form.is_valid()
        verified = not settings.TURNSTILE_REQUIRE or verify_registration_turnstile(
            request.POST.get('cf-turnstile-response', ''),
            request.get_host().split(':')[0],
        )
        if not verified:
            form.add_error(None, 'Security verification failed or expired. Please complete the verification and try again.')
        if form_valid and verified:
            application = form.save()
            try:
                send_application_confirmation(application, request)
            except Exception:
                logging.getLogger(__name__).exception('Confirmation email failed for application %s', application.pk)
                messages.warning(request, 'Your application was saved, but the confirmation email could not be sent. Please contact BIIN for a copy.')
            return redirect('registration_success')
    else:
        form = CampusAmbassadorApplicationForm()

    return render(request, 'registration_form.html', {
        'form': form, 'registration_open': setting.registration_open,
        'turnstile_site_key': settings.TURNSTILE_SITE_KEY,
        'turnstile_required': settings.TURNSTILE_REQUIRE,
    })


def registration_success(request):
    return render(request, 'registration_success.html')


def application_pdf_download(request, token):
    from .pdf import build_application_pdf

    try:
        payload = signing.loads(token, salt='registration.pdf', max_age=settings.REGISTRATION_PDF_LINK_MAX_AGE)
    except signing.BadSignature:
        raise Http404('This download link is invalid or has expired.')
    application = get_object_or_404(CampusAmbassadorApplication, pk=payload['application_id'])
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="biin_application.pdf"'
    response['Cache-Control'] = 'private, no-store'
    response['Referrer-Policy'] = 'no-referrer'
    response['X-Robots-Tag'] = 'noindex, nofollow'
    build_application_pdf(response, [application])
    return response


@login_required(login_url='login')
@user_passes_test(is_staff_user, login_url='login')
def applications(request):
    applicants = CampusAmbassadorApplication.objects.all()
    setting, _ = RegistrationSetting.objects.get_or_create(pk=1)
    return render(request, 'registration_list.html', {'applicants': applicants, 'registration_open': setting.registration_open})


@login_required(login_url='login')
@user_passes_test(is_staff_user, login_url='login')
@require_http_methods(['GET', 'POST'])
def ambassador_card(request, pk):
    from .cards import build_ambassador_card

    application = get_object_or_404(CampusAmbassadorApplication, pk=pk)
    if request.method == 'POST':
        form = CardPhotoPositionForm(request.POST, instance=application)
        if not form.is_valid():
            response = JsonResponse({'errors': form.errors}, status=400)
        else:
            # Update only the card position, preserving other application edits.
            application.save(update_fields=CardPhotoPositionForm.Meta.fields)
            response = JsonResponse({'saved': True, 'position': application_photo_position(application)})
    else:
        response = render(request, 'ambassador_card.html', {
            'application': application,
            'card_svg': mark_safe(build_ambassador_card(application, inline=True).decode('utf-8')),
            'card_position': application_photo_position(application),
        })
    response['Cache-Control'] = 'private, no-store'
    return response


@login_required(login_url='login')
@user_passes_test(is_staff_user, login_url='login')
def ambassador_card_download(request, pk):
    from .cards import build_ambassador_card_png

    application = get_object_or_404(CampusAmbassadorApplication, pk=pk)
    response = HttpResponse(build_ambassador_card_png(application), content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="biin_ambassador_{application.pk}.png"'
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


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
    from .pdf import build_application_pdf

    if request.GET.get('blank') == '1':
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="biin_blank_application.pdf"'
        response['Cache-Control'] = 'private, no-store'
        build_application_pdf(response, [None])
        return response

    applications = CampusAmbassadorApplication.objects.all()
    if 'ids' in request.GET:
        raw_ids = request.GET.getlist('ids')
        if not raw_ids or any(not value.isdecimal() or len(value) > 18 for value in raw_ids):
            return HttpResponse('Select valid submissions.', status=400)
        ids = {int(value) for value in raw_ids}
        applications = applications.filter(pk__in=ids)
        if applications.count() != len(ids):
            return HttpResponse('One or more submissions were not found.', status=404)
    if not applications.exists():
        return HttpResponse('No submissions available to export.', status=400)

    response = HttpResponse(content_type='application/pdf')
    disposition = 'inline' if request.GET.get('print') == '1' else 'attachment'
    response['Content-Disposition'] = f'{disposition}; filename="campus_ambassadors.pdf"'
    response['Cache-Control'] = 'private, no-store'
    build_application_pdf(response, applications)
    return response
