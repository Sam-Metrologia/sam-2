"""
Comando para limpiar todos los datos de prueba de la base de datos.
Mantiene solo los grupos de usuarios para empezar con datos reales.

Uso:
    python manage.py limpiar_datos_prueba

Para ejecutar sin confirmación:
    python manage.py limpiar_datos_prueba --no-confirm
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.db import transaction
from core.models import (
    Empresa, CustomUser, Equipo, Calibracion, Mantenimiento,
    Comprobacion, ZipRequest
)
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Limpia todos los datos de prueba manteniendo solo grupos de usuarios'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-confirm',
            action='store_true',
            help='Ejecutar sin solicitar confirmación'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué datos serían eliminados sin hacer cambios'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        no_confirm = options['no_confirm']

        self.stdout.write(
            self.style.WARNING('[ADVERTENCIA] Este comando eliminará TODOS los datos de prueba')
        )
        self.stdout.write('Se mantendrán únicamente los grupos de usuarios.')

        # Mostrar estadísticas actuales
        stats = self.get_current_stats()
        self.show_stats(stats, "DATOS ACTUALES")

        if not dry_run and not no_confirm:
            confirm = input('\n¿Está seguro de que desea continuar? (escriba "SI" para confirmar): ')
            if confirm != 'SI':
                self.stdout.write(self.style.ERROR('Operación cancelada'))
                return

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS('\n[DRY-RUN] Los datos mostrados arriba serían eliminados')
            )
            return

        # Proceder con la limpieza
        try:
            with transaction.atomic():
                self.clean_data()

            # Mostrar estadísticas finales
            final_stats = self.get_current_stats()
            self.show_stats(final_stats, "DATOS DESPUÉS DE LIMPIEZA")

            self.stdout.write(
                self.style.SUCCESS('\n[EXITO] Limpieza completada exitosamente')
            )
            self.stdout.write(
                'La base de datos está lista para datos reales de producción.'
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Error durante la limpieza: {e}')
            )
            logger.error(f'Error en limpieza de datos: {e}', exc_info=True)

    def get_current_stats(self):
        """Obtiene estadísticas actuales de la base de datos."""
        return {
            'empresas': Empresa.objects.count(),
            'usuarios': CustomUser.objects.count(),
            'equipos': Equipo.objects.count(),
            'calibraciones': Calibracion.objects.count(),
            'mantenimientos': Mantenimiento.objects.count(),
            'comprobaciones': Comprobacion.objects.count(),
            'zip_requests': ZipRequest.objects.count(),
            'grupos': Group.objects.count(),
        }

    def show_stats(self, stats, title):
        """Muestra estadísticas de datos."""
        self.stdout.write(f'\n[{title}]')
        self.stdout.write(f'- Empresas: {stats["empresas"]}')
        self.stdout.write(f'- Usuarios: {stats["usuarios"]}')
        self.stdout.write(f'- Equipos: {stats["equipos"]}')
        self.stdout.write(f'- Calibraciones: {stats["calibraciones"]}')
        self.stdout.write(f'- Mantenimientos: {stats["mantenimientos"]}')
        self.stdout.write(f'- Comprobaciones: {stats["comprobaciones"]}')
        self.stdout.write(f'- Solicitudes ZIP: {stats["zip_requests"]}')
        self.stdout.write(f'- Grupos (se mantienen): {stats["grupos"]}')

    def clean_data(self):
        """Ejecuta la limpieza de datos en orden correcto."""

        # 1. Eliminar solicitudes ZIP
        zip_count = ZipRequest.objects.count()
        ZipRequest.objects.all().delete()
        self.stdout.write(f'[ELIMINADO] {zip_count} solicitudes ZIP')

        # 2. Eliminar registros de equipos (en orden de dependencias)
        comprobaciones_count = Comprobacion.objects.count()
        Comprobacion.objects.all().delete()
        self.stdout.write(f'[ELIMINADO] {comprobaciones_count} comprobaciones')

        mantenimientos_count = Mantenimiento.objects.count()
        Mantenimiento.objects.all().delete()
        self.stdout.write(f'[ELIMINADO] {mantenimientos_count} mantenimientos')

        calibraciones_count = Calibracion.objects.count()
        Calibracion.objects.all().delete()
        self.stdout.write(f'[ELIMINADO] {calibraciones_count} calibraciones')

        # 3. Eliminar equipos
        equipos_count = Equipo.objects.count()
        Equipo.objects.all().delete()
        self.stdout.write(f'[ELIMINADO] {equipos_count} equipos')

        # 4. Eliminar usuarios (excepto superusuarios)
        usuarios_normales = CustomUser.objects.filter(is_superuser=False)
        usuarios_count = usuarios_normales.count()
        usuarios_normales.delete()
        self.stdout.write(f'[ELIMINADO] {usuarios_count} usuarios normales')

        superusers_count = CustomUser.objects.filter(is_superuser=True).count()
        self.stdout.write(f'[MANTENIDO] {superusers_count} superusuarios')

        # 5. Eliminar empresas
        empresas_count = Empresa.objects.count()
        Empresa.objects.all().delete()
        self.stdout.write(f'[ELIMINADO] {empresas_count} empresas')

        # 6. Los grupos se mantienen automáticamente
        grupos_count = Group.objects.count()
        self.stdout.write(f'[MANTENIDO] {grupos_count} grupos de usuarios')

        logger.info('Limpieza de datos de prueba completada exitosamente')