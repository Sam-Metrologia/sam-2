"""
Migración: Permitir null en estado_aprobacion de Comprobacion y limpiar
documentos manuales del flujo de aprobación.

Los documentos subidos manualmente (sin datos JSON) no deben estar en el
flujo de aprobación. Esta migración:
1. Permite NULL en Comprobacion.estado_aprobacion (igual que Calibracion)
2. Establece estado_aprobacion=NULL para documentos sin datos JSON
"""

from django.db import migrations, models


def limpiar_aprobacion_documentos_manuales(apps, schema_editor):
    """
    Establece estado_aprobacion=None para documentos que fueron subidos
    manualmente (no tienen datos JSON) y que están en estado 'pendiente'.
    """
    Calibracion = apps.get_model('core', 'Calibracion')
    Comprobacion = apps.get_model('core', 'Comprobacion')

    # Confirmaciones metrológicas subidas manualmente (sin datos JSON)
    cal_confirmaciones = Calibracion.objects.filter(
        confirmacion_metrologica_pdf__isnull=False,
        confirmacion_estado_aprobacion='pendiente',
    ).filter(
        confirmacion_metrologica_datos__isnull=True
    )
    count_conf = cal_confirmaciones.update(confirmacion_estado_aprobacion=None)

    # También limpiar las que tienen JSON vacío {}
    cal_confirmaciones_vacias = Calibracion.objects.filter(
        confirmacion_metrologica_pdf__isnull=False,
        confirmacion_estado_aprobacion='pendiente',
        confirmacion_metrologica_datos={}
    )
    count_conf += cal_confirmaciones_vacias.update(confirmacion_estado_aprobacion=None)

    # Intervalos de calibración subidos manualmente (sin datos JSON)
    cal_intervalos = Calibracion.objects.filter(
        intervalos_calibracion_pdf__isnull=False,
        intervalos_estado_aprobacion='pendiente',
    ).filter(
        intervalos_calibracion_datos__isnull=True
    )
    count_int = cal_intervalos.update(intervalos_estado_aprobacion=None)

    cal_intervalos_vacios = Calibracion.objects.filter(
        intervalos_calibracion_pdf__isnull=False,
        intervalos_estado_aprobacion='pendiente',
        intervalos_calibracion_datos={}
    )
    count_int += cal_intervalos_vacios.update(intervalos_estado_aprobacion=None)

    # Comprobaciones subidas manualmente (sin datos JSON)
    comp_manual = Comprobacion.objects.filter(
        comprobacion_pdf__isnull=False,
        estado_aprobacion='pendiente',
    ).filter(
        datos_comprobacion__isnull=True
    )
    count_comp = comp_manual.update(estado_aprobacion=None)

    comp_manual_vacias = Comprobacion.objects.filter(
        comprobacion_pdf__isnull=False,
        estado_aprobacion='pendiente',
        datos_comprobacion={}
    )
    count_comp += comp_manual_vacias.update(estado_aprobacion=None)

    if count_conf or count_int or count_comp:
        print(f"\n  Documentos manuales limpiados:")
        print(f"    - Confirmaciones: {count_conf}")
        print(f"    - Intervalos: {count_int}")
        print(f"    - Comprobaciones: {count_comp}")


def revertir(apps, schema_editor):
    """Reversión: volver a poner 'pendiente' en documentos sin JSON."""
    Calibracion = apps.get_model('core', 'Calibracion')
    Comprobacion = apps.get_model('core', 'Comprobacion')

    Calibracion.objects.filter(
        confirmacion_metrologica_pdf__isnull=False,
        confirmacion_estado_aprobacion__isnull=True,
        confirmacion_metrologica_datos__isnull=True
    ).update(confirmacion_estado_aprobacion='pendiente')

    Calibracion.objects.filter(
        intervalos_calibracion_pdf__isnull=False,
        intervalos_estado_aprobacion__isnull=True,
        intervalos_calibracion_datos__isnull=True
    ).update(intervalos_estado_aprobacion='pendiente')

    Comprobacion.objects.filter(
        comprobacion_pdf__isnull=False,
        estado_aprobacion__isnull=True,
        datos_comprobacion__isnull=True
    ).update(estado_aprobacion='pendiente')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0058_agregar_listado_equipos_formato'),
    ]

    operations = [
        # Paso 1: Permitir NULL en estado_aprobacion de Comprobacion
        migrations.AlterField(
            model_name='comprobacion',
            name='estado_aprobacion',
            field=models.CharField(
                blank=True,
                choices=[
                    ('pendiente', 'Pendiente de Aprobación'),
                    ('aprobado', 'Aprobado'),
                    ('rechazado', 'Rechazado'),
                ],
                default='pendiente',
                max_length=20,
                null=True,
                verbose_name='Estado de Aprobación',
            ),
        ),
        # Paso 2: Limpiar datos de documentos manuales
        migrations.RunPython(
            limpiar_aprobacion_documentos_manuales,
            reverse_code=revertir,
        ),
    ]
