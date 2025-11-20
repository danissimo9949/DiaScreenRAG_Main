import statistics
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import TemplateView

from card.models import (
    GlucoseMeasurement,
    PhysicalActivityMeasurement,
    FoodMeasurement,
    InsulineDoseMeasurement,
    GlycemicProfileMeasurement,
)
from user_auth.models import Patient


class PatientAnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = "analytic/dashboard.html"
    patient = None

    def dispatch(self, request, *args, **kwargs):
        patient_pk = kwargs.get("pk")
        self.patient = get_object_or_404(
            Patient.objects.select_related("user"), pk=patient_pk
        )

        if not self._user_can_view_patient(request.user):
            raise PermissionDenied("You don't have access to this patient's analytics.")

        return super().dispatch(request, *args, **kwargs)

    def _user_can_view_patient(self, user):
        if user.is_staff or user.is_superuser:
            return True
        return self.patient.user_id == user.id

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.patient

        period = self.request.GET.get('period', '7')
        today = timezone.localdate()
        
        if period == '30':
            start_date = today - timedelta(days=29)
            period_label = '30 днів'
        elif period == '90':
            start_date = today - timedelta(days=89)
            period_label = '90 днів'
        elif period == '365':
            start_date = today - timedelta(days=364)
            period_label = '1 рік'
        else:
            start_date = today - timedelta(days=6)
            period_label = '7 днів'
            period = '7'

        glucose_qs = GlucoseMeasurement.objects.filter(patient=patient)
        glucose_period_qs = glucose_qs.filter(
            date_of_measurement__range=(start_date, today)
        ) if start_date else glucose_qs
        
        food_qs = FoodMeasurement.objects.filter(patient=patient)
        activity_qs = PhysicalActivityMeasurement.objects.filter(patient=patient)
        insuline_qs = InsulineDoseMeasurement.objects.filter(patient=patient)
        glycemic_profile_qs = GlycemicProfileMeasurement.objects.filter(patient=patient)

        context.update(
            {
                "patient": patient,
                "period": period,
                "period_label": period_label,
                "total_glucose_measurements": glucose_qs.count(),
                "total_food_measurements": food_qs.count(),
                "total_activity_measurements": activity_qs.count(),
                "total_insuline_measurements": insuline_qs.count(),
                "total_glycemic_profile_measurements": glycemic_profile_qs.count(),
            }
        )

        context["weekly_metrics"] = {
            "glucose": glucose_period_qs.count(),
            "food": food_qs.filter(
                date_of_measurement__range=(start_date, today)
            ).count() if start_date else food_qs.count(),
            "activity": activity_qs.filter(
                date_of_measurement__range=(start_date, today)
            ).count() if start_date else activity_qs.count(),
            "insuline": insuline_qs.filter(
                date_of_measurement__range=(start_date, today)
            ).count() if start_date else insuline_qs.count(),
        }

    
        glucose_avg = glucose_qs.aggregate(avg=Avg("glucose"))["avg"]
        context["averages"] = {
            "glucose": glucose_avg,
            "hba1c": glycemic_profile_qs.aggregate(avg=Avg("hba1c"))["avg"],
        }

        glucose_values = [float(g.glucose) for g in glucose_period_qs]
        if glucose_values:
            context["advanced_metrics"] = self._calculate_advanced_metrics(
                glucose_values=glucose_values,
                patient=patient
            )
        else:
            context["advanced_metrics"] = None

        context["recent_glucose_measurements"] = (
            glucose_qs.select_related("patient__user").order_by("-created_at")[:5]
        )

        context["chart_payload"] = self._build_chart_payload(
            glucose_qs=glucose_period_qs,
            glucose_all_qs=glucose_qs,
            weekly_metrics=context["weekly_metrics"],
            start_date=start_date,
            today=today,
        )

        return context

    def _calculate_advanced_metrics(self, *, glucose_values, patient):
        """Расчет расширенных метрик: TIR, SD, CV"""
        if not glucose_values:
            return None
        
        target_min = float(patient.target_glucose_min) if patient.target_glucose_min else 4.0
        target_max = float(patient.target_glucose_max) if patient.target_glucose_max else 9.0
        
        in_range = sum(1 for v in glucose_values if target_min <= v <= target_max)
        tir_percent = (in_range / len(glucose_values)) * 100 if glucose_values else 0
    
        hypo_count = sum(1 for v in glucose_values if v < 3.9)
        hypo_percent = (hypo_count / len(glucose_values)) * 100 if glucose_values else 0
        
        critical_hypo_count = sum(1 for v in glucose_values if v < 3.0)
        critical_hypo_percent = (critical_hypo_count / len(glucose_values)) * 100 if glucose_values else 0
        
        hyper_count = sum(1 for v in glucose_values if v > 10.0)
        hyper_percent = (hyper_count / len(glucose_values)) * 100 if glucose_values else 0

        try:
            sd = statistics.stdev(glucose_values) if len(glucose_values) > 1 else 0
        except:
            sd = 0
        
        mean = statistics.mean(glucose_values)
        cv = (sd / mean * 100) if mean > 0 else 0
        
        gmi = (3.31 + 0.02392 * mean) if mean > 0 else 0
        
        return {
            "tir_percent": round(tir_percent, 1),
            "hypo_percent": round(hypo_percent, 1),
            "critical_hypo_percent": round(critical_hypo_percent, 1),
            "hyper_percent": round(hyper_percent, 1),
            "sd": round(sd, 2),
            "cv": round(cv, 1),
            "gmi": round(gmi, 1),
            "mean": round(mean, 2),
        }

    def _build_chart_payload(self, *, glucose_qs, glucose_all_qs, weekly_metrics, start_date, today):
        daily_glucose = (
            glucose_qs.values("date_of_measurement")
            .annotate(avg=Avg("glucose"))
            .order_by("date_of_measurement")
        )

        glucose_trend_labels = [
            entry["date_of_measurement"].strftime("%d.%m") for entry in daily_glucose
        ]
        glucose_trend_values = [
            float(entry["avg"]) if entry["avg"] is not None else None
            for entry in daily_glucose
        ]

        hourly_data = {}
        for measurement in glucose_qs:
            hour = measurement.time_of_measurement.hour
            if hour not in hourly_data:
                hourly_data[hour] = []
            hourly_data[hour].append(float(measurement.glucose))
        
        hourly_labels = []
        hourly_means = []
        hourly_medians = []
        if hourly_data:
            for hour in sorted(hourly_data.keys()):
                values = hourly_data[hour]
                if values:
                    hourly_labels.append(f"{hour:02d}:00")
                    hourly_means.append(round(statistics.mean(values), 2))
                    try:
                        hourly_medians.append(round(statistics.median(values), 2))
                    except:
                        hourly_medians.append(hourly_means[-1])

        weekly_activity_labels = [
            "Замірів глюкози",
            "Прийомів їжі",
            "Фізичних активностей",
            "Інʼєкцій інсуліну",
        ]
        weekly_activity_values = [
            weekly_metrics["glucose"],
            weekly_metrics["food"],
            weekly_metrics["activity"],
            weekly_metrics["insuline"],
        ]

        category_counts = (
            glucose_all_qs.values("glucose_measurement_category")
            .annotate(total=Count("id"))
            .order_by("glucose_measurement_category")
        )

        category_labels = []
        category_values = []
        for entry in category_counts:
            label = entry["glucose_measurement_category"] or "Без категорії"
            category_labels.append(label)
            category_values.append(entry["total"])

        return {
            "glucoseTrend": {
                "labels": glucose_trend_labels,
                "data": glucose_trend_values,
            },
            "glucoseByHour": {
                "labels": hourly_labels,
                "means": hourly_means,
                "medians": hourly_medians,
            },
            "weeklyActivity": {
                "labels": weekly_activity_labels,
                "data": weekly_activity_values,
            },
            "glucoseCategories": {
                "labels": category_labels,
                "data": category_values,
            },
        }
