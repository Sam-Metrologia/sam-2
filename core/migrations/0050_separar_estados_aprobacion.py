# Generated manually
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0049_alter_calibracion_aprobado_por_and_more'),
    ]

    operations = [
        # Campos para CONFIRMACIÓN METROLÓGICA
        migrations.AddField(
            model_name='calibracion',
            name='confirmacion_estado_aprobacion',
            field=models.CharField(
                blank=True,
                choices=[
                    ('pendiente', 'Pendiente de Aprobación'),
                    ('aprobado', 'Aprobado'),
                    ('rechazado', 'Rechazado')
                ],
                default='pendiente',
                max_length=20,
                null=True,
                verbose_name='Estado de Aprobación - Confirmación'
            ),
        ),
        migrations.AddField(
            model_name='calibracion',
            name='confirmacion_aprobado_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='confirmaciones_aprobadas',
                to='core.customuser',
                verbose_name='Aprobado por - Confirmación'
            ),
        ),
        migrations.AddField(
            model_name='calibracion',
            name='confirmacion_fecha_aprobacion',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Fecha de Aprobación - Confirmación'
            ),
        ),
        migrations.AddField(
            model_name='calibracion',
            name='confirmacion_observaciones_rechazo',
            field=models.TextField(
                blank=True,
                null=True,
                verbose_name='Observaciones de Rechazo - Confirmación'
            ),
        ),

        # Campos para INTERVALOS DE CALIBRACIÓN
        migrations.AddField(
            model_name='calibracion',
            name='intervalos_estado_aprobacion',
            field=models.CharField(
                blank=True,
                choices=[
                    ('pendiente', 'Pendiente de Aprobación'),
                    ('aprobado', 'Aprobado'),
                    ('rechazado', 'Rechazado')
                ],
                default='pendiente',
                max_length=20,
                null=True,
                verbose_name='Estado de Aprobación - Intervalos'
            ),
        ),
        migrations.AddField(
            model_name='calibracion',
            name='intervalos_aprobado_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='intervalos_aprobados',
                to='core.customuser',
                verbose_name='Aprobado por - Intervalos'
            ),
        ),
        migrations.AddField(
            model_name='calibracion',
            name='intervalos_fecha_aprobacion',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Fecha de Aprobación - Intervalos'
            ),
        ),
        migrations.AddField(
            model_name='calibracion',
            name='intervalos_observaciones_rechazo',
            field=models.TextField(
                blank=True,
                null=True,
                verbose_name='Observaciones de Rechazo - Intervalos'
            ),
        ),

        # Migrar datos existentes de estado_aprobacion a los nuevos campos
        # Si tiene confirmacion_metrologica_pdf, copiar estado a confirmacion_*
        # Si tiene intervalos_calibracion_pdf, copiar estado a intervalos_*
        migrations.RunPython(
            code=lambda apps, schema_editor: migrate_approval_states(apps, schema_editor),
            reverse_code=migrations.RunPython.noop,
        ),
    ]


def migrate_approval_states(apps, schema_editor):
    """
    Migrar estados de aprobación existentes a los nuevos campos específicos.
    """
    Calibracion = apps.get_model('core', 'Calibracion')

    for cal in Calibracion.objects.all():
        # Si tiene confirmación metrológica, copiar estado
        if cal.confirmacion_metrologica_pdf:
            cal.confirmacion_estado_aprobacion = cal.estado_aprobacion
            cal.confirmacion_aprobado_por = cal.aprobado_por
            cal.confirmacion_fecha_aprobacion = cal.fecha_aprobacion
            cal.confirmacion_observaciones_rechazo = cal.observaciones_rechazo

        # Si tiene intervalos, copiar estado
        if cal.intervalos_calibracion_pdf:
            cal.intervalos_estado_aprobacion = cal.estado_aprobacion
            cal.intervalos_aprobado_por = cal.aprobado_por
            cal.intervalos_fecha_aprobacion = cal.fecha_aprobacion
            cal.intervalos_observaciones_rechazo = cal.observaciones_rechazo

        cal.save()
