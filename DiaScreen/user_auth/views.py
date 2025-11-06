from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from .forms import LoginForm, UserRegistrationForm
from django.contrib.auth import logout


def home(request):
    return render(request, 'auth/home.html')


def login_view(request):
    """
    Перегляд для входу користувача.
    """
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
    """
    Перегляд для реєстрації нового користувача.
    """
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