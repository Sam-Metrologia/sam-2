from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0073_add_proveedor_acreditacion_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='modulo_prestamos_activo',
            field=models.BooleanField(
                default=True,
                verbose_name='Módulo de Préstamos Activo',
                help_text='Activa o desactiva el módulo de préstamos de equipos para esta empresa. Útil para ocultarlo durante auditorías.'
            ),
        ),
    ]
