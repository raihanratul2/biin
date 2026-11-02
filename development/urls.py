from django.conf import settings
from django.urls import path

app_name = 'development'
urlpatterns = []

if settings.DEBUG:
    from . import views

    urlpatterns = [
        path('emails/', views.email_index, name='email_index'),
        path('emails/application-confirmation/', views.email_preview, {'kind': 'confirmation'}, name='confirmation'),
        path('emails/ambassador-selection/', views.email_preview, {'kind': 'selection'}, name='selection'),
        path('emails/card/', views.card_preview, name='card_share'),
        path('emails/card.png', views.card_image, name='card_image'),
        path('emails/application.pdf', views.application_pdf, name='application_pdf'),
    ]
