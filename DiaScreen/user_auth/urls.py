from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from .views import (
    home,
    login_view,
    privacy_policy,
    register_view,
    logout_view,
    profile_view,
    profile_edit,
)
from .forms import StyledPasswordResetForm, StyledSetPasswordForm

urlpatterns = [
    path('', home, name='home'),
    path('login/', login_view, name='login'),
    path('privacy-policy/', privacy_policy, name='privacy_policy'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),
    path('profile/edit/', profile_edit, name='profile_edit'),
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            form_class=StyledPasswordResetForm,
            template_name='auth/password_reset_form.html',
            email_template_name='auth/password_reset_email.html',
            subject_template_name='auth/password_reset_subject.txt',
            success_url=reverse_lazy('password_reset_done'),
        ),
        name='password_reset',
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='auth/password_reset_done.html'
        ),
        name='password_reset_done',
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            form_class=StyledSetPasswordForm,
            template_name='auth/password_reset_confirm.html',
            success_url=reverse_lazy('password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='auth/password_reset_complete.html'
        ),
        name='password_reset_complete',
    ),
]