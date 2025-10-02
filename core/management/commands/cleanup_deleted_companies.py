# core/management/commands/cleanup_deleted_companies.py

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from core.models import Empresa
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '''
    Limpia empresas eliminadas que han excedido el período de retención (6 meses).

    Uso:
    python manage.py cleanup_deleted_companies                # Simulación (dry-run)
    python manage.py cleanup_deleted_companies --execute      # Ejecución real
    python manage.py cleanup_deleted_companies --days=90      # Personalizar días (por defecto 180)
    '''

    def add_arguments(self, parser):
        parser.add_argument(
            '--execute',
            action='store_true',
            dest='execute',
            default=False,
            help='Ejecuta la limpieza real. Sin esta opción, solo muestra qué se eliminaría (dry-run).'
        )

        parser.add_argument(
            '--days',
            type=int,
            dest='days',
            default=180,
            help='Número de días después de los cuales eliminar permanentemente (por defecto: 180 días = 6 meses).'
        )

        parser.add_argument(
            '--company-id',
            type=int,
            dest='company_id',
            help='ID específico de empresa para procesar (opcional).'
        )

    def handle(self, *args, **options):
        execute = options['execute']
        retention_days = options['days']
        company_id = options.get('company_id')

        # Mostrar configuración
        self.stdout.write(self.style.HTTP_INFO('=== LIMPIEZA DE EMPRESAS ELIMINADAS ==='))
        self.stdout.write(f'Período de retención: {retention_days} días')
        self.stdout.write(f'Modo: {"EJECUCIÓN REAL" if execute else "SIMULACIÓN (dry-run)"}')
        self.stdout.write(f'Fecha actual: {timezone.now().strftime("%d/%m/%Y %H:%M")}')
        self.stdout.write('')

        try:
            if company_id:
                # Procesar empresa específica
                self._process_specific_company(company_id, execute, retention_days)
            else:
                # Procesar todas las empresas elegibles
                self._process_all_companies(execute, retention_days)

        except Exception as e:
            raise CommandError(f'Error durante la limpieza: {e}')

    def _process_specific_company(self, company_id, execute, retention_days):
        """Procesa una empresa específica."""
        try:
            empresa = Empresa.objects.get(id=company_id, is_deleted=True)
        except Empresa.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Empresa con ID {company_id} no encontrada o no está eliminada.'))
            return

        days_deleted = (timezone.now() - empresa.deleted_at).days if empresa.deleted_at else 0

        self.stdout.write(f'Empresa encontrada: {empresa.nombre}')
        self.stdout.write(f'Eliminada el: {empresa.deleted_at.strftime("%d/%m/%Y %H:%M") if empresa.deleted_at else "Fecha desconocida"}')
        self.stdout.write(f'Días desde eliminación: {days_deleted}')

        if days_deleted >= retention_days:
            if execute:
                empresa.delete()
                self.stdout.write(self.style.SUCCESS(f'OK - Empresa {empresa.nombre} eliminada permanentemente.'))
                logger.info(f'Empresa {empresa.nombre} (ID:{company_id}) eliminada permanentemente por comando manual')
            else:
                self.stdout.write(self.style.WARNING(f'ADVERTENCIA - Empresa {empresa.nombre} SERIA eliminada permanentemente.'))
        else:
            remaining_days = retention_days - days_deleted
            self.stdout.write(self.style.HTTP_INFO(f'INFO - Empresa {empresa.nombre} sera eliminada en {remaining_days} dias.'))

    def _process_all_companies(self, execute, retention_days):
        """Procesa todas las empresas elegibles para eliminación."""
        # Obtener empresas eliminadas hace más del período especificado
        cutoff_date = timezone.now() - timezone.timedelta(days=retention_days)
        companies_to_process = Empresa.objects.filter(
            is_deleted=True,
            deleted_at__lte=cutoff_date
        ).order_by('deleted_at')

        total_companies = companies_to_process.count()

        if total_companies == 0:
            self.stdout.write(self.style.SUCCESS('OK - No hay empresas para eliminar permanentemente.'))

            # Mostrar empresas eliminadas que aún están en período de retención
            pending_companies = Empresa.objects.filter(is_deleted=True, deleted_at__gt=cutoff_date)
            if pending_companies.exists():
                self.stdout.write('')
                self.stdout.write(self.style.HTTP_INFO('Empresas eliminadas en período de retención:'))
                for empresa in pending_companies.order_by('deleted_at'):
                    days_deleted = (timezone.now() - empresa.deleted_at).days
                    remaining_days = retention_days - days_deleted
                    self.stdout.write(f'  • {empresa.nombre} - {remaining_days} días restantes')
            return

        self.stdout.write(f'Empresas encontradas para eliminación permanente: {total_companies}')
        self.stdout.write('')

        deleted_count = 0
        error_count = 0

        for empresa in companies_to_process:
            days_deleted = (timezone.now() - empresa.deleted_at).days if empresa.deleted_at else 0

            self.stdout.write(f'Procesando: {empresa.nombre}')
            self.stdout.write(f'  • ID: {empresa.id}')
            self.stdout.write(f'  • Eliminada el: {empresa.deleted_at.strftime("%d/%m/%Y %H:%M") if empresa.deleted_at else "Fecha desconocida"}')
            self.stdout.write(f'  • Días desde eliminación: {days_deleted}')
            self.stdout.write(f'  • Eliminada por: {empresa.deleted_by.username if empresa.deleted_by else "Sistema"}')
            self.stdout.write(f'  • Razón: {empresa.delete_reason or "Sin razón especificada"}')

            if execute:
                try:
                    empresa_nombre = empresa.nombre
                    empresa.delete()
                    self.stdout.write(self.style.SUCCESS(f'  OK - Eliminada permanentemente'))
                    logger.info(f'Empresa {empresa_nombre} eliminada permanentemente por comando automático')
                    deleted_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ERROR: {e}'))
                    logger.error(f'Error eliminando permanentemente empresa {empresa.nombre}: {e}')
                    error_count += 1
            else:
                self.stdout.write(self.style.WARNING(f'  ADVERTENCIA - SERIA eliminada permanentemente'))

            self.stdout.write('')

        # Resumen final
        self.stdout.write('=== RESUMEN ===')
        if execute:
            self.stdout.write(self.style.SUCCESS(f'OK - Empresas eliminadas permanentemente: {deleted_count}'))
            if error_count > 0:
                self.stdout.write(self.style.ERROR(f'ERRORES: {error_count}'))
        else:
            self.stdout.write(self.style.WARNING(f'ADVERTENCIA - Empresas que SERIAN eliminadas: {total_companies}'))
            self.stdout.write('')
            self.stdout.write(self.style.HTTP_INFO('Para ejecutar la eliminacion real, use: --execute'))