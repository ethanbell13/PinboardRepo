from django.urls import path
#from django.contrib.auth import views as auth_views
from .views import home_view, login_view, register_view, logout_view, dashboard_view, create_board_view

urlpatterns = [
    path('', home_view, name='home'),
    #path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('board/create/', create_board_view, name='create_board'),
]
