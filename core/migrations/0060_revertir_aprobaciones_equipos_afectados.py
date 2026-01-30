"""
Migración de datos: Revertir aprobaciones de los 5 equipos afectados.

Los equipos CB-001, CB-002, CB-031, CB-041 tuvieron documentos aprobados
durante el incidente. Se revierten a 'pendiente' para que puedan ser
re-aprobados correctamente con el sistema corregido.
"""

from django.db import migrations


# Códigos internos de los equipos afectados
EQUIPOS_AFECTADOS = ['CB-001', 'CB-002', 'CB-031', 'CB-041']


def revertir_aprobaciones(apps, schema_editor):
    Calibracion = apps.get_model('core', 'Calibracion')
    Comprobacion = apps.get_model('core', 'Comprobacion')

    # Revertir confirmaciones aprobadas a 'pendiente'
    count_conf = Calibracion.objects.filter(
        equipo__codigo_interno__in=EQUIPOS_AFECTADOS,
        confirmacion_estado_aprobacion='aprobado',
    ).update(
        confirmacion_estado_aprobacion='pendiente',
        confirmacion_aprobado_por=None,
        confirmacion_fecha_aprobacion=None,
        confirmacion_observaciones_rechazo=None,
    )

    # Revertir intervalos aprobados a 'pendiente'
    count_int = Calibracion.objects.filter(
        equipo__codigo_interno__in=EQUIPOS_AFECTADOS,
        intervalos_estado_aprobacion='aprobado',
    ).update(
        intervalos_estado_aprobacion='pendiente',
        intervalos_aprobado_por=None,
        intervalos_fecha_aprobacion=None,
        intervalos_observaciones_rechazo=None,
    )

    # Revertir comprobaciones aprobadas a 'pendiente'
    count_comp = Comprobacion.objects.filter(
        equipo__codigo_interno__in=EQUIPOS_AFECTADOS,
        estado_aprobacion='aprobado',
    ).update(
        estado_aprobacion='pendiente',
        aprobado_por=None,
        fecha_aprobacion=None,
        observaciones_rechazo=None,
    )

    if count_conf or count_int or count_comp:
        print(f"\n  Aprobaciones revertidas a 'pendiente':")
        print(f"    - Confirmaciones: {count_conf}")
        print(f"    - Intervalos: {count_int}")
        print(f"    - Comprobaciones: {count_comp}")
    else:
        print("\n  No se encontraron documentos aprobados para revertir.")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0059_limpiar_aprobacion_documentos_manuales'),
    ]

    operations = [
        migrations.RunPython(
            revertir_aprobaciones,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
