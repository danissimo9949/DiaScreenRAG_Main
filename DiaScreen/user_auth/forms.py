import re
from decimal import Decimal
from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.core.exceptions import ValidationError

from .models import User, Patient, Address


class LoginForm(AuthenticationForm):
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
        username = self.cleaned_data.get('username')
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, username):
            try:
                user = User.objects.get(email=username)
                return user.username
            except User.DoesNotExist:
                raise ValidationError('Користувач з таким email не знайдений.')
        return username


class UserRegistrationForm(UserCreationForm):
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
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Користувач з таким email вже існує.')
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('Користувач з таким ім\'ям вже існує.')
        return username
    
    def clean(self):
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


class StyledPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label='Email',
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'name@example.com',
            'autocomplete': 'email',
        })
    )


class StyledSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label='Новий пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password',
            'placeholder': 'Введіть новий пароль',
        })
    )
    new_password2 = forms.CharField(
        label='Підтвердження пароля',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password',
            'placeholder': 'Повторіть новий пароль',
        })
    )


class PatientProfileForm(forms.ModelForm):
    username = forms.CharField(
        label='Імʼя користувача',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    phone_number = forms.CharField(
        label='Номер телефону',
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+380...'})
    )
    date_of_birth = forms.DateField(
        label='Дата народження',
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    height = forms.FloatField(
        label='Зріст (м)',
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    weight = forms.FloatField(
        label='Вага (кг)',
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
    )
    address_country = forms.CharField(
        label='Країна',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    address_city = forms.CharField(
        label='Місто',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    address_street = forms.CharField(
        label='Вулиця',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    address_house_number = forms.CharField(
        label='Номер будинку',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    address_postal_code = forms.CharField(
        label='Поштовий індекс',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    class Meta:
        model = Patient
        fields = [
            'phone_number',
            'date_of_birth',
            'sex',
            'height',
            'weight',
            'diabetes_type',
            'blood_type',
            'avatar',
        ]
        widgets = {
            'sex': forms.Select(attrs={'class': 'form-select'}),
            'diabetes_type': forms.Select(attrs={'class': 'form-select'}),
            'blood_type': forms.Select(attrs={'class': 'form-select'}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            if field.widget.attrs.get('class') is None:
                field.widget.attrs['class'] = 'form-control'

        if self.user:
            self.fields['username'].initial = self.user.username

        patient = self.instance if self.instance and self.instance.pk else None
        if patient:
            address = getattr(patient, 'address', None)
            if address:
                self.fields['address_country'].initial = address.country
                self.fields['address_city'].initial = address.city
                self.fields['address_street'].initial = address.street
                self.fields['address_house_number'].initial = address.house_number
                self.fields['address_postal_code'].initial = address.postal_code

    def clean_username(self):
        username = self.cleaned_data['username']
        qs = User.objects.filter(username=username)
        if self.user:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise ValidationError('Користувач з таким імʼям вже існує.')
        return username

    def clean_address_house_number(self):
        value = self.cleaned_data.get('address_house_number')
        if value in (None, ''):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError('Номер будинку повинен бути числом.')

    def clean_height(self):
        height = self.cleaned_data.get('height')
        if height is None:
            return height
        if height > 3:
            height = height / 100
        return round(height, 3)


class GlucoseTargetForm(forms.ModelForm):
    target_glucose_min = forms.DecimalField(
        label='Мінімальна ціль глюкози (ммоль/л)',
        required=False,
        max_digits=4,
        decimal_places=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0'}),
        help_text='Рекомендовано 4.0 ммоль/л',
    )
    target_glucose_max = forms.DecimalField(
        label='Максимальна ціль глюкози (ммоль/л)',
        required=False,
        max_digits=4,
        decimal_places=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0'}),
        help_text='Рекомендовано 9.0 ммоль/л',
    )

    class Meta:
        model = Patient
        fields = ['target_glucose_min', 'target_glucose_max']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        patient = self.instance if self.instance and self.instance.pk else None
        if patient:
            if patient.target_glucose_min is not None:
                self.fields['target_glucose_min'].initial = float(patient.target_glucose_min)
            if patient.target_glucose_max is not None:
                self.fields['target_glucose_max'].initial = float(patient.target_glucose_max)

    def clean(self):
        cleaned_data = super().clean()
        min_target = cleaned_data.get('target_glucose_min')
        max_target = cleaned_data.get('target_glucose_max')

        if min_target is not None and max_target is not None:
            if min_target <= 0 or max_target <= 0:
                raise ValidationError('Цільові значення глюкози повинні бути більше 0.')
            if min_target >= max_target:
                raise ValidationError('Мінімальне значення має бути менше за максимальне.')

        if min_target is None and max_target is not None:
            cleaned_data['target_glucose_min'] = Decimal('4.0')
        if max_target is None and min_target is not None:
            cleaned_data['target_glucose_max'] = Decimal('9.0')

        return cleaned_data

