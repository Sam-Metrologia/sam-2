# Generated to force cache table creation - Timestamp: 2025-09-19

from django.db import migrations, connection
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


def force_create_cache_table(apps, schema_editor):
    """Forzar creación de tabla de cache."""
    print("🚀 FORZANDO CREACIÓN DE TABLA DE CACHE...")

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

        print(f"📊 Estado actual: Tabla existe = {table_exists}")

        if not table_exists:
            print("🔨 Creando tabla de cache...")
            call_command('createcachetable', 'sam_cache_table', verbosity=2)
            print("✅ Comando createcachetable ejecutado")

            # Verificar nuevamente
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'sam_cache_table'
                    );
                """)
                table_created = cursor.fetchone()[0]

            if table_created:
                print("🎉 ¡TABLA DE CACHE CREADA EXITOSAMENTE!")
            else:
                print("❌ FALLO: Tabla no existe después de creación")
        else:
            print("ℹ️  Tabla ya existe - no es necesario crearla")

    except Exception as e:
        print(f"💥 ERROR EN MIGRACIÓN: {e}")
        logger.error(f"Error forzando creación de tabla cache: {e}")


def reverse_force_create_cache_table(apps, schema_editor):
    """Rollback - eliminar tabla de cache."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS sam_cache_table;")
        print("🗑️  Tabla de cache eliminada (rollback)")
    except Exception as e:
        print(f"⚠️  Error en rollback: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_create_cache_table'),
    ]

    operations = [
        migrations.RunPython(
            force_create_cache_table,
            reverse_force_create_cache_table,
        ),
    ]