# Generated to force cache table creation - Timestamp: 2025-09-19

from django.db import migrations, connection
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


def force_create_cache_table(apps, schema_editor):
    """Forzar creación de tabla de cache."""
    logger.info("FORZANDO CREACION DE TABLA DE CACHE...")

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

        logger.info(f"Estado actual: Tabla existe = {table_exists}")

        if not table_exists:
            logger.info("Creando tabla de cache...")
            call_command('createcachetable', 'sam_cache_table', verbosity=2)
            logger.info("Comando createcachetable ejecutado")

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
                logger.info("TABLA DE CACHE CREADA EXITOSAMENTE!")
            else:
                logger.error("FALLO: Tabla no existe despues de creacion")
        else:
            logger.info("Tabla ya existe - no es necesario crearla")

    except Exception as e:
        logger.error(f"ERROR EN MIGRACION: {e}")


def reverse_force_create_cache_table(apps, schema_editor):
    """Rollback - eliminar tabla de cache."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS sam_cache_table;")
        logger.info("Tabla de cache eliminada (rollback)")
    except Exception as e:
        logger.warning(f"Error en rollback: {e}")


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