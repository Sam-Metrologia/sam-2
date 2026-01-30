# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0051_alter_calibracion_aprobado_por_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='equipo',
            name='proveedor',
            field=models.CharField(
                blank=True,
                help_text='Empresa que vendió el equipo (ej: Multiples, Amazon, etc.)',
                max_length=200,
                null=True,
                verbose_name='Proveedor'
            ),
        ),
    ]
