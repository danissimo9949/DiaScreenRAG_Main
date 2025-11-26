import statistics
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
import json
import requests

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from card.models import (
    GlucoseMeasurement,
    PhysicalActivityMeasurement,
    FoodMeasurement,
    InsulineDoseMeasurement,
    GlycemicProfileMeasurement,
)
from user_auth.models import Patient

PDF_PRIMARY_FONT = "DiaScreenSans"
PDF_BOLD_FONT = "DiaScreenSans-Bold"
_PDF_FONTS_READY = False


def _ensure_pdf_fonts():
    """
    Register a Unicode TTF font so that ReportLab can render Ukrainian text.
    """
    global _PDF_FONTS_READY
    if _PDF_FONTS_READY:
        return True

    base_dir = Path(settings.BASE_DIR)
    candidates_regular = [
        base_dir / "static" / "fonts" / "DejaVuSans.ttf",
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    ]
    candidates_bold = [
        base_dir / "static" / "fonts" / "DejaVuSans-Bold.ttf",
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ]

    regular_path = next((p for p in candidates_regular if p.exists()), None)
    bold_path = next((p for p in candidates_bold if p.exists()), None)

    if regular_path is None:
        return False

    if bold_path is None:
        bold_path = regular_path

    pdfmetrics.registerFont(TTFont(PDF_PRIMARY_FONT, str(regular_path)))
    pdfmetrics.registerFont(TTFont(PDF_BOLD_FONT, str(bold_path)))

    _PDF_FONTS_READY = True
    return True


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


class PatientAnalyticsPDFExportView(LoginRequiredMixin, TemplateView):
    """View для экспорта аналитики в PDF"""
    
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

    def get(self, request, *args, **kwargs):
        period = request.GET.get('period', '7')
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

        glucose_qs = GlucoseMeasurement.objects.filter(patient=self.patient)
        glucose_period_qs = glucose_qs.filter(
            date_of_measurement__range=(start_date, today)
        ) if start_date else glucose_qs
        
        food_qs = FoodMeasurement.objects.filter(patient=self.patient)
        activity_qs = PhysicalActivityMeasurement.objects.filter(patient=self.patient)
        insuline_qs = InsulineDoseMeasurement.objects.filter(patient=self.patient)
        glycemic_profile_qs = GlycemicProfileMeasurement.objects.filter(patient=self.patient)

        weekly_metrics = {
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
        hba1c_avg = glycemic_profile_qs.aggregate(avg=Avg("hba1c"))["avg"]

        glucose_values = [float(g.glucose) for g in glucose_period_qs]
        advanced_metrics = None
        if glucose_values:
            advanced_metrics = self._calculate_advanced_metrics(
                glucose_values=glucose_values,
                patient=self.patient
            )

        font_ready = _ensure_pdf_fonts()
        font_regular = PDF_PRIMARY_FONT if font_ready else "Helvetica"
        font_bold = PDF_BOLD_FONT if font_ready else "Helvetica-Bold"

        pdf_buffer = _render_analytics_pdf(
            patient=self.patient,
            generated_at=timezone.now(),
            period_label=period_label,
            start_date=start_date,
            end_date=today,
            total_glucose=glucose_qs.count(),
            total_food=food_qs.count(),
            total_activity=activity_qs.count(),
            total_insuline=insuline_qs.count(),
            total_glycemic_profile=glycemic_profile_qs.count(),
            weekly_metrics=weekly_metrics,
            glucose_avg=glucose_avg,
            hba1c_avg=hba1c_avg,
            advanced_metrics=advanced_metrics,
            recent_glucose=list(glucose_qs.order_by("-created_at")[:10]),
            font_regular=font_regular,
            font_bold=font_bold,
        )

        filename = f"Analytics_{self.patient.user.username}_{today.strftime('%Y%m%d')}.pdf"
        pdf_bytes = pdf_buffer.getvalue()

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Length'] = len(pdf_bytes)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

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


def _format_decimal(value, suffix="", default="—", precision=2):
    if value is None:
        return default
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return f"{value}{suffix}"
    return f"{numeric:.{precision}f}{suffix}"


def _render_analytics_pdf(
    *,
    patient,
    generated_at,
    period_label,
    start_date,
    end_date,
    total_glucose,
    total_food,
    total_activity,
    total_insuline,
    total_glycemic_profile,
    weekly_metrics,
    glucose_avg,
    hba1c_avg,
    advanced_metrics,
    recent_glucose,
    font_regular,
    font_bold,
):
    
    buffer = BytesIO()
    width, height = A4
    margin = 20 * mm
    line_height = 6 * mm
    bullet = "\u2022"

    c = canvas.Canvas(buffer, pagesize=A4)
    y = height - margin

    def ensure_space(rows=1):
        nonlocal y
        if y - rows * line_height < margin:
            c.showPage()
            y = height - margin
            c.setFont(font_regular, 11)

    def draw_heading(text, size=15):
        nonlocal y
        ensure_space(2)
        c.setFont(font_bold, size)
        c.drawString(margin, y, text)
        y -= line_height * 1.4
        c.setFont(font_regular, 11)

    def draw_line(text, size=11):
        nonlocal y
        ensure_space()
        c.setFont(font_regular, size)
        c.drawString(margin, y, text)
        y -= line_height

    def draw_bullet_line(text, size=11):
        nonlocal y
        ensure_space()
        c.setFont(font_regular, size)
        c.drawString(margin, y, f"{bullet} {text}")
        y -= line_height

    draw_heading("Звіт аналітики пацієнта", size=17)
    full_name = patient.user.get_full_name() or patient.user.username
    draw_line(f"Пацієнт: {full_name}")
    draw_line(f"Тип діабету: {patient.get_diabetes_type_display() or '—'}")
    draw_line(
        f"Дата народження: {patient.date_of_birth.strftime('%d.%m.%Y') if patient.date_of_birth else '—'}"
    )
    draw_line(f"Створено: {generated_at.strftime('%d.%m.%Y %H:%M')}")
    if start_date:
        draw_line(
            f"Період: {start_date.strftime('%d.%m.%Y')} — {end_date.strftime('%d.%m.%Y')} ({period_label})"
        )
    else:
        draw_line(f"Період: повна історія ({period_label})")

    draw_heading("Загальна статистика", size=14)
    draw_bullet_line(f"Всього замірів глюкози: {total_glucose}")
    draw_bullet_line(f"Всього прийомів їжі: {total_food}")
    draw_bullet_line(f"Всього фізичних активностей: {total_activity}")
    draw_bullet_line(f"Всього інʼєкцій інсуліну: {total_insuline}")
    draw_bullet_line(f"Всього глюкозних профілів: {total_glycemic_profile}")

    draw_heading("Активність за період", size=14)
    draw_bullet_line(f"Замірів глюкози: {weekly_metrics['glucose']}")
    draw_bullet_line(f"Прийомів їжі: {weekly_metrics['food']}")
    draw_bullet_line(f"Фізичних активностей: {weekly_metrics['activity']}")
    draw_bullet_line(f"Інʼєкцій інсуліну: {weekly_metrics['insuline']}")
    draw_heading("Середні показники", size=14)
    draw_bullet_line(f"Середній рівень глюкози: {_format_decimal(glucose_avg, ' ммоль/л')}")
    draw_bullet_line(f"Середній HbA1c: {_format_decimal(hba1c_avg, ' %')}")


    if advanced_metrics:
        draw_heading("Розширені метрики глікемії", size=14)
        target_min = patient.target_glucose_min or 4.0
        target_max = patient.target_glucose_max or 9.0
        draw_bullet_line(
            f"Time in Range (TIR): {advanced_metrics['tir_percent']}% "
            f"(ціль: {target_min}-{target_max} ммоль/л)"
        )
        draw_bullet_line(f"Гіпоглікемія (< 3.9 ммоль/л): {advanced_metrics['hypo_percent']}%")
        draw_bullet_line(f"Критична гіпо (< 3.0 ммоль/л): {advanced_metrics['critical_hypo_percent']}%")
        draw_bullet_line(f"Гіперглікемія (> 10.0 ммоль/л): {advanced_metrics['hyper_percent']}%")
        draw_bullet_line(f"Стандартне відхилення (SD): {advanced_metrics['sd']} ммоль/л")
        draw_bullet_line(f"Коефіцієнт варіації (CV): {advanced_metrics['cv']}%")
        draw_bullet_line(f"GMI (оцінка HbA1c): {advanced_metrics['gmi']}%")
        draw_bullet_line(f"Середнє значення: {advanced_metrics['mean']} ммоль/л")

    if recent_glucose:
        draw_heading("Останні заміри глюкози", size=14)
        for record in recent_glucose[:10]:
            category = record.glucose_measurement_category or 'без категорії'
            draw_bullet_line(
                f"{record.date_of_measurement.strftime('%d.%m.%Y')} "
                f"{record.time_of_measurement.strftime('%H:%M')} — "
                f"{record.glucose} ммоль/л ({category})"
            )

    draw_line("")
    draw_line("Звіт сформовано автоматично на основі даних сервісу DiaScreen.", size=10)
    draw_line("Для уточнення звертайтесь до пацієнта або його лікаря.", size=10)

    c.save()
    buffer.seek(0)
    return buffer


def build_analytics_context(patient, period_data):
    context_parts = []
    full_name = patient.user.get_full_name() or patient.user.username
    context_parts.append(f"Пацієнт: {full_name}")
    if patient.diabetes_type:
        context_parts.append(f"Тип діабету: {patient.get_diabetes_type_display()}")
    if patient.age is not None:
        context_parts.append(f"Вік: {patient.age} років")
    if patient.target_glucose_min and patient.target_glucose_max:
        context_parts.append(
            f"Цільовий діапазон глюкози: {float(patient.target_glucose_min):.1f}-{float(patient.target_glucose_max):.1f} ммоль/л"
        )
    
    
    context_parts.append(f"\nПеріод аналізу: {period_data.get('period_label', 'невідомо')}")
    
    context_parts.append("\n=== Загальна статистика ===")
    context_parts.append(f"Всього замірів глюкози: {period_data.get('total_glucose', 0)}")
    context_parts.append(f"Всього прийомів їжі: {period_data.get('total_food', 0)}")
    context_parts.append(f"Всього фізичних активностей: {period_data.get('total_activity', 0)}")
    context_parts.append(f"Всього ін'єкцій інсуліну: {period_data.get('total_insuline', 0)}")
    
    weekly = period_data.get('weekly_metrics', {})
    context_parts.append(f"\nАктивність за період:")
    context_parts.append(f"- Замірів глюкози: {weekly.get('glucose', 0)}")
    context_parts.append(f"- Прийомів їжі: {weekly.get('food', 0)}")
    context_parts.append(f"- Фізичних активностей: {weekly.get('activity', 0)}")
    context_parts.append(f"- Ін'єкцій інсуліну: {weekly.get('insuline', 0)}")
    
    averages = period_data.get('averages', {})
    if averages.get('glucose'):
        context_parts.append(f"\nСередній рівень глюкози: {float(averages['glucose']):.2f} ммоль/л")
    if averages.get('hba1c'):
        context_parts.append(f"Середній HbA1c: {float(averages['hba1c']):.2f}%")
    

    advanced = period_data.get('advanced_metrics')
    if advanced:
        context_parts.append("\n=== Розширені метрики ===")
        context_parts.append(f"Time in Range (TIR): {advanced.get('tir_percent', 0)}%")
        context_parts.append(f"Гіпоглікемія (< 3.9 ммоль/л): {advanced.get('hypo_percent', 0)}%")
        context_parts.append(f"Критична гіпо (< 3.0 ммоль/л): {advanced.get('critical_hypo_percent', 0)}%")
        context_parts.append(f"Гіперглікемія (> 10.0 ммоль/л): {advanced.get('hyper_percent', 0)}%")
        context_parts.append(f"Стандартне відхилення (SD): {advanced.get('sd', 0)} ммоль/л")
        context_parts.append(f"Коефіцієнт варіації (CV): {advanced.get('cv', 0)}%")
        context_parts.append(f"GMI (оцінка HbA1c): {advanced.get('gmi', 0)}%")
        context_parts.append(f"Середнє значення: {advanced.get('mean', 0)} ммоль/л")
    
    return "\n".join(context_parts)


@login_required
@require_http_methods(["POST"])
def analyze_analytics_data(request, pk):
    """API endpoint для аналізу даних через AI"""
    patient = get_object_or_404(Patient.objects.select_related("user"), pk=pk)
    
    if not (request.user.is_staff or request.user.is_superuser or patient.user_id == request.user.id):
        return JsonResponse({'success': False, 'error': 'Немає доступу'}, status=403)
    
    try:
        data = json.loads(request.body)
        period = data.get('period', '7')
        
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

        weekly_metrics = {
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
        hba1c_avg = glycemic_profile_qs.aggregate(avg=Avg("hba1c"))["avg"]

        glucose_values = [float(g.glucose) for g in glucose_period_qs]
        advanced_metrics = None
        if glucose_values:
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
            
            advanced_metrics = {
                "tir_percent": round(tir_percent, 1),
                "hypo_percent": round(hypo_percent, 1),
                "critical_hypo_percent": round(critical_hypo_percent, 1),
                "hyper_percent": round(hyper_percent, 1),
                "sd": round(sd, 2),
                "cv": round(cv, 1),
                "gmi": round(gmi, 1),
                "mean": round(mean, 2),
            }

        period_data = {
            'period_label': period_label,
            'total_glucose': glucose_qs.count(),
            'total_food': food_qs.count(),
            'total_activity': activity_qs.count(),
            'total_insuline': insuline_qs.count(),
            'weekly_metrics': weekly_metrics,
            'averages': {
                'glucose': glucose_avg,
                'hba1c': hba1c_avg,
            },
            'advanced_metrics': advanced_metrics,
        }
        
        analytics_context = build_analytics_context(patient, period_data)
        
        question = (
            "Проаналізуй мої дані за цей період та дай персональні рекомендації. "
            "Вкажи на проблемні моменти, що можна покращити, та що робити добре. "
            "Будь конкретним та корисним. Давай практичні поради."
        )
        
        rag_personal_url = getattr(
            settings,
            'RAG_PERSONAL_API_URL',
            f"{getattr(settings, 'RAG_API_URL', 'http://127.0.0.1:8001/get-response').rstrip('/')}/personalized"
        )
        
        response = requests.post(
            rag_personal_url,
            json={
                'question': question,
                'context': analytics_context,
                'mode': 'personalized',
            },
            timeout=300
        )
        response.raise_for_status()
        data = response.json()
        answer_text = (data.get('answer') or '').strip()
        
        if not answer_text:
            answer_text = 'Вибачте, сервіс не надав відповіді. Спробуйте пізніше.'
        
        return JsonResponse({
            'success': True,
            'analysis': answer_text,
            'context_used': True,
        })
        
    except requests.RequestException as e:
        return JsonResponse({
            'success': False,
            'error': 'Помилка з\'єднання з AI-сервісом. Спробуйте пізніше.'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Помилка: {str(e)}'
        }, status=500)
