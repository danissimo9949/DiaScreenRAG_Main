from datetime import timedelta
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import DeleteView, UpdateView
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .forms import (
    AnthropometricMeasurementForm,
    FoodMeasurementForm,
    FoodPortionFormSet,
    FoodPortionFormSetEdit,
    GlucoseMeasurementForm,
    GlycemicProfileMeasurementForm,
    InsulineDoseMeasurementForm,
    PhysicalActivityMeasurementForm,
)
from .models import (
    AnthropometricMeasurement,
    FoodMeasurement,
    GlucoseMeasurement,
    GlycemicProfileMeasurement,
    InsulineDoseMeasurement,
    PhysicalActivityMeasurement,
)

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


@login_required
def patient_card(request):
    patient = request.user.profile

    glucose_form = GlucoseMeasurementForm()
    activity_form = PhysicalActivityMeasurementForm()
    food_form = FoodMeasurementForm()
    portion_formset = FoodPortionFormSet(prefix='portion')
    insuline_form = InsulineDoseMeasurementForm()
    glycemic_form = GlycemicProfileMeasurementForm()
    anthropometry_form = AnthropometricMeasurementForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_glucose':
            glucose_form = GlucoseMeasurementForm(request.POST)
            if glucose_form.is_valid():
                obj = glucose_form.save(commit=False)
                obj.patient = patient
                obj.save()
                messages.success(request, 'Замір глюкози додано')
                return redirect('card:patient_card')

        elif action == 'create_activity':
            activity_form = PhysicalActivityMeasurementForm(request.POST)
            if activity_form.is_valid():
                obj = activity_form.save(commit=False)
                obj.patient = patient
                obj.save()
                messages.success(request, 'Фізична активність додана')
                return redirect('card:patient_card')

        elif action == 'create_food':
            food_form = FoodMeasurementForm(request.POST)
            portion_formset = FoodPortionFormSet(request.POST, prefix='portion')
            if food_form.is_valid() and portion_formset.is_valid():
                meal = food_form.save(commit=False)
                meal.patient = patient
                meal.save()
                portion_formset.instance = meal
                portion_formset.save()
                # meal.save() will recalc in model
                meal.save()
                messages.success(request, 'Прийом їжі додано')
                return redirect('card:patient_card')

        elif action == 'create_insuline':
            insuline_form = InsulineDoseMeasurementForm(request.POST)
            if insuline_form.is_valid():
                obj = insuline_form.save(commit=False)
                obj.patient = patient
                obj.save()
                messages.success(request, 'Інʼєкцію інсуліну додано')
                return redirect('card:patient_card')

        elif action == 'create_glycemic_profile':
            glycemic_form = GlycemicProfileMeasurementForm(request.POST)
            if glycemic_form.is_valid():
                obj = glycemic_form.save(commit=False)
                obj.patient = patient
                obj.save()
                messages.success(request, 'Показник глікемії додано')
                return redirect('card:patient_card')

        elif action == 'create_anthropometry':
            anthropometry_form = AnthropometricMeasurementForm(request.POST)
            if anthropometry_form.is_valid():
                obj = anthropometry_form.save(commit=False)
                obj.patient = patient
                obj.save()
                messages.success(request, 'Антропометричний запис додано')
                return redirect('card:patient_card')

    glucose_qs = GlucoseMeasurement.objects.filter(patient=patient).order_by('-date_of_measurement', '-time_of_measurement')
    activity_qs = PhysicalActivityMeasurement.objects.filter(patient=patient).order_by('-date_of_measurement', '-time_of_activity')
    food_qs = FoodMeasurement.objects.filter(patient=patient).order_by('-date_of_measurement', '-time_of_eating')
    insuline_qs = InsulineDoseMeasurement.objects.filter(patient=patient).order_by('-date_of_measurement', '-time')
    glycemic_qs = GlycemicProfileMeasurement.objects.filter(patient=patient).order_by('-measurement_date', '-measurement_time')
    anthropometry_qs = AnthropometricMeasurement.objects.filter(patient=patient).order_by('-measurement_date', '-measurement_time')

    glucose_list = list(glucose_qs[:10])
    activity_list = list(activity_qs[:10])
    food_list = list(food_qs[:10])
    insuline_list = list(insuline_qs[:10])
    glycemic_list = list(glycemic_qs[:10])
    anthropometry_list = list(anthropometry_qs[:10])

    return render(request, 'card/patient_card.html', {
        'glucose_form': glucose_form,
        'activity_form': activity_form,
        'food_form': food_form,
        'portion_formset': portion_formset,
        'insuline_form': insuline_form,
        'glycemic_form': glycemic_form,
        'anthropometry_form': anthropometry_form,
        'glucose_list': glucose_list,
        'activity_list': activity_list,
        'food_list': food_list,
        'insuline_list': insuline_list,
        'glycemic_list': glycemic_list,
        'anthropometry_list': anthropometry_list,
        'glucose_latest': glucose_qs.first(),
        'activity_latest': activity_qs.first(),
        'food_latest': food_qs.first(),
        'insuline_latest': insuline_qs.first(),
        'glycemic_latest': glycemic_qs.first(),
        'anthropometry_latest': anthropometry_qs.first(),
        'patient': patient,
    })


class GlucoseUpdateView(UpdateView):
    model = GlucoseMeasurement
    form_class = GlucoseMeasurementForm
    template_name = 'card/edit_form.html'

    def get_success_url(self):
        return reverse('card:patient_card')


class GlucoseDeleteView(DeleteView):
    model = GlucoseMeasurement
    success_url = reverse_lazy('card:patient_card')
    template_name = 'card/confirm_delete.html'


class ActivityUpdateView(UpdateView):
    model = PhysicalActivityMeasurement
    form_class = PhysicalActivityMeasurementForm
    template_name = 'card/edit_form.html'

    def get_success_url(self):
        return reverse('card:patient_card')


class ActivityDeleteView(DeleteView):
    model = PhysicalActivityMeasurement
    success_url = reverse_lazy('card:patient_card')
    template_name = 'card/confirm_delete.html'


class FoodUpdateView(UpdateView):
    model = FoodMeasurement
    form_class = FoodMeasurementForm
    template_name = 'card/edit_food.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method == 'POST':
            context['portion_formset'] = FoodPortionFormSetEdit(self.request.POST, instance=self.object, prefix='portion')
        else:
            context['portion_formset'] = FoodPortionFormSetEdit(instance=self.object, prefix='portion')
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        formset = FoodPortionFormSetEdit(self.request.POST, instance=self.object, prefix='portion')
        if form.is_valid() and formset.is_valid():
            return self.form_valid(form, formset)
        return self.form_invalid(form, formset)

    def form_valid(self, form, formset):
        self.object = form.save()
        formset.instance = self.object
        formset.save()
        self.object.save()
        messages.success(self.request, 'Прийом їжі оновлено')
        return redirect('card:patient_card')

    def form_invalid(self, form, formset):
        context = self.get_context_data()
        context['form'] = form
        context['portion_formset'] = formset
        return self.render_to_response(context)


class FoodDeleteView(DeleteView):
    model = FoodMeasurement
    success_url = reverse_lazy('card:patient_card')
    template_name = 'card/confirm_delete.html'


class InsulineUpdateView(UpdateView):
    model = InsulineDoseMeasurement
    form_class = InsulineDoseMeasurementForm
    template_name = 'card/edit_form.html'

    def get_success_url(self):
        return reverse('card:patient_card')


class InsulineDeleteView(DeleteView):
    model = InsulineDoseMeasurement
    success_url = reverse_lazy('card:patient_card')
    template_name = 'card/confirm_delete.html'


@login_required
def doctor_report(request):
    patient = request.user.profile

    period = request.GET.get('period', '30')
    today = timezone.localdate()
    start_date = None
    period_label = 'Вся історія'

    if period in {'7', '30', '90'}:
        days = int(period)
        start_date = today - timedelta(days=days - 1)
        period_label = f'Останні {days} днів'
    elif period == '365':
        start_date = today - timedelta(days=364)
        period_label = 'Останній рік'

    date_filter = {}
    if start_date:
        date_filter['date_of_measurement__range'] = (start_date, today)
        glycemic_filter = {'measurement_date__range': (start_date, today)}
    else:
        glycemic_filter = {}

    glucose_qs = GlucoseMeasurement.objects.filter(patient=patient, **date_filter).order_by('-date_of_measurement', '-time_of_measurement')
    food_qs = FoodMeasurement.objects.filter(patient=patient, **date_filter).order_by('-date_of_measurement', '-time_of_eating')
    activity_qs = PhysicalActivityMeasurement.objects.filter(patient=patient, **date_filter).order_by('-date_of_measurement', '-time_of_activity')
    insuline_qs = InsulineDoseMeasurement.objects.filter(patient=patient, **date_filter).order_by('-date_of_measurement', '-time')
    glycemic_qs = GlycemicProfileMeasurement.objects.filter(patient=patient, **glycemic_filter).order_by('-measurement_date', '-measurement_time')
    anthropometry_qs = AnthropometricMeasurement.objects.filter(patient=patient).order_by('-measurement_date', '-measurement_time')

    last_glucose = glucose_qs.first()
    glucose_values = [float(g.glucose) for g in glucose_qs]
    hba1c_values = [float(g.hba1c) for g in glycemic_qs]
    summary = {
        'glucose_total': glucose_qs.count(),
        'food_total': food_qs.count(),
        'activity_total': activity_qs.count(),
        'insuline_total': insuline_qs.count(),
        'glycemic_total': glycemic_qs.count(),
        'anthropometry_total': anthropometry_qs.count(),
        'glucose_avg': round(sum(glucose_values) / len(glucose_values), 2) if glucose_values else None,
        'hba1c_avg': round(sum(hba1c_values) / len(hba1c_values), 2) if hba1c_values else None,
        'last_glucose': last_glucose,
    }

    font_ready = _ensure_pdf_fonts()
    font_regular = PDF_PRIMARY_FONT if font_ready else "Helvetica"
    font_bold = PDF_BOLD_FONT if font_ready else "Helvetica-Bold"

    pdf_buffer = _render_pdf_report(
        patient=patient,
        generated_at=timezone.now(),
        period_label=period_label,
        start_date=start_date,
        end_date=today,
        summary=summary,
        glucose_records=list(glucose_qs[:15]),
        food_records=list(food_qs[:10]),
        activity_records=list(activity_qs[:10]),
        insuline_records=list(insuline_qs[:10]),
        glycemic_records=list(glycemic_qs[:5]),
        anthropometry_latest=anthropometry_qs.first(),
        font_regular=font_regular,
        font_bold=font_bold,
    )

    filename = f"DiaScreen_Report_{patient.user.username}_{today.strftime('%Y%m%d')}.pdf"
    pdf_bytes = pdf_buffer.getvalue()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Length'] = len(pdf_bytes)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _format_decimal(value, suffix="", default="—", precision=2):
    if value is None:
        return default
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return f"{value}{suffix}"
    return f"{numeric:.{precision}f}{suffix}"


def _render_pdf_report(
    *,
    patient,
    generated_at,
    period_label,
    start_date,
    end_date,
    summary,
    glucose_records,
    food_records,
    activity_records,
    insuline_records,
    glycemic_records,
    anthropometry_latest,
    font_regular,
    font_bold,
):
    """
    Draw a concise PDF report using ReportLab primitives.
    """
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

    draw_heading("Медичний звіт пацієнта", size=17)
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

    draw_heading("Коротке зведення", size=14)
    draw_bullet_line(f"Замірів глюкози: {summary['glucose_total']}")
    draw_bullet_line(f"Середній рівень глюкози: {_format_decimal(summary['glucose_avg'], ' ммоль/л')}")
    draw_bullet_line(f"Середній HbA1c: {_format_decimal(summary['hba1c_avg'], ' %')}")
    draw_bullet_line(f"Прийомів їжі: {summary['food_total']}")
    draw_bullet_line(f"Фізичних активностей: {summary['activity_total']}")
    draw_bullet_line(f"Інʼєкцій інсуліну: {summary['insuline_total']}")
    if summary['last_glucose']:
        last = summary['last_glucose']
        category = last.glucose_measurement_category or 'без категорії'
        draw_bullet_line(
            f"Останній замір: {last.date_of_measurement.strftime('%d.%m.%Y')} "
            f"{last.time_of_measurement.strftime('%H:%M')} — {last.glucose} ммоль/л ({category})"
        )

    if glycemic_records:
        draw_heading("Профіль глікемії", size=14)
        for record in glycemic_records:
            draw_bullet_line(
                f"{record.measurement_date.strftime('%d.%m.%Y')} "
                f"{record.measurement_time.strftime('%H:%M')} · "
                f"Середня глюкоза {record.average_glucose} ммоль/л · HbA1c {record.hba1c}% "
                f"(гіпо: {record.hypoglycemic_events}, гіпер: {record.hyperglycemic_events})"
            )

    if anthropometry_latest:
        draw_heading("Антропометрія", size=14)
        draw_line(
            f"Останній запис: {anthropometry_latest.measurement_date.strftime('%d.%m.%Y')} "
            f"{anthropometry_latest.measurement_time.strftime('%H:%M')}"
        )
        draw_bullet_line(
            f"Вага: {anthropometry_latest.weight} кг · ІМТ: {anthropometry_latest.bmi}"
        )
        draw_bullet_line(
            f"Талія: {anthropometry_latest.waist_circumference} см · "
            f"Стегна: {anthropometry_latest.hip_circumference} см"
        )
        if anthropometry_latest.notes:
            draw_line(f"Примітки: {anthropometry_latest.notes}")

    if glucose_records:
        draw_heading("Останні заміри глюкози", size=14)
        for record in glucose_records:
            draw_bullet_line(
                f"{record.date_of_measurement.strftime('%d.%m.%Y')} "
                f"{record.time_of_measurement.strftime('%H:%M')} — {record.glucose} ммоль/л "
                f"({record.glucose_measurement_category or 'без категорії'})"
            )

    if food_records:
        draw_heading("Прийоми їжі", size=14)
        for record in food_records:
            draw_bullet_line(
                f"{record.date_of_measurement.strftime('%d.%m.%Y')} "
                f"{record.time_of_eating.strftime('%H:%M')} — {record.category}, "
                f"ХО: {_format_decimal(record.bread_unit)} · "
                f"доза до: {record.insuline_dose_before} · "
                f"доза після: {_format_decimal(record.insuline_dose_after)}"
            )

    if insuline_records:
        draw_heading("Інʼєкції інсуліну", size=14)
        for record in insuline_records:
            draw_bullet_line(
                f"{record.date_of_measurement.strftime('%d.%m.%Y')} "
                f"{record.time.strftime('%H:%M')} — {record.category}, доза {record.insuline_dose} ОД"
            )

    if activity_records:
        draw_heading("Фізична активність", size=14)
        for record in activity_records:
            extras = []
            if record.number_of_approaches is not None:
                extras.append(f"підходів: {record.number_of_approaches}")
            if record.commentary:
                extras.append(record.commentary)
            suffix = f" ({'; '.join(extras)})" if extras else ""
            draw_bullet_line(
                f"{record.date_of_measurement.strftime('%d.%m.%Y')} "
                f"{record.time_of_activity.strftime('%H:%M')} — {record.type_of_activity.name}{suffix}"
            )

    draw_line("")
    draw_line("Звіт сформовано автоматично на основі даних сервісу DiaScreen.", size=10)
    draw_line("Для уточнення звертайтесь до пацієнта або його лікаря.", size=10)

    c.save()
    buffer.seek(0)
    return buffer

