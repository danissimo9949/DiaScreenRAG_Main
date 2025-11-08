from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import DeleteView, UpdateView
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

@login_required
def patient_card(request):
    patient = getattr(request.user, 'profile', None)

    if patient is None:
        messages.error(request, 'Для доступу до карти пацієнта необхідно створити профіль пацієнта.')
        return redirect('home')

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
def analytics_placeholder(request):
    messages.info(request, 'Сторінка аналітики у розробці')
    return redirect('card:patient_card')


@login_required
def doctor_report_placeholder(request):
    messages.info(request, 'Функція створення звіту у розробці')
    return redirect('card:patient_card')

