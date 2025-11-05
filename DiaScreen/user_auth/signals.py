import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Patient, Address

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