"""Read-only previews, guarded before loading fixtures or rendering assets."""
from functools import wraps

from django.conf import settings
from django.http import Http404


def debug_only(view):
    @wraps(view)
    def guarded(request, *args, **kwargs):
        if not settings.DEBUG:
            raise Http404
        response = view(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store'
        response['X-Robots-Tag'] = 'noindex, nofollow'
        return response
    return guarded


def preview_context(request):
    from django.urls import reverse
    from registration.card_sharing import card_share_links
    from registration.emails import email_context
    from .email_samples import sample_application

    application = sample_application()
    context = email_context(request, title='Application received', preheader='Development email preview.')
    context.update(card_share_links(
        request.build_absolute_uri(reverse('development:card_share')),
        request.build_absolute_uri(reverse('development:card_image')),
        application.campus_name,
    ))
    context.update({
        'application': application,
        'ambassador_name': application.full_name,
        'campus_name': application.campus_name,
        'pdf_url': request.build_absolute_uri(reverse('development:application_pdf')),
        'link_hours': settings.REGISTRATION_PDF_LINK_MAX_AGE / 3600,
        'test_email': request.GET.get('test') == '1',
    })
    return context


@debug_only
def email_index(request):
    from django.shortcuts import render

    return render(request, 'development/email_index.html')


@debug_only
def email_preview(request, kind):
    from base64 import b64encode
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    from registration.emails import SOCIAL_ICONS, email_static_file

    context = preview_context(request)
    template = 'application_confirmation' if kind == 'confirmation' else 'ambassador_selection'
    if kind == 'selection':
        context['email_title'] = "You're selected!"
    if request.GET.get('format') == 'txt':
        return HttpResponse(render_to_string(f'emails/{template}.txt', context), content_type='text/plain; charset=utf-8')
    html = render_to_string(f'emails/{template}.html', context)
    # Browsers cannot resolve MIME Content-ID URLs used by actual email clients.
    assets = {'biin-logo': 'BIIN_Logo.png', **{f'social-{icon}': f'social/{icon}.png' for icon in SOCIAL_ICONS}}
    for cid, asset in assets.items():
        if f'cid:{cid}' in html:
            data = b64encode(email_static_file(asset).read_bytes()).decode('ascii')
            html = html.replace(f'cid:{cid}', f'data:image/png;base64,{data}')
    html = html.replace('cid:ambassador-card', context['card_image_url'])
    return HttpResponse(html)


@debug_only
def card_preview(request):
    from django.shortcuts import render

    return render(request, 'ambassador_card_share.html', preview_context(request))


@debug_only
def card_image(request):
    from django.http import HttpResponse
    from registration.cards import build_ambassador_card_png
    from .email_samples import sample_application

    response = HttpResponse(build_ambassador_card_png(sample_application()), content_type='image/png')
    disposition = 'attachment' if request.GET.get('download') == '1' else 'inline'
    response['Content-Disposition'] = f'{disposition}; filename="biin_demo_card.png"'
    return response


@debug_only
def application_pdf(request):
    from django.http import HttpResponse
    from registration.pdf import build_application_pdf
    from .email_samples import sample_application

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="biin_demo_application.pdf"'
    build_application_pdf(response, [sample_application()])
    return response
