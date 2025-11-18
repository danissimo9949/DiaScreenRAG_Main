import logging
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Patient, Address, Notification

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_patient(sender, instance, created, **kwargs):
    """
    Automatically create a Patient and Address for a new User
    """
    if created:
        if not Patient.objects.filter(user=instance).exists():
            try:
                address = Address.objects.create()
                Patient.objects.create(user=instance, address=address)
            except Exception as e:
                logger.error(f"Error creating Patient for user {instance.username}: {e}")


@receiver(post_save, sender='card.GlucoseMeasurement')
def check_glucose_levels(sender, instance, created, **kwargs):

    if not created:
        return
    
    try:
        patient = instance.patient
        user = patient.user
        glucose_value = float(instance.glucose)
        
        target_min = float(patient.target_glucose_min) if patient.target_glucose_min else 4.0
        target_max = float(patient.target_glucose_max) if patient.target_glucose_max else 9.0
        
        if glucose_value < 3.5:
            Notification.objects.create(
                user=user,
                title='⚠️ Критична гіпоглікемія!',
                message=f'Рівень глюкози {glucose_value} ммоль/л є критично низьким. Негайно прийміть заходи!',
                notification_type='danger',
                link='/card/'
            )
        elif glucose_value < target_min:
            Notification.objects.create(
                user=user,
                title='⚠️ Низький рівень глюкози',
                message=f'Рівень глюкози {glucose_value} ммоль/л нижчий за цільовий діапазон ({target_min}-{target_max} ммоль/л).',
                notification_type='warning',
                link='/card/'
            )
        elif glucose_value > 15.0:
            Notification.objects.create(
                user=user,
                title='🔴 Критична гіперглікемія!',
                message=f'Рівень глюкози {glucose_value} ммоль/л є критично високим. Перевірте дозування інсуліну!',
                notification_type='danger',
                link='/card/'
            )
        elif glucose_value > target_max:
            Notification.objects.create(
                user=user,
                title='⚠️ Високий рівень глюкози',
                message=f'Рівень глюкози {glucose_value} ммоль/л вищий за цільовий діапазон ({target_min}-{target_max} ммоль/л).',
                notification_type='warning',
                link='/card/'
            )
    except Exception as e:
        logger.error(f"Error creating glucose notification: {e}")