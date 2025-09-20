from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Verifica el estado del sistema de cache y crea la tabla si es necesario'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔧 Verificando sistema de cache...'))

        # Verificar si la tabla de cache existe
        try:
            with connection.cursor() as cursor:
                # Para PostgreSQL
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'sam_cache_table'
                    );
                """)
                table_exists = cursor.fetchone()[0]

            if table_exists:
                self.stdout.write(
                    self.style.SUCCESS('✅ Tabla sam_cache_table existe en la base de datos')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('❌ Tabla sam_cache_table NO existe en la base de datos')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error verificando tabla: {e}')
            )
            table_exists = False

        # Verificar si el cache funciona
        try:
            test_key = 'test_cache_key_verification'
            test_value = 'test_cache_value_123'

            # Intentar escribir en cache
            cache.set(test_key, test_value, 60)

            # Intentar leer del cache
            retrieved_value = cache.get(test_key)

            if retrieved_value == test_value:
                self.stdout.write(
                    self.style.SUCCESS('✅ Sistema de cache funciona correctamente')
                )
                # Limpiar el test
                cache.delete(test_key)
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️  Cache no funciona - valor no coincide')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error probando cache: {e}')
            )

        # Si la tabla no existe, crearla
        if not table_exists:
            self.stdout.write(
                self.style.WARNING('🔨 Creando tabla de cache automáticamente...')
            )
            try:
                from django.core.management import call_command
                call_command('createcachetable', 'sam_cache_table', verbosity=1)
                self.stdout.write(
                    self.style.SUCCESS('✅ Tabla de cache creada exitosamente')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error creando tabla de cache: {e}')
                )

        # Resumen final
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN DEL SISTEMA DE CACHE'))
        self.stdout.write('='*50)

        if table_exists:
            self.stdout.write('✅ Tabla de cache: EXISTE')
        else:
            self.stdout.write('❌ Tabla de cache: NO EXISTE')

        self.stdout.write('🎯 Sistema optimizado con fallback graceful')
        self.stdout.write('🔄 Cache funciona automáticamente cuando la tabla existe')