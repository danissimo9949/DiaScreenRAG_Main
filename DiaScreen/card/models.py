from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from user_auth.models import Patient


def current_local_time():
    return timezone.localtime().time()


class GlucoseMeasurement(models.Model):

    CATEGORY = (
        ('Натщесердце', 'Натщесердце'),
        ('До сніданку', 'До сніданку'),
        ('Після сніданку', 'Після сніданку'),
        ('Перед перекусом', 'Перед перекусом'),
        ('Після перекусу', 'Після перекусу'),
        ('До обіду', 'До обіду'),
        ('Після обіду', 'Після обіду'),
        ('До вечері', 'До вечері'),
        ('Після вечері', 'Після вечері'),
        ('Перед сном', 'Перед сном'),
        ('Інше', 'Інше'),
    )

    glucose = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0.5), MaxValueValidator(35)],
    )
    glucose_measurement_category = models.CharField(
        max_length=50,
        choices=CATEGORY,
        blank=True,
        null=True,
    )
    date_of_measurement = models.DateField(default=timezone.localdate)
    time_of_measurement = models.TimeField(default=current_local_time)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        category = self.glucose_measurement_category or "—"
        return f"{self.glucose} (категорія: {category})"
    
    class Meta:
        verbose_name = 'Замір глюкози'
        verbose_name_plural = 'Заміри глюкози'
        ordering = ['-date_of_measurement', '-time_of_measurement']
        indexes = [
            models.Index(fields=['patient', 'date_of_measurement']),
        ]


class TypeOfActivity(models.Model):
    name = models.CharField(max_length=100, blank=False, null=False, unique=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Тип активності'
        verbose_name_plural = 'Типи активності'


class PhysicalActivityMeasurement(models.Model):

    number_of_approaches = models.IntegerField(blank=True, null=True)
    type_of_activity = models.ForeignKey(TypeOfActivity, on_delete=models.PROTECT)
    date_of_measurement = models.DateField(default=timezone.localdate)
    time_of_activity = models.TimeField(default=current_local_time)
    commentary = models.TextField(max_length=1000, blank=True, null=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        approaches = self.number_of_approaches if self.number_of_approaches is not None else '—'
        return f'{self.patient} виконав {approaches} підходів у {self.type_of_activity.name}'
    
    class Meta:
        verbose_name = 'Замір фізичної активності'
        verbose_name_plural = 'Заміри фізичної активності'
        ordering = ['-date_of_measurement', '-time_of_activity']
        indexes = [
            models.Index(fields=['patient', 'date_of_measurement']),
        ]


class FoodItem(models.Model):

    name = models.CharField(max_length=200, blank=False, null=False, db_index=True)
    proteins = models.DecimalField(max_digits=6, decimal_places=2)
    fats = models.DecimalField(max_digits=6, decimal_places=2)
    carbohydrates = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"Їжа: {self.name}, білки - {self.proteins}, жири - {self.fats}, вуглеводи - {self.carbohydrates}"
    
    class Meta:
        verbose_name = 'Порція їжі'
        verbose_name_plural = 'Порції їжі'


class FoodMeasurement(models.Model):

    CATEGORY = (
        ('Сніданок', 'Сніданок'),
        ('Перекус', 'Перекус'),
        ('Обід', 'Обід'),
        ('Другий перекус', 'Другий перекус'),
        ('Вечеря', 'Вечеря'),
    )

    category = models.CharField(max_length=50, choices=CATEGORY, default='Сніданок')
    insuline_dose_before = models.DecimalField(max_digits=5, decimal_places=2)
    insuline_dose_after = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    date_of_measurement = models.DateField(default=timezone.localdate)
    time_of_eating = models.TimeField(default=current_local_time)
    bread_unit = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    food_items = models.ManyToManyField(FoodItem, through='FoodPortion', related_name='food_measurements')

    def calculate_bread_unit(self):
        """
        Calculate bread unit (≈12g carbohydrate) based on portions weight.
        """
        qs = self.portions.select_related('food').all()
        if not qs.exists():
            return None

        total_carbohydrates = Decimal('0')
        for portion in qs:
            total_carbohydrates += Decimal(portion.food.carbohydrates)
        return total_carbohydrates / Decimal('12')

    def calculate_dose(self, bread_unit=None):
        bu = bread_unit if bread_unit is not None else self.bread_unit
        if bu is None:
            return None
        return bu

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        bread_unit = self.calculate_bread_unit()
        dose = self.calculate_dose(bread_unit)

        FoodMeasurement.objects.filter(pk=self.pk).update(
            bread_unit=bread_unit,
            insuline_dose_after=dose,
        )

        self.bread_unit = bread_unit
        self.insuline_dose_after = dose

    def __str__(self):
        return f'''
            Дата прийому їжі - {self.date_of_measurement}, час прийому - {self.time_of_eating} |
            Кількість хлібних одиниць - {self.bread_unit}, приблизна доля інсуліну - {self.insuline_dose_after}
        '''
    
    class Meta:
        verbose_name = 'Замір їжі'
        verbose_name_plural = 'Заміри їжі'
        ordering = ['-date_of_measurement', '-time_of_eating']
        indexes = [
            models.Index(fields=['patient', 'date_of_measurement']),
        ]


class FoodPortion(models.Model):
    food = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    measurement = models.ForeignKey('FoodMeasurement', on_delete=models.CASCADE, related_name='portions')
    grams = models.DecimalField(max_digits=7, decimal_places=2, validators=[MinValueValidator(0)])

    def __str__(self):
        return f"{self.grams} г {self.food.name}"

    class Meta:
        verbose_name = 'Порція'
        verbose_name_plural = 'Порції'

class InsulineDoseMeasurement(models.Model):

    CATEGORY = (
        ('Натщесердце', 'Натщесердце'),
        ('До сніданку', 'До сніданку'),
        ('Після сніданку', 'Після сніданку'),
        ('Перед перекусом', 'Перед перекусом'),
        ('Після перекусу', 'Після перекусу'),
        ('До обіду', 'До обіду'),
        ('Після обіду', 'Після обіду'),
        ('До вечері', 'До вечері'),
        ('Після вечері', 'Після вечері'),
        ('Перед сном', 'Перед сном'),
        ('Інше', 'Інше'),
    )

    category = models.CharField(max_length=50, choices=CATEGORY, blank=False, null=False)
    insuline_dose = models.DecimalField(
        max_digits=5, decimal_places=2,
        blank=False, null=False,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    date_of_measurement = models.DateField(default=timezone.localdate)
    time = models.TimeField(default=current_local_time)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return  f'Категорія: {self.category}, станом на {self.time} вкололи {self.insuline_dose} ОД інсуліну'
    
    class Meta:
        verbose_name = 'Замір інсуліну'
        verbose_name_plural = 'Заміри інсуліну'
        ordering = ['-date_of_measurement', '-time']
        indexes = [
            models.Index(fields=['patient', 'date_of_measurement']),
        ]
