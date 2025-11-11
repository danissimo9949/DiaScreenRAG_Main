from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from support.models import SupportTicket
from card.models import (
    GlucoseMeasurement,
    InsulineDoseMeasurement,
    GlycemicProfileMeasurement,
)

from .forms import LoginForm, UserRegistrationForm, PatientProfileForm, GlucoseTargetForm
from .models import Patient


def home(request):
    patient_count = Patient.objects.count()
    total_entries = (
        GlucoseMeasurement.objects.count()
        + InsulineDoseMeasurement.objects.count()
        + GlycemicProfileMeasurement.objects.count()
    )

    latest_glucose = None
    latest_insuline = None
    daily_status = None
    patient_profile = None
    target_min_value = 4.0
    target_max_value = 9.0
    profile_completion_warning = None

    if request.user.is_authenticated:
        patient_profile = getattr(request.user, 'profile', None)
        if patient_profile:
            if patient_profile.target_glucose_min is not None:
                target_min_value = float(patient_profile.target_glucose_min)
            if patient_profile.target_glucose_max is not None:
                target_max_value = float(patient_profile.target_glucose_max)

            latest_glucose = (
                GlucoseMeasurement.objects.filter(patient=patient_profile)
                .order_by('-date_of_measurement', '-time_of_measurement')
                .first()
            )
            latest_insuline = (
                InsulineDoseMeasurement.objects.filter(patient=patient_profile)
                .order_by('-date_of_measurement', '-time')
                .first()
            )
            latest_glycemic = (
                GlycemicProfileMeasurement.objects.filter(patient=patient_profile)
                .order_by('-measurement_date', '-measurement_time')
                .first()
            )

            if latest_glucose:
                glucose_value = float(latest_glucose.glucose)
                target_min = target_min_value
                target_max = target_max_value

                status_class = 'bg-primary-subtle text-primary'
                if target_min <= glucose_value <= target_max:
                    daily_status = {
                        'type': 'success',
                        'message': 'Сьогодні рівень глюкози в межах цілі.',
                        'css_class': 'bg-success-subtle text-success',
                    }
                elif glucose_value < target_min:
                    daily_status = {
                        'type': 'warning',
                        'message': 'Сьогодні рівень глюкози нижчий за ціль. Будьте уважні.',
                        'css_class': 'bg-warning-subtle text-warning',
                    }
                else:
                    daily_status = {
                        'type': 'danger',
                        'message': 'Сьогодні рівень глюкози перевищує ціль. Перевірте свої показники.',
                        'css_class': 'bg-danger-subtle text-danger',
                    }
            elif latest_glycemic:
                avg_glucose = float(latest_glycemic.average_glucose)
                if target_min_value <= avg_glucose <= target_max_value:
                    daily_status = {
                        'type': 'success',
                        'message': 'Середня глюкоза за останній профіль у межах цілі.',
                        'css_class': 'bg-success-subtle text-success',
                    }
                elif avg_glucose < target_min_value:
                    daily_status = {
                        'type': 'warning',
                        'message': 'Середня глюкоза за останній профіль нижча за норму.',
                        'css_class': 'bg-warning-subtle text-warning',
                    }
                else:
                    daily_status = {
                        'type': 'danger',
                        'message': 'Середня глюкоза за останній профіль перевищує норму.',
                        'css_class': 'bg-danger-subtle text-danger',
                    }

        if patient_profile:
            missing_fields = []
            if not patient_profile.date_of_birth:
                missing_fields.append('дата народження')
            if not patient_profile.sex:
                missing_fields.append('стать')
            if patient_profile.height is None:
                missing_fields.append('зріст')
            if patient_profile.weight is None:
                missing_fields.append('вага')
            if not patient_profile.diabetes_type:
                missing_fields.append('тип діабету')
            if missing_fields:
                profile_completion_warning = (
                    f"Заповніть профіль: {', '.join(missing_fields)}. "
                    "Це допоможе отримувати точніші рекомендації."
                )
        else:
            profile_completion_warning = (
                "Створіть профіль пацієнта, щоб система могла персоналізувати рекомендації."
            )

    context = {
        'patient_count': patient_count,
        'total_entries': total_entries,
        'latest_glucose': latest_glucose,
        'latest_insuline': latest_insuline,
        'patient_profile': patient_profile,
        'daily_status': daily_status,
        'target_glucose_min': target_min_value,
        'target_glucose_max': target_max_value,
        'profile_completion_warning': profile_completion_warning,
    }

    return render(request, 'auth/home.html', context)


def privacy_policy(request):
    return render(request, 'privacy_policy.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, 'Будь ласка, виправте помилки в формі.')
    else:
        form = LoginForm()
    
    return render(request, 'auth/login-form.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Автоматично логіним користувача після реєстрації
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Будь ласка, виправте помилки в формі.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'auth/register-form.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def profile_view(request):
    patient = getattr(request.user, 'profile', None)

    if patient is None:
        messages.info(request, 'Профіль пацієнта ще не створено. Заповніть дані для точнішої аналітики.')

    is_support = request.user.groups.filter(name='Support').exists()
    support_tickets = []
    if is_support:
        support_tickets = list(
            SupportTicket.objects.select_related("user").order_by("-created_at")[:50]
        )

    last_measurement_message = None
    if patient:
        last_glucose = (
            GlucoseMeasurement.objects.filter(patient=patient)
            .order_by('-date_of_measurement', '-time_of_measurement')
            .first()
        )
        last_insuline = (
            InsulineDoseMeasurement.objects.filter(patient=patient)
            .order_by('-date_of_measurement', '-time')
            .first()
        )

        latest_dt = None
        current_tz = timezone.get_current_timezone()

        if last_glucose:
            combined = datetime.combine(
                last_glucose.date_of_measurement,
                last_glucose.time_of_measurement,
            )
            latest_dt = timezone.make_aware(combined, current_tz)

        if last_insuline:
            combined = datetime.combine(
                last_insuline.date_of_measurement,
                last_insuline.time,
            )
            candidate = timezone.make_aware(combined, current_tz)
            if latest_dt is None or candidate > latest_dt:
                latest_dt = candidate

        if latest_dt is None:
            last_measurement_message = 'Ви ще не додали жодного заміру. Памʼятайте оновлювати дані для точнішого моніторингу.'
        elif timezone.now() - latest_dt > timedelta(days=2):
            last_measurement_message = 'Більше двох днів без нових замірів. Будь ласка, оновіть показники.'

    context = {
        'user_obj': request.user,
        'patient': patient,
        'is_support': is_support,
        'support_tickets': support_tickets,
        'last_measurement_warning': last_measurement_message,
    }
    return render(request, 'auth/profile.html', context)


@login_required
def profile_edit(request):
    patient = getattr(request.user, 'profile', None)

    form = PatientProfileForm(
        request.POST or None,
        request.FILES or None,
        instance=patient,
        user=request.user
    )

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Профіль успішно оновлено.')
            return redirect('profile')
        messages.error(request, 'Виправте помилки у формі та спробуйте ще раз.')

    return render(request, 'auth/profile_edit.html', {'form': form})


@login_required
def glucose_target_settings(request):
    patient = getattr(request.user, 'profile', None)

    if patient is None:
        messages.info(request, 'Створіть профіль пацієнта, щоб налаштувати цільові показники.')
        return redirect('card:patient_card')

    form = GlucoseTargetForm(
        request.POST or None,
        instance=patient,
    )

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Цільовий діапазон глюкози оновлено.')
            return redirect('profile')
        messages.error(request, 'Перевірте введені дані.')

    return render(request, 'auth/glucose_targets.html', {'form': form})