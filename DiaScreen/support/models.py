from django.conf import settings
from django.db import models


class SupportTicket(models.Model):
    STATUS_NEW = "new"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_RESOLVED = "resolved"
    STATUS_CHOICES = [
        (STATUS_NEW, "Новий"),
        (STATUS_IN_PROGRESS, "В роботі"),
        (STATUS_RESOLVED, "Закрито"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="support_tickets",
        null=True,
        blank=True,
    )
    subject = models.CharField(max_length=255)
    description = models.TextField()
    page_context = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Звернення в підтримку"
        verbose_name_plural = "Звернення в підтримку"

    def __str__(self) -> str:
        return f"#{self.pk or '—'} {self.subject}"


