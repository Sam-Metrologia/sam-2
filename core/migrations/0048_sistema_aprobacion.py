# Generated manually on 2026-01-22

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0047_agregar_formatos_independientes'),
    ]

    operations = [
        # Agregar campo creado_por a Calibracion
        migrations.AddField(
            model_name='calibracion',
            name='creado_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='calibraciones_creadas',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Creado por'
            ),
        ),

        # Agregar campos de aprobación a Calibracion (para confirmación e intervalos)
        migrations.AddField(
            model_name='calibracion',
            name='aprobado_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='calibraciones_aprobadas',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Aprobado por'
            ),
        ),
        migrations.AddField(
            model_name='calibracion',
            name='fecha_aprobacion',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Fecha de Aprobación'
            ),
        ),
        migrations.AddField(
            model_name='calibracion',
            name='estado_aprobacion',
            field=models.CharField(
                choices=[
                    ('pendiente', 'Pendiente de Aprobación'),
                    ('aprobado', 'Aprobado'),
                    ('rechazado', 'Rechazado')
                ],
                default='pendiente',
                max_length=20,
                verbose_name='Estado de Aprobación'
            ),
        ),
        migrations.AddField(
            model_name='calibracion',
            name='observaciones_rechazo',
            field=models.TextField(
                blank=True,
                null=True,
                verbose_name='Observaciones de Rechazo'
            ),
        ),

        # Agregar campo creado_por a Comprobacion
        migrations.AddField(
            model_name='comprobacion',
            name='creado_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='comprobaciones_creadas',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Creado por'
            ),
        ),

        # Agregar campos de aprobación a Comprobacion
        migrations.AddField(
            model_name='comprobacion',
            name='aprobado_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='comprobaciones_aprobadas',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Aprobado por'
            ),
        ),
        migrations.AddField(
            model_name='comprobacion',
            name='fecha_aprobacion',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Fecha de Aprobación'
            ),
        ),
        migrations.AddField(
            model_name='comprobacion',
            name='estado_aprobacion',
            field=models.CharField(
                choices=[
                    ('pendiente', 'Pendiente de Aprobación'),
                    ('aprobado', 'Aprobado'),
                    ('rechazado', 'Rechazado')
                ],
                default='pendiente',
                max_length=20,
                verbose_name='Estado de Aprobación'
            ),
        ),
        migrations.AddField(
            model_name='comprobacion',
            name='observaciones_rechazo',
            field=models.TextField(
                blank=True,
                null=True,
                verbose_name='Observaciones de Rechazo'
            ),
        ),
    ]
