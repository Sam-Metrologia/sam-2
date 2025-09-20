# core/management/commands/test_storage_limits.py
# Comando para probar que las restricciones de límites funcionan correctamente

from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from core.models import Empresa, Equipo
from core.storage_validators import StorageLimitValidator


class Command(BaseCommand):
    help = 'Prueba las restricciones de límites de almacenamiento y equipos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='ID de la empresa a probar (opcional)'
        )

    def handle(self, *args, **options):
        empresa_id = options.get('empresa_id')

        if empresa_id:
            try:
                empresa = Empresa.objects.get(id=empresa_id)
                empresas_a_probar = [empresa]
            except Empresa.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Empresa con ID {empresa_id} no encontrada.')
                )
                return
        else:
            empresas_a_probar = Empresa.objects.all()

        self.stdout.write(
            self.style.SUCCESS('\n[INICIO] Prueba de restricciones de limites\n')
        )

        for empresa in empresas_a_probar:
            self.stdout.write(f'\n--- Probando empresa: {empresa.nombre} ---')

            # Probar límites de almacenamiento
            self._test_storage_limits(empresa)

            # Probar límites de equipos
            self._test_equipment_limits(empresa)

        self.stdout.write(
            self.style.SUCCESS('\n[FIN] Prueba de restricciones completada\n')
        )

    def _test_storage_limits(self, empresa):
        """Prueba los límites de almacenamiento."""
        self.stdout.write('\n  [STORAGE] Probando limites de almacenamiento...')

        # Obtener resumen actual
        resumen = StorageLimitValidator.get_storage_summary(empresa)

        self.stdout.write(f'    Limite: {resumen["limite_mb"]} MB')
        self.stdout.write(f'    Uso actual: {resumen["uso_mb"]} MB')
        self.stdout.write(f'    Porcentaje: {resumen["porcentaje"]}%')
        self.stdout.write(f'    Estado: {resumen["estado"]} - {resumen["mensaje"]}')
        self.stdout.write(f'    Disponible: {resumen["disponible_mb"]} MB')

        # Probar diferentes tamaños de archivo
        tamanos_prueba = [
            1 * 1024 * 1024,    # 1MB
            10 * 1024 * 1024,   # 10MB
            50 * 1024 * 1024,   # 50MB
            100 * 1024 * 1024,  # 100MB
        ]

        for tamano in tamanos_prueba:
            tamano_mb = tamano / (1024 * 1024)
            try:
                StorageLimitValidator.validate_storage_limit(empresa, tamano)
                self.stdout.write(
                    self.style.SUCCESS(f'    [OK] Archivo de {tamano_mb}MB permitido')
                )
            except ValidationError as e:
                self.stdout.write(
                    self.style.WARNING(f'    [BLOQUEADO] Archivo de {tamano_mb}MB: {str(e)[:80]}...')
                )

    def _test_equipment_limits(self, empresa):
        """Prueba los límites de equipos."""
        self.stdout.write('\n  [EQUIPOS] Probando limites de equipos...')

        # Obtener información actual
        limite_equipos = empresa.get_limite_equipos()
        equipos_actuales = Equipo.objects.filter(empresa=empresa).count()

        self.stdout.write(f'    Limite: {limite_equipos}')
        self.stdout.write(f'    Equipos actuales: {equipos_actuales}')

        if limite_equipos == float('inf'):
            self.stdout.write(
                self.style.SUCCESS('    [OK] Limite infinito - sin restricciones')
            )
        else:
            try:
                StorageLimitValidator.validate_equipment_limit(empresa)
                restantes = limite_equipos - equipos_actuales
                self.stdout.write(
                    self.style.SUCCESS(f'    [OK] Puede crear {restantes} equipos mas')
                )
            except ValidationError as e:
                self.stdout.write(
                    self.style.WARNING(f'    [BLOQUEADO] {str(e)[:80]}...')
                )

        # Mostrar estado de suscripción
        estado_suscripcion = empresa.get_estado_suscripcion_display()
        self.stdout.write(f'    Estado suscripcion: {estado_suscripcion}')

        if empresa.es_periodo_prueba:
            fecha_fin = empresa.get_fecha_fin_plan()
            self.stdout.write(f'    Periodo de prueba hasta: {fecha_fin}')

        if empresa.acceso_manual_activo:
            self.stdout.write('    [INFO] Acceso manual activo - limites extendidos')

    def _test_storage_edge_cases(self, empresa):
        """Prueba casos extremos de almacenamiento."""
        self.stdout.write('\n  [EDGE CASES] Probando casos extremos...')

        # Caso 1: Archivo exactamente en el límite
        disponible = StorageLimitValidator.get_storage_summary(empresa)['disponible_mb']
        if disponible > 0:
            tamano_limite = int(disponible * 1024 * 1024)
            try:
                StorageLimitValidator.validate_storage_limit(empresa, tamano_limite)
                self.stdout.write(
                    self.style.SUCCESS(f'    [OK] Archivo exacto al limite ({disponible}MB)')
                )
            except ValidationError:
                self.stdout.write(
                    self.style.ERROR(f'    [ERROR] Archivo exacto al limite deberia ser valido')
                )

        # Caso 2: Archivo 1 byte sobre el límite
        if disponible > 0:
            tamano_exceso = int(disponible * 1024 * 1024) + 1
            try:
                StorageLimitValidator.validate_storage_limit(empresa, tamano_exceso)
                self.stdout.write(
                    self.style.ERROR(f'    [ERROR] Archivo sobre limite deberia ser bloqueado')
                )
            except ValidationError:
                self.stdout.write(
                    self.style.SUCCESS(f'    [OK] Archivo sobre limite correctamente bloqueado')
                )