from django.contrib import admin

from .models import (
    AnthropometricMeasurement,
    FoodMeasurement,
    GlucoseMeasurement,
    GlycemicProfileMeasurement,
    InsulineDoseMeasurement,
    PhysicalActivityMeasurement,
    TypeOfActivity,
)


@admin.register(GlucoseMeasurement)
class GlucoseMeasurementAdmin(admin.ModelAdmin):
    list_display = ('patient', 'glucose', 'date_of_measurement', 'time_of_measurement', 'glucose_measurement_category')
    list_filter = ('glucose_measurement_category', 'date_of_measurement')
    search_fields = ('patient__user__username',)


@admin.register(GlycemicProfileMeasurement)
class GlycemicProfileMeasurementAdmin(admin.ModelAdmin):
    list_display = ('patient', 'average_glucose', 'hba1c', 'measurement_date', 'measurement_time')
    list_filter = ('measurement_date',)
    search_fields = ('patient__user__username',)


@admin.register(AnthropometricMeasurement)
class AnthropometricMeasurementAdmin(admin.ModelAdmin):
    list_display = ('patient', 'weight', 'bmi', 'measurement_date', 'measurement_time')
    list_filter = ('measurement_date',)
    search_fields = ('patient__user__username',)


@admin.register(FoodMeasurement)
class FoodMeasurementAdmin(admin.ModelAdmin):
    list_display = ('patient', 'category', 'date_of_measurement', 'time_of_eating', 'bread_unit')
    list_filter = ('category', 'date_of_measurement')
    search_fields = ('patient__user__username',)


@admin.register(InsulineDoseMeasurement)
class InsulineDoseMeasurementAdmin(admin.ModelAdmin):
    list_display = ('patient', 'category', 'insuline_dose', 'date_of_measurement', 'time')
    list_filter = ('category', 'date_of_measurement')
    search_fields = ('patient__user__username',)


@admin.register(PhysicalActivityMeasurement)
class PhysicalActivityMeasurementAdmin(admin.ModelAdmin):
    list_display = ('patient', 'type_of_activity', 'number_of_approaches', 'date_of_measurement', 'time_of_activity')
    list_filter = ('type_of_activity', 'date_of_measurement')
    search_fields = ('patient__user__username',)


@admin.register(TypeOfActivity)
class TypeOfActivityAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
