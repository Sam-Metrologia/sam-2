# Generated manually for cache table creation

from django.db import migrations, connection
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


def create_cache_table(apps, schema_editor):
    """Crear tabla de cache de Django con verificación."""
    try:
        # Verificar si la tabla ya existe
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'sam_cache_table'
                );
            """)
            table_exists = cursor.fetchone()[0]

        if table_exists:
            print("ℹ️  Tabla de cache 'sam_cache_table' ya existe - saltando creación")
            return

        # Crear la tabla si no existe
        call_command('createcachetable', 'sam_cache_table', verbosity=1)
        print("✅ Tabla de cache 'sam_cache_table' creada exitosamente")

        # Verificar que se creó correctamente
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'sam_cache_table'
                );
            """)
            table_created = cursor.fetchone()[0]

        if table_created:
            print("✅ Verificación: Tabla de cache creada y confirmada")
        else:
            print("❌ Error: Tabla de cache no se pudo verificar después de creación")

    except Exception as e:
        logger.error(f"Error en migración de cache: {e}")
        print(f"⚠️  Error creando tabla de cache: {e}")
        # No fallar la migración por esto
        pass


def delete_cache_table(apps, schema_editor):
    """Eliminar tabla de cache (rollback)."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS sam_cache_table;")
        print("🗑️  Tabla de cache 'sam_cache_table' eliminada")
    except Exception as e:
        logger.warning(f"Error eliminando tabla de cache: {e}")
        print(f"⚠️  Error eliminando tabla de cache: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_alter_empresa_limite_almacenamiento_mb'),
    ]

    operations = [
        migrations.RunPython(
            create_cache_table,
            delete_cache_table,
        ),
    ]