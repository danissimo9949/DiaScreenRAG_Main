from django import forms
from django.forms import inlineformset_factory

from .models import (
    FoodItem,
    FoodMeasurement,
    FoodPortion,
    GlucoseMeasurement,
    InsulineDoseMeasurement,
    PhysicalActivityMeasurement,
)


class GlucoseMeasurementForm(forms.ModelForm):
    class Meta:
        model = GlucoseMeasurement
        fields = ['glucose', 'glucose_measurement_category', 'date_of_measurement', 'time_of_measurement']
        widgets = {
            'glucose': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'glucose_measurement_category': forms.Select(attrs={'class': 'form-select'}),
            'date_of_measurement': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time_of_measurement': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }


class PhysicalActivityMeasurementForm(forms.ModelForm):
    class Meta:
        model = PhysicalActivityMeasurement
        fields = ['type_of_activity', 'number_of_approaches', 'date_of_measurement', 'time_of_activity', 'commentary']
        widgets = {
            'type_of_activity': forms.Select(attrs={'class': 'form-select'}),
            'number_of_approaches': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'date_of_measurement': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time_of_activity': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'commentary': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class FoodMeasurementForm(forms.ModelForm):
    class Meta:
        model = FoodMeasurement
        fields = ['category', 'date_of_measurement', 'time_of_eating', 'insuline_dose_before']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'date_of_measurement': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time_of_eating': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'insuline_dose_before': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }


class FoodPortionForm(forms.ModelForm):
    food_name = forms.CharField(label='Назва продукту', max_length=200)
    carbohydrates = forms.DecimalField(
        label='Вуглеводи (г у порції)',
        max_digits=6,
        decimal_places=2,
        required=False,
        min_value=0,
    )

    class Meta:
        model = FoodPortion
        fields = ['grams']
        widgets = {
            'grams': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['grams'].required = False
        if self.instance and self.instance.pk and self.instance.food:
            self.fields['food_name'].initial = self.instance.food.name
            self.fields['carbohydrates'].initial = self.instance.food.carbohydrates

    def save(self, commit=True):
        food_name = self.cleaned_data.get('food_name')
        carbs = self.cleaned_data.get('carbohydrates', 0) or 0

        if not food_name or not food_name.strip():
            if self.instance.pk:
                return self.instance
            return None

        defaults = {
            'proteins': 0,
            'fats': 0,
            'carbohydrates': carbs,
        }
        food_item, created = FoodItem.objects.get_or_create(
            name=food_name.strip(),
            defaults=defaults,
        )
        
        if not created:
            if food_item.carbohydrates != carbs:
                food_item.carbohydrates = carbs
                food_item.save(update_fields=['carbohydrates'])

        self.instance.food = food_item

        if commit:
            return super().save(commit=True)
        return self.instance


FoodPortionFormSet = inlineformset_factory(
    parent_model=FoodMeasurement,
    model=FoodPortion,
    form=FoodPortionForm,
    extra=1,
    can_delete=True,
)

FoodPortionFormSetEdit = inlineformset_factory(
    parent_model=FoodMeasurement,
    model=FoodPortion,
    form=FoodPortionForm,
    extra=0,
    can_delete=True,
)


class InsulineDoseMeasurementForm(forms.ModelForm):
    class Meta:
        model = InsulineDoseMeasurement
        fields = ['category', 'date_of_measurement', 'time', 'insuline_dose']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'date_of_measurement': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'insuline_dose': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }


