
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('user_auth', '0002_patient_target_ranges'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Заголовок')),
                ('message', models.TextField(verbose_name='Повідомлення')),
                ('notification_type', models.CharField(choices=[('info', 'Інформаційне'), ('warning', 'Попередження'), ('danger', 'Критичне'), ('success', 'Успіх')], default='info', max_length=20, verbose_name='Тип уведомлення')),
                ('is_read', models.BooleanField(default=False, verbose_name='Прочитано')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Створено')),
                ('read_at', models.DateTimeField(blank=True, null=True, verbose_name='Прочитано о')),
                ('link', models.CharField(blank=True, max_length=500, null=True, verbose_name='Посилання')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL, verbose_name='Користувач')),
            ],
            options={
                'verbose_name': 'Сповіщення',
                'verbose_name_plural': 'Сповіщення',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user', '-created_at', 'is_read'], name='user_auth_n_user_id_created_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user', 'is_read'], name='user_auth_n_user_id_is_read_idx'),
        ),
    ]

