# Generated manually for cache table creation

from django.db import migrations
from django.core.management import call_command


def create_cache_table(apps, schema_editor):
    """Crear tabla de cache de Django."""
    try:
        call_command('createcachetable', 'sam_cache_table', verbosity=0)
        print("✅ Tabla de cache 'sam_cache_table' creada exitosamente")
    except Exception as e:
        print(f"⚠️  Error creando tabla de cache (puede que ya exista): {e}")


def delete_cache_table(apps, schema_editor):
    """Eliminar tabla de cache (rollback)."""
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS sam_cache_table;")
        print("🗑️  Tabla de cache 'sam_cache_table' eliminada")
    except Exception as e:
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