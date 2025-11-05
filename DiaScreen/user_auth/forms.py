import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from .models import User


class LoginForm(AuthenticationForm):
    """
    Login form for users - supports both username and email
    """
    username = forms.CharField(
        label='Ім\'я користувача або Email',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введіть ім\'я користувача або email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введіть пароль'
        })
    )
    
    error_messages = {
        'invalid_login': 'Неправильне ім\'я користувача або пароль.',
        'inactive': 'Цей аккаунт неактивний.',
    }
    
    def clean_username(self):
        """Перевіряє, чи є введене значення email, і конвертує його в username"""
        username = self.cleaned_data.get('username')
        # Більш точна перевірка на email за допомогою регулярного виразу
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, username):
            try:
                user = User.objects.get(email=username)
                return user.username
            except User.DoesNotExist:
                raise ValidationError('Користувач з таким email не знайдений.')
        return username


class UserRegistrationForm(UserCreationForm):
    """
    Форма для реєстрації нового користувача.
    Розширює стандартну форму UserCreationForm.
    """
    email = forms.EmailField(
        label='Email',
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введіть email'
        }),
        help_text='Обов\'язкове поле. Вкажіть дійсну email адресу.'
    )
    username = forms.CharField(
        label='Ім\'я користувача',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введіть ім\'я користувача'
        }),
        help_text='Обов\'язкове. 150 символів або менше. Лише букви, цифри та @/./+/-/_.'
    )
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введіть пароль'
        }),
        help_text='Пароль повинен містити мінімум 8 символів.'
    )
    password2 = forms.CharField(
        label='Підтвердження пароля',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Повторіть пароль'
        }),
        help_text='Повторіть пароль для підтвердження.'
    )
    policy_agreement = forms.BooleanField(
        label='Я згоден з політикою конфіденційності',
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        error_messages={
            'required': 'Ви повинні згодитися з політикою конфіденційності.'
        }
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'policy_agreement')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['policy_agreement']:
                field.widget.attrs.update({'class': 'form-control'})
    
    def clean_email(self):
        """
        Перевіряє унікальність email
        """
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Користувач з таким email вже існує.')
        return email
    
    def clean_username(self):
        """
        Перевіряє унікальність ім\'я користувача
        """
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('Користувач з таким ім\'ям вже існує.')
        return username
    
    def clean(self):
        """
        Додаткова валідація форми
        """
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        policy_agreement = cleaned_data.get('policy_agreement')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError({
                'password2': 'Паролі не збігаються.'
            })
        
        if not policy_agreement:
            raise ValidationError({
                'policy_agreement': 'Ви повинні згодитися з політикою конфіденційності.'
            })
        
        return cleaned_data
    
    def save(self, commit=True):
        """Зберігає користувача з встановленим email"""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.policy_agreement = self.cleaned_data['policy_agreement']
        if commit:
            user.save()
        return user

