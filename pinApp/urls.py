from django.urls import path
from .views import (home_view, 
                    login_view, 
                    register_view, 
                    logout_view, 
                    dashboard_view, 
                    edit_profile_view, 
                    create_board_view, 
                    edit_board_view, 
                    delete_board_view, 
                    delete_pin_view)

urlpatterns = [
    path('', home_view, name='home'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('profile/edit/', edit_profile_view, name='edit_profile'),
    path('board/create/', create_board_view, name='create_board'),
    path('board/<int:bid>/', edit_board_view, name='edit_board'),
    path('board/<int:bid>/delete/', delete_board_view, name='delete_board'),
    path('pin/<int:pinid>/delete/', delete_pin_view, name='delete_pin'),
]
