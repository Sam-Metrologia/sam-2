# Generated manually to fix production database
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='limite_almacenamiento_mb',
            field=models.IntegerField(
                default=1000,
                help_text='Límite de almacenamiento en MB para la empresa',
                verbose_name='Límite de almacenamiento (MB)'
            ),
        ),
    ]