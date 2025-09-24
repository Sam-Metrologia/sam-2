# core/migrations/0020_add_performance_indexes.py
# Migración para añadir índices críticos de performance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_systemscheduleconfig'),
    ]

    operations = [
        # Índices para el modelo Equipo
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_equipo_estado ON core_equipo (estado);",
            reverse_sql="DROP INDEX IF EXISTS idx_equipo_estado;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_equipo_empresa_estado ON core_equipo (empresa_id, estado);",
            reverse_sql="DROP INDEX IF EXISTS idx_equipo_empresa_estado;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_equipo_proxima_calibracion ON core_equipo (proxima_calibracion);",
            reverse_sql="DROP INDEX IF EXISTS idx_equipo_proxima_calibracion;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_equipo_codigo_interno ON core_equipo (codigo_interno);",
            reverse_sql="DROP INDEX IF EXISTS idx_equipo_codigo_interno;"
        ),

        # Índices para el modelo Calibracion
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_calibracion_fecha ON core_calibracion (fecha_calibracion);",
            reverse_sql="DROP INDEX IF EXISTS idx_calibracion_fecha;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_calibracion_equipo_fecha ON core_calibracion (equipo_id, fecha_calibracion DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_calibracion_equipo_fecha;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_calibracion_resultado ON core_calibracion (resultado);",
            reverse_sql="DROP INDEX IF EXISTS idx_calibracion_resultado;"
        ),

        # Índices para el modelo Mantenimiento
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_mantenimiento_fecha ON core_mantenimiento (fecha_mantenimiento);",
            reverse_sql="DROP INDEX IF EXISTS idx_mantenimiento_fecha;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_mantenimiento_equipo_fecha ON core_mantenimiento (equipo_id, fecha_mantenimiento DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_mantenimiento_equipo_fecha;"
        ),

        # Índices para el modelo Comprobacion
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_comprobacion_fecha ON core_comprobacion (fecha_comprobacion);",
            reverse_sql="DROP INDEX IF EXISTS idx_comprobacion_fecha;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_comprobacion_equipo_fecha ON core_comprobacion (equipo_id, fecha_comprobacion DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_comprobacion_equipo_fecha;"
        ),

        # Índices para el modelo Empresa
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_empresa_estado_suscripcion ON core_empresa (estado_suscripcion);",
            reverse_sql="DROP INDEX IF EXISTS idx_empresa_estado_suscripcion;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_empresa_fecha_inicio ON core_empresa (fecha_inicio_plan);",
            reverse_sql="DROP INDEX IF EXISTS idx_empresa_fecha_inicio;"
        ),

        # Índices para CustomUser
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_customuser_empresa ON core_customuser (empresa_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_customuser_empresa;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_customuser_is_active ON core_customuser (is_active);",
            reverse_sql="DROP INDEX IF EXISTS idx_customuser_is_active;"
        ),

        # Índices compuestos para consultas complejas
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_equipo_empresa_proxima_cal ON core_equipo (empresa_id, proxima_calibracion) WHERE estado = 'Activo';",
            reverse_sql="DROP INDEX IF EXISTS idx_equipo_empresa_proxima_cal;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_calibracion_fecha_resultado ON core_calibracion (fecha_calibracion, resultado);",
            reverse_sql="DROP INDEX IF EXISTS idx_calibracion_fecha_resultado;"
        ),
    ]