from django.urls import path

from . import views

urlpatterns = [
    path('register/', views.registration_form, name='registration_form'),
    path('success/', views.registration_success, name='registration_success'),
    path('settings/', views.registration_settings, name='registration_settings'),
    path('applications/', views.applications, name='applications'),
    path('export/excel/', views.export_excel, name='export_excel'),
    path('export/pdf/', views.export_pdf, name='export_pdf'),
]
