from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_auth', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='patient',
            name='target_glucose_max',
            field=models.DecimalField(
                blank=True,
                decimal_places=1,
                default=Decimal('9.0'),
                max_digits=4,
                null=True,
                verbose_name='Максимальна ціль глюкози (ммоль/л)',
            ),
        ),
        migrations.AddField(
            model_name='patient',
            name='target_glucose_min',
            field=models.DecimalField(
                blank=True,
                decimal_places=1,
                default=Decimal('4.0'),
                max_digits=4,
                null=True,
                verbose_name='Мінімальна ціль глюкози (ммоль/л)',
            ),
        ),
    ]

