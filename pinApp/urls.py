from django.urls import path
from django.contrib.auth import views as auth_views
from .views import home_view, register_view

urlpatterns = [
    path('', home_view, name='home'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('register/', register_view, name='register'),
]
