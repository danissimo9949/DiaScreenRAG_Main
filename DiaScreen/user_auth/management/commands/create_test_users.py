"""
Django management command для створення тестових користувачів з заповненими даними
для дослідження RAG-технології.

Використання:
    python manage.py create_test_users
"""

from datetime import date, timedelta, time
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from user_auth.models import User, Patient, Address
from card.models import (
    GlucoseMeasurement,
    InsulineDoseMeasurement,
    FoodMeasurement,
    FoodItem,
    FoodPortion,
    PhysicalActivityMeasurement,
    TypeOfActivity,
    AnthropometricMeasurement,
    GlycemicProfileMeasurement,
)


class Command(BaseCommand):
    help = 'Створює тестових користувачів з заповненими профілями та медичними записами'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Початок створення тестових користувачів...'))

        # Створюємо тестових користувачів
        users_data = [
            {
                'username': 'test_patient1',
                'email': 'test1@diascreen.com',
                'password': 'TestPass123',
                'first_name': 'Олександр',
                'last_name': 'Петренко',
                'patient_data': {
                    'diabetes_type': 'type1',
                    'date_of_birth': date(1990, 5, 15),
                    'sex': 'male',
                    'height': 1.75,
                    'weight': 75.0,
                    'blood_type': 'A+',
                    'phone_number': '+380501234567',
                    'target_glucose_min': Decimal('4.0'),
                    'target_glucose_max': Decimal('9.0'),
                }
            },
            {
                'username': 'test_patient2',
                'email': 'test2@diascreen.com',
                'password': 'TestPass123',
                'first_name': 'Марія',
                'last_name': 'Коваленко',
                'patient_data': {
                    'diabetes_type': 'type2',
                    'date_of_birth': date(1985, 8, 22),
                    'sex': 'female',
                    'height': 1.65,
                    'weight': 68.0,
                    'blood_type': 'B+',
                    'phone_number': '+380501234568',
                    'target_glucose_min': Decimal('5.0'),
                    'target_glucose_max': Decimal('8.0'),
                }
            },
            {
                'username': 'test_patient3',
                'email': 'test3@diascreen.com',
                'password': 'TestPass123',
                'first_name': 'Дмитро',
                'last_name': 'Іваненко',
                'patient_data': {
                    'diabetes_type': 'type1',
                    'date_of_birth': date(1995, 3, 10),
                    'sex': 'male',
                    'height': 1.80,
                    'weight': 82.0,
                    'blood_type': 'O+',
                    'phone_number': '+380501234569',
                    'target_glucose_min': Decimal('4.5'),
                    'target_glucose_max': Decimal('9.5'),
                }
            },
        ]

        created_users = []

        for idx, user_data in enumerate(users_data):
            # Перевіряємо чи користувач вже існує
            user = None
            patient = None
            
            if User.objects.filter(username=user_data['username']).exists():
                self.stdout.write(
                    self.style.WARNING(f'Користувач {user_data["username"]} вже існує, перевіряємо профіль...')
                )
                user = User.objects.get(username=user_data['username'])
                
                # Перевіряємо чи є профіль пацієнта
                try:
                    patient = user.profile
                    # Оновлюємо дані профілю
                    for key, value in user_data['patient_data'].items():
                        setattr(patient, key, value)
                    patient.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Оновлено профіль для {user_data["username"]}')
                    )
                except ObjectDoesNotExist:
                    # Користувач існує, але профілю немає - створюємо
                    # Створюємо унікальну адресу для кожного пацієнта
                    address = Address.objects.create(
                        country='Україна',
                        city='Київ',
                        street=f'Хрещатик {idx + 1}',
                        house_number=idx + 1,
                        postal_code=f'0100{idx + 1}'
                    )
                    patient, created = Patient.objects.get_or_create(
                        user=user,
                        defaults={
                            'address': address,
                            **user_data['patient_data']
                        }
                    )
                    if not created:
                        # Якщо профіль вже існує, оновлюємо
                        for key, value in user_data['patient_data'].items():
                            setattr(patient, key, value)
                        patient.address = address
                        patient.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Створено/оновлено профіль для {user_data["username"]}')
                    )
            else:
                # Створюємо унікальну адресу для кожного пацієнта
                address = Address.objects.create(
                    country='Україна',
                    city='Київ',
                    street=f'Хрещатик {idx + 1}',
                    house_number=idx + 1,
                    postal_code=f'0100{idx + 1}'
                )

                # Створюємо користувача
                user = User.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=user_data['password'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    policy_agreement=True,
                )

                # Створюємо профіль пацієнта (get_or_create для безпеки)
                patient, created = Patient.objects.get_or_create(
                    user=user,
                    defaults={
                        'address': address,
                        **user_data['patient_data']
                    }
                )
                if not created:
                    # Якщо профіль вже існує, оновлюємо дані
                    for key, value in user_data['patient_data'].items():
                        setattr(patient, key, value)
                    patient.address = address
                    patient.save()

                self.stdout.write(
                    self.style.SUCCESS(f'✓ Створено користувача: {user_data["username"]} / {user_data["password"]}')
                )

            created_users.append((user, user_data['password']))

        # Створюємо медичні записи для кожного користувача
        self.stdout.write(self.style.SUCCESS('\nСтворення медичних записів...'))

        for user, password in created_users:
            try:
                patient = user.profile
                self._create_medical_records(patient, user.username)
            except ObjectDoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Профіль не знайдено для {user.username}, пропускаємо...')
                )

        # Виводимо інформацію про створених користувачів
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('ТЕСТОВІ КОРИСТУВАЧІ УСПІШНО СТВОРЕНО'))
        self.stdout.write(self.style.SUCCESS('='*60))
        for user, password in created_users:
            patient = user.profile
            self.stdout.write(f'\nЛогін: {user.username}')
            self.stdout.write(f'Пароль: {password}')
            self.stdout.write(f'Email: {user.email}')
            self.stdout.write(f'Тип діабету: {patient.get_diabetes_type_display()}')
            self.stdout.write(f'Цільовий діапазон: {patient.target_glucose_min}-{patient.target_glucose_max} ммоль/л')
            self.stdout.write(f'Замірів глюкози: {GlucoseMeasurement.objects.filter(patient=patient).count()}')
            self.stdout.write(f'Ін\'єкцій інсуліну: {InsulineDoseMeasurement.objects.filter(patient=patient).count()}')
            self.stdout.write(f'Прийомів їжі: {FoodMeasurement.objects.filter(patient=patient).count()}')
            self.stdout.write(f'Активностей: {PhysicalActivityMeasurement.objects.filter(patient=patient).count()}')
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))

    def _create_medical_records(self, patient, username):
        """Створює медичні записи для пацієнта"""
        today = timezone.localdate()
        
        # Створюємо типи активності, якщо їх немає
        activity_types = ['Біг', 'Плавання', 'Велосипед', 'Ходьба', 'Йога']
        for activity_name in activity_types:
            TypeOfActivity.objects.get_or_create(name=activity_name)

        # Створюємо продукти, якщо їх немає
        food_items_data = [
            {'name': 'Вівсянка', 'proteins': 12.0, 'fats': 7.0, 'carbohydrates': 60.0},
            {'name': 'Яйце', 'proteins': 13.0, 'fats': 11.0, 'carbohydrates': 1.0},
            {'name': 'Хліб білий', 'proteins': 8.0, 'fats': 3.0, 'carbohydrates': 50.0},
            {'name': 'Курятина', 'proteins': 25.0, 'fats': 7.0, 'carbohydrates': 0.0},
            {'name': 'Гречка', 'proteins': 13.0, 'fats': 3.0, 'carbohydrates': 72.0},
        ]
        
        food_items = {}
        for food_data in food_items_data:
            food, created = FoodItem.objects.get_or_create(
                name=food_data['name'],
                defaults={
                    'proteins': Decimal(str(food_data['proteins'])),
                    'fats': Decimal(str(food_data['fats'])),
                    'carbohydrates': Decimal(str(food_data['carbohydrates'])),
                }
            )
            food_items[food_data['name']] = food

        # Заміри глюкози за останні 14 днів
        glucose_values = [
            (5.6, 'Натщесердце', time(7, 0)),
            (6.2, 'Після сніданку', time(9, 30)),
            (5.8, 'До обіду', time(13, 0)),
            (7.1, 'Після обіду', time(15, 30)),
            (5.4, 'До вечері', time(19, 0)),
            (6.8, 'Після вечері', time(21, 0)),
            (5.2, 'Перед сном', time(22, 30)),
        ]

        for i in range(14):
            measurement_date = today - timedelta(days=i)
            for glucose_val, category, measurement_time in glucose_values:
                GlucoseMeasurement.objects.get_or_create(
                    patient=patient,
                    date_of_measurement=measurement_date,
                    time_of_measurement=measurement_time,
                    defaults={
                        'glucose': Decimal(str(glucose_val + (i % 3) * 0.3)),
                        'glucose_measurement_category': category,
                    }
                )

        # Ін'єкції інсуліну
        insuline_data = [
            ('Натщесердце', 8.0, time(7, 15)),
            ('Після сніданку', 4.0, time(9, 45)),
            ('До обіду', 6.0, time(13, 15)),
            ('Після обіду', 3.0, time(15, 45)),
            ('До вечері', 7.0, time(19, 15)),
            ('Перед сном', 10.0, time(22, 45)),
        ]

        for i in range(7):
            measurement_date = today - timedelta(days=i)
            for category, dose, injection_time in insuline_data:
                InsulineDoseMeasurement.objects.get_or_create(
                    patient=patient,
                    date_of_measurement=measurement_date,
                    time=injection_time,
                    category=category,
                    defaults={
                        'insuline_dose': Decimal(str(dose)),
                    }
                )

        # Прийоми їжі
        food_meals = [
            ('Сніданок', time(8, 0), 'Вівсянка', 100, 2.5),
            ('Обід', time(13, 30), 'Курятина', 150, 3.0),
            ('Обід', time(13, 30), 'Гречка', 200, 0),
            ('Вечеря', time(19, 30), 'Яйце', 100, 2.0),
            ('Вечеря', time(19, 30), 'Хліб білий', 50, 0),
        ]

        for i in range(7):
            measurement_date = today - timedelta(days=i)
            for category, eating_time, food_name, grams, insulin_before in food_meals:
                if food_name in food_items:
                    food_measurement, created = FoodMeasurement.objects.get_or_create(
                        patient=patient,
                        date_of_measurement=measurement_date,
                        time_of_eating=eating_time,
                        category=category,
                        defaults={
                            'insuline_dose_before': Decimal(str(insulin_before)),
                        }
                    )
                    
                    if created:
                        FoodPortion.objects.create(
                            food=food_items[food_name],
                            measurement=food_measurement,
                            grams=Decimal(str(grams))
                        )
                        food_measurement.save()  # Перераховує хлібні одиниці

        # Фізична активність
        activities = [
            ('Біг', 3, time(18, 0), 'Ранкова пробіжка'),
            ('Плавання', 1, time(20, 0), 'Вечірнє плавання'),
            ('Ходьба', None, time(10, 0), 'Прогулянка'),
        ]

        for i in range(5):
            measurement_date = today - timedelta(days=i)
            for activity_name, approaches, activity_time, commentary in activities:
                activity_type = TypeOfActivity.objects.get(name=activity_name)
                PhysicalActivityMeasurement.objects.get_or_create(
                    patient=patient,
                    date_of_measurement=measurement_date,
                    time_of_activity=activity_time,
                    type_of_activity=activity_type,
                    defaults={
                        'number_of_approaches': approaches,
                        'commentary': commentary,
                    }
                )

        # Антропометричні виміри
        for i in range(0, 30, 7):  # Кожні 7 днів
            measurement_date = today - timedelta(days=i)
            base_weight = float(patient.weight) if patient.weight else 70.0
            base_bmi = float(patient.bmi) if patient.bmi else 22.0
            AnthropometricMeasurement.objects.get_or_create(
                patient=patient,
                measurement_date=measurement_date,
                defaults={
                    'measurement_time': time(8, 0),
                    'weight': Decimal(str(base_weight + (i % 3) * 0.5)),
                    'bmi': Decimal(str(base_bmi + (i % 3) * 0.1)),
                    'waist_circumference': Decimal('80.0'),
                    'hip_circumference': Decimal('95.0'),
                    'notes': 'Регулярний контроль',
                }
            )

        # Глікемічні профілі
        for i in range(0, 60, 14):  # Кожні 2 тижні
            measurement_date = today - timedelta(days=i)
            GlycemicProfileMeasurement.objects.get_or_create(
                patient=patient,
                measurement_date=measurement_date,
                defaults={
                    'measurement_time': time(9, 0),
                    'average_glucose': Decimal('6.2'),
                    'hba1c': Decimal('5.8'),
                    'hypoglycemic_events': 2,
                    'hyperglycemic_events': 3,
                }
            )

        self.stdout.write(f'  ✓ Створено записи для {username}')

