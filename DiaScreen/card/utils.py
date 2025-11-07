from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg
from collections import defaultdict

from user_auth.models import Patient
from .models import (
    GlucoseMeasurement,
    InsulineDoseMeasurement,
    FoodMeasurement,
    PhysicalActivityMeasurement,
)


def get_start_date():
    """Возвращает дату начала последней недели (7 дней назад)."""
    return timezone.localdate() - timedelta(days=7)


def group_by_day(queryset, date_field):
    """Группирует queryset по дате."""
    grouped = defaultdict(list)
    for obj in queryset:
        day = getattr(obj, date_field)
        grouped[day].append(obj)
    return dict(grouped)


def get_glucose_weekly(patient):
    """Возвращает замеры глюкозы по дням за неделю."""
    start_date = get_start_date()
    qs = GlucoseMeasurement.objects.filter(
        patient=patient,
        date_of_measurement__gte=start_date
    ).order_by("date_of_measurement", "time_of_measurement")

    # если нет данных — берём всё что есть
    if not qs.exists():
        qs = GlucoseMeasurement.objects.filter(patient=patient).order_by("date_of_measurement")

    grouped = group_by_day(qs, "date_of_measurement")

    result = []
    for date, measurements in grouped.items():
        day_avg = round(sum(float(m.glucose) for m in measurements) / len(measurements), 2)
        result.append({
            "date": date.strftime("%Y-%m-%d"),
            "average": day_avg,
            "measurements": [
                {
                    "value": float(m.glucose),
                    "category": m.glucose_measurement_category,
                    "time": m.time_of_measurement.strftime("%H:%M"),
                }
                for m in measurements
            ]
        })
    return result


def get_insulin_weekly(patient):
    """Возвращает замеры инсулина по дням."""
    start_date = get_start_date()
    qs = InsulineDoseMeasurement.objects.filter(
        patient=patient,
        date_of_measurement__gte=start_date
    ).order_by("date_of_measurement", "time")

    if not qs.exists():
        qs = InsulineDoseMeasurement.objects.filter(patient=patient).order_by("date_of_measurement")

    grouped = group_by_day(qs, "date_of_measurement")

    result = []
    for date, doses in grouped.items():
        result.append({
            "date": date.strftime("%Y-%m-%d"),
            "total_dose": round(sum(float(d.insuline_dose) for d in doses), 2),
            "records": [
                {
                    "category": d.category,
                    "dose": float(d.insuline_dose),
                    "time": d.time.strftime("%H:%M"),
                }
                for d in doses
            ]
        })
    return result


def get_food_weekly(patient):
    """Возвращает данные по еде за неделю по дням."""
    start_date = get_start_date()
    qs = FoodMeasurement.objects.filter(
        patient=patient,
        date_of_measurement__gte=start_date
    ).prefetch_related("portions__food").order_by("date_of_measurement")

    if not qs.exists():
        qs = FoodMeasurement.objects.filter(patient=patient).prefetch_related("portions__food").order_by("date_of_measurement")

    grouped = group_by_day(qs, "date_of_measurement")

    result = []
    for date, meals in grouped.items():
        result.append({
            "date": date.strftime("%Y-%m-%d"),
            "meals": [
                {
                    "category": m.category,
                    "bread_unit": float(m.bread_unit or 0),
                    "insuline_dose_before": float(m.insuline_dose_before or 0),
                    "insuline_dose_after": float(m.insuline_dose_after or 0),
                    "time": m.time_of_eating.strftime("%H:%M"),
                    "food_items": [
                        {
                            "name": portion.food.name,
                            "grams": float(portion.grams),
                            "carbs": float(portion.food.carbohydrates),
                        }
                        for portion in m.portions.all()
                    ]
                }
                for m in meals
            ]
        })
    return result


def get_activity_weekly(patient):
    """Возвращает физическую активность по дням."""
    start_date = get_start_date()
    qs = PhysicalActivityMeasurement.objects.filter(
        patient=patient,
        date_of_measurement__gte=start_date
    ).select_related("type_of_activity").order_by("date_of_measurement")

    if not qs.exists():
        qs = PhysicalActivityMeasurement.objects.filter(patient=patient).select_related("type_of_activity").order_by("date_of_measurement")

    grouped = group_by_day(qs, "date_of_measurement")

    result = []
    for date, activities in grouped.items():
        result.append({
            "date": date.strftime("%Y-%m-%d"),
            "activities": [
                {
                    "type": a.type_of_activity.name,
                    "approaches": a.number_of_approaches,
                    "comment": a.commentary,
                    "time": a.time_of_activity.strftime("%H:%M"),
                }
                for a in activities
            ]
        })
    return result


def get_patient_weekly_data(patient: Patient):
    """Собирает все данные пациента за неделю (или меньше, если данных не хватает)."""
    return {
        "patient_id": patient.id,
        "patient_name": patient.user.username,
        "glucose": get_glucose_weekly(patient),
        "insulin": get_insulin_weekly(patient),
        "food": get_food_weekly(patient),
        "activity": get_activity_weekly(patient),
    }
