from django.urls import path
from .views import (
    home,
    login_view,
    register_view,
    logout_view,
    profile_view,
    profile_edit,
)

urlpatterns = [
    path('', home, name='home'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),
    path('profile/edit/', profile_edit, name='profile_edit'),
]