from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.db.models import Avg
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

        today = timezone.localdate()
        week_start = today - timedelta(days=6)

        glucose_qs = GlucoseMeasurement.objects.filter(patient=patient)
        food_qs = FoodMeasurement.objects.filter(patient=patient)
        activity_qs = PhysicalActivityMeasurement.objects.filter(patient=patient)
        insuline_qs = InsulineDoseMeasurement.objects.filter(patient=patient)
        glycemic_profile_qs = GlycemicProfileMeasurement.objects.filter(patient=patient)

        context.update(
            {
                "patient": patient,
                "total_glucose_measurements": glucose_qs.count(),
                "total_food_measurements": food_qs.count(),
                "total_activity_measurements": activity_qs.count(),
                "total_insuline_measurements": insuline_qs.count(),
                "total_glycemic_profile_measurements": glycemic_profile_qs.count(),
            }
        )

        context["weekly_metrics"] = {
            "glucose": glucose_qs.filter(
                date_of_measurement__range=(week_start, today)
            ).count(),
            "food": food_qs.filter(
                date_of_measurement__range=(week_start, today)
            ).count(),
            "activity": activity_qs.filter(
                date_of_measurement__range=(week_start, today)
            ).count(),
            "insuline": insuline_qs.filter(
                date_of_measurement__range=(week_start, today)
            ).count(),
        }

        context["averages"] = {
            "glucose": glucose_qs.aggregate(avg=Avg("glucose"))["avg"],
            "hba1c": glycemic_profile_qs.aggregate(avg=Avg("hba1c"))["avg"],
        }

        context["recent_glucose_measurements"] = (
            glucose_qs.select_related("patient__user").order_by("-created_at")[:5]
        )

        return context
