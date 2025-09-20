from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Configura el sistema de cache creando la tabla de cache si no existe'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar recreación de la tabla de cache',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔧 Configurando sistema de cache...'))

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

            if table_exists and not options['force']:
                self.stdout.write(
                    self.style.WARNING('⚠️  La tabla sam_cache_table ya existe. Usa --force para recrearla.')
                )
                return

            if table_exists and options['force']:
                self.stdout.write(self.style.WARNING('🗑️  Eliminando tabla existente...'))
                with connection.cursor() as cursor:
                    cursor.execute("DROP TABLE IF EXISTS sam_cache_table;")

            # Crear la tabla de cache
            self.stdout.write(self.style.SUCCESS('📊 Creando tabla de cache...'))
            call_command('createcachetable', 'sam_cache_table', verbosity=2)

            self.stdout.write(
                self.style.SUCCESS('✅ Sistema de cache configurado correctamente!')
            )

        except Exception as e:
            error_msg = f"❌ Error configurando cache: {e}"
            self.stdout.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            raise