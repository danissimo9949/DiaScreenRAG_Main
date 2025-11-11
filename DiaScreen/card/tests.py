from datetime import datetime, time

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from user_auth.models import Address, Patient

from .models import (
    AnthropometricMeasurement,
    FoodMeasurement,
    FoodPortion,
    GlucoseMeasurement,
    GlycemicProfileMeasurement,
    InsulineDoseMeasurement,
    PhysicalActivityMeasurement,
    TypeOfActivity,
)


User = get_user_model()


class CardViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.address = Address.objects.create()
        cls.user = User.objects.create_user(
            username="patient",
            email="patient@example.com",
            password="StrongPass123",
        )
        cls.patient = Patient.objects.create(
            user=cls.user,
            address=cls.address,
        )
        cls.type_of_activity = TypeOfActivity.objects.create(name="Біг")

    def setUp(self):
        self.client = Client()

    def test_patient_card_requires_login(self):
        response = self.client.get(reverse('card:patient_card'))
        login_url = reverse('login')
        self.assertRedirects(response, f"{login_url}?next=/card/")

    def test_patient_card_get(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('card:patient_card'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'card/patient_card.html')
        self.assertIn('glucose_form', response.context)
        self.assertIn('support_ticket_form', response.context)

    def test_create_glucose_measurement(self):
        self.client.force_login(self.user)
        payload = {
            'action': 'create_glucose',
            'glucose': '5.6',
            'glucose_measurement_category': 'Натщесердце',
            'date_of_measurement': datetime.today().date(),
            'time_of_measurement': time(8, 0),
        }
        response = self.client.post(reverse('card:patient_card'), data=payload, follow=True)
        self.assertRedirects(response, reverse('card:patient_card'))
        self.assertEqual(GlucoseMeasurement.objects.filter(patient=self.patient).count(), 1)

    def test_create_activity_measurement(self):
        self.client.force_login(self.user)
        payload = {
            'action': 'create_activity',
            'type_of_activity': self.type_of_activity.pk,
            'number_of_approaches': 3,
            'date_of_measurement': datetime.today().date(),
            'time_of_activity': time(9, 30),
            'commentary': 'Ранкова пробіжка',
        }
        response = self.client.post(reverse('card:patient_card'), data=payload, follow=True)
        self.assertRedirects(response, reverse('card:patient_card'))
        self.assertEqual(PhysicalActivityMeasurement.objects.filter(patient=self.patient).count(), 1)

    def test_create_food_measurement_with_portion(self):
        self.client.force_login(self.user)
        payload = {
            'action': 'create_food',
            'category': 'Сніданок',
            'date_of_measurement': datetime.today().date(),
            'time_of_eating': time(7, 45),
            'insuline_dose_before': '2.5',
            'portion-TOTAL_FORMS': '1',
            'portion-INITIAL_FORMS': '0',
            'portion-MIN_NUM_FORMS': '0',
            'portion-MAX_NUM_FORMS': '1000',
            'portion-0-food_name': 'Вівсянка',
            'portion-0-carbohydrates': '24',
            'portion-0-grams': '100',
        }
        response = self.client.post(reverse('card:patient_card'), data=payload, follow=True)
        self.assertRedirects(response, reverse('card:patient_card'))
        meal = FoodMeasurement.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(meal)
        self.assertEqual(meal.category, 'Сніданок')
        self.assertEqual(meal.portions.count(), 1)
        portion = meal.portions.first()
        self.assertIsInstance(portion, FoodPortion)

    def test_create_insuline_measurement(self):
        self.client.force_login(self.user)
        payload = {
            'action': 'create_insuline',
            'category': 'Після сніданку',
            'date_of_measurement': datetime.today().date(),
            'time': time(8, 15),
            'insuline_dose': '1.5',
        }
        response = self.client.post(reverse('card:patient_card'), data=payload, follow=True)
        self.assertRedirects(response, reverse('card:patient_card'))
        self.assertEqual(InsulineDoseMeasurement.objects.filter(patient=self.patient).count(), 1)

    def test_create_glycemic_measurement(self):
        self.client.force_login(self.user)
        payload = {
            'action': 'create_glycemic_profile',
            'measurement_date': datetime.today().date(),
            'measurement_time': time(6, 30),
            'average_glucose': '6.5',
            'hba1c': '5.5',
            'hypoglycemic_events': 0,
            'hyperglycemic_events': 0,
        }
        response = self.client.post(reverse('card:patient_card'), data=payload, follow=True)
        self.assertRedirects(response, reverse('card:patient_card'))
        self.assertEqual(GlycemicProfileMeasurement.objects.filter(patient=self.patient).count(), 1)

    def test_create_anthropometry_measurement(self):
        self.client.force_login(self.user)
        payload = {
            'action': 'create_anthropometry',
            'measurement_date': datetime.today().date(),
            'measurement_time': time(6, 0),
            'weight': '70',
            'bmi': '22.5',
            'waist_circumference': '80',
            'hip_circumference': '95',
            'notes': 'Самопочуття нормальне',
        }
        response = self.client.post(reverse('card:patient_card'), data=payload, follow=True)
        self.assertRedirects(response, reverse('card:patient_card'))
        self.assertEqual(AnthropometricMeasurement.objects.filter(patient=self.patient).count(), 1)
