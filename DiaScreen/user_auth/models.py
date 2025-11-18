from datetime import date
from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ObjectDoesNotExist
from django.db import models

class Address(models.Model):
    """
     Address model for users and patients
    """
    country = models.CharField(max_length=50, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    street = models.CharField(max_length=50, blank=True, null=True)
    house_number = models.IntegerField(blank=True, null=True)
    postal_code = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = "Address"
        verbose_name_plural = "Addresses"

    def __str__(self):
        parts = [
            self.country,
            self.city,
            self.street,
            str(self.house_number) if self.house_number else None,
            self.postal_code
        ]
        address_str = ", ".join(filter(None, parts))
        return address_str if address_str else f"Address #{self.id}"


class User(AbstractUser):
    email = models.EmailField(unique=True)

    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    policy_agreement = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username

    @property
    def has_patient_profile(self):
        try:
            self.profile
        except ObjectDoesNotExist:
            return False
        return True


class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    address = models.OneToOneField(Address, on_delete=models.CASCADE, related_name="patient_address")
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    bmi = models.FloatField(null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    blood_type = models.CharField(max_length=10, choices=[('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'), ('AB+', 'AB+'), ('AB-', 'AB-'), ('O+', 'O+'), ('O-', 'O-')], null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    diabetes_type = models.CharField(max_length=50, choices=[('type1', 'Діабет 1-го типу'), ('type2', 'Діабет 2-го типу'), ('gestational', 'Гестаційний діабет')], null=True, blank=True)
    sex = models.CharField(max_length=10, choices=[('male', 'Чоловік'), ('female', 'Жінка')], null=True, blank=True)
    is_on_insulin = models.BooleanField(default=False)
    target_glucose_min = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        default=Decimal('4.0'),
        verbose_name='Мінімальна ціль глюкози (ммоль/л)',
    )
    target_glucose_max = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        default=Decimal('9.0'),
        verbose_name='Максимальна ціль глюкози (ммоль/л)',
    )
  
    def calculate_bmi(self):
        if self.weight and self.height:
            return self.weight / (self.height ** 2)
        return None
    
    def calculate_age(self):
        if self.date_of_birth:
            today = date.today()
            age = today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
            return age
        return None

    def check_is_on_insulin(self):
        if self.diabetes_type == 'type1':
            self.is_on_insulin = True
        elif self.diabetes_type:
            pass
        return self.is_on_insulin

    def save(self, *args, **kwargs):
        self.bmi = self.calculate_bmi()
        self.age = self.calculate_age()
        self.is_on_insulin = self.check_is_on_insulin()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'
        ordering = ['user__username']
        constraints = [
            models.UniqueConstraint(
                fields=['phone_number'],
                condition=models.Q(phone_number__isnull=False),
                name='unique_phone_number'
            )
        ]


class Notification(models.Model):
    TYPE_CHOICES = [
        ('info', 'Інформаційне'),
        ('warning', 'Попередження'),
        ('danger', 'Критичне'),
        ('success', 'Успіх'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Користувач'
    )
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    message = models.TextField(verbose_name='Повідомлення')
    notification_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='info',
        verbose_name='Тип сповіщення'
    )
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Створено')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='Прочитано о')
    link = models.CharField(max_length=500, blank=True, null=True, verbose_name='Посилання')
    
    class Meta:
        verbose_name = 'Сповіщення'
        verbose_name_plural = 'Сповіщення'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at', 'is_read']),
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def mark_as_read(self):
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])