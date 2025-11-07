from django.db import models
from django.conf import settings
from django.utils import timezone


class AISession(models.Model):
    session_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_sessions',
        verbose_name='Користувач',
        db_index=True
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Час створення',
        db_index=True
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Час оновлення',
        db_index=True
    )
    summary = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Короткий опис',
        help_text='Короткий опис діалогу (перше повідомлення або заголовок)'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна сесія',
        help_text='Чи є сесія активною'
    )

    class Meta:
        verbose_name = 'AI Сесія'
        verbose_name_plural = 'AI Сесії'
        ordering = ['-updated_at', '-created_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"Сесія {self.session_id} - {self.user.username} ({self.created_at.strftime('%d.%m.%Y %H:%M')})"

    def get_last_message_time(self):
        last_message = self.messages.order_by('-created_at').first()
        return last_message.created_at if last_message else self.created_at

    def get_message_count(self):
        return self.messages.count()

    def update_summary_from_first_message(self):
        first_message = self.messages.filter(sender='user').first()
        if first_message and not self.summary:
            self.summary = first_message.message_text[:200]
            self.save(update_fields=['summary'])


class AIMessage(models.Model):
    SENDER_CHOICES = [
        ('user', 'Користувач'),
        ('assistant', 'ШІ-асистент'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Обробляється'),
        ('completed', 'Завершено'),
        ('error', 'Помилка'),
    ]

    message_id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(
        AISession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Сесія',
        db_index=True
    )
    sender = models.CharField(
        max_length=20,
        choices=SENDER_CHOICES,
        verbose_name='Відправник',
        db_index=True
    )
    message_text = models.TextField(
        verbose_name='Текст повідомлення'
    )
    
    context = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        verbose_name='Контекст RAG',
        help_text='Контекст для RAG: попередні повідомлення, embeddings, тощо'
    )
    sources = models.JSONField(
        default=list,
        blank=True,
        null=True,
        verbose_name='Джерела',
        help_text='Джерела інформації використані для відповіді (документи, статті)'
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        verbose_name='Метадані',
        help_text='Додаткова інформація: модель, версія API, параметри запросу'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='completed',
        verbose_name='Статус обробки',
        db_index=True
    )
    token_count = models.IntegerField(
        blank=True,
        null=True,
        verbose_name='Кількість токенів',
        help_text='Кількість токенів в повідомленні'
    )
    response_time_ms = models.IntegerField(
        blank=True,
        null=True,
        verbose_name='Час відповіді (мс)',
        help_text='Час обробки запиту мікросервісом в мілісекундах'
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name='Повідомлення про помилку',
        help_text='Повідомлення про помилку якщо статус = error'
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Час створення',
        db_index=True
    )

    class Meta:
        verbose_name = 'AI Повідомлення'
        verbose_name_plural = 'AI Повідомлення'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        sender_name = dict(self.SENDER_CHOICES).get(self.sender, self.sender)
        preview = self.message_text[:50] + '...' if len(self.message_text) > 50 else self.message_text
        return f"{sender_name}: {preview}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AISession.objects.filter(pk=self.session.session_id).update(updated_at=timezone.now())
        
        if self.sender == 'user' and not self.session.summary:
            self.session.update_summary_from_first_message()
