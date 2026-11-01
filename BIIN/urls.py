from django.contrib import admin
from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='login.html', redirect_authenticated_user=True, next_page='applications'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('', include('home.urls')),
    path('registration/', include('registration.urls')),
]

if settings.DJANGO_ADMIN_ENABLED:
    urlpatterns.insert(0, path('admin/', admin.site.urls))
