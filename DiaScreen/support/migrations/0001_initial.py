from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SupportTicket",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("subject", models.CharField(max_length=255)),
                ("description", models.TextField()),
                ("page_context", models.CharField(blank=True, max_length=100)),
                ("status", models.CharField(choices=[("new", "Новий"), ("in_progress", "В роботі"), ("resolved", "Закрито")], default="new", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="support_tickets", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Звернення в підтримку",
                "verbose_name_plural": "Звернення в підтримку",
                "ordering": ("-created_at",),
            },
        ),
    ]


