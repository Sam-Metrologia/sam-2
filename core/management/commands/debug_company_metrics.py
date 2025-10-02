from django.core.management.base import BaseCommand
from core.models import Empresa, Equipo, Calibracion, Mantenimiento, Comprobacion, MetricasEficienciaMetrologica
from datetime import date

class Command(BaseCommand):
    help = 'Debug company metrics calculation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=int,
            help='Debug specific company by ID',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== DEBUG COMPANY METRICS ==='))

        if options['company_id']:
            empresas = Empresa.objects.filter(id=options['company_id'])
        else:
            # Check companies user mentioned: 234 (CERTI) and PRUEBA12 (ALMA)
            empresas = Empresa.objects.filter(nombre__in=['234', 'PRUEBA12'])

        current_year = date.today().year

        for empresa in empresas:
            self.stdout.write(f"\n--- Empresa: {empresa.nombre} (ID: {empresa.id}) ---")

            # Check basic data
            equipos = Equipo.objects.filter(empresa=empresa)
            self.stdout.write(f"Equipos totales: {equipos.count()}")

            # Check activities for current year
            calibraciones = Calibracion.objects.filter(
                equipo__empresa=empresa,
                fecha_calibracion__year=current_year
            )
            mantenimientos = Mantenimiento.objects.filter(
                equipo__empresa=empresa,
                fecha_mantenimiento__year=current_year
            )
            comprobaciones = Comprobacion.objects.filter(
                equipo__empresa=empresa,
                fecha_comprobacion__year=current_year
            )

            self.stdout.write(f"Calibraciones {current_year}: {calibraciones.count()}")
            self.stdout.write(f"Mantenimientos {current_year}: {mantenimientos.count()}")
            self.stdout.write(f"Comprobaciones {current_year}: {comprobaciones.count()}")

            # Check existing metrics
            try:
                metricas = MetricasEficienciaMetrologica.objects.get(empresa=empresa)
                self.stdout.write(f"Métricas existentes:")
                self.stdout.write(f"  - Puntuación general: {metricas.puntuacion_eficiencia_general}")
                self.stdout.write(f"  - Estado: {metricas.estado_eficiencia}")
                self.stdout.write(f"  - Cumplimiento calibraciones: {metricas.cumplimiento_calibraciones}")
                self.stdout.write(f"  - Disponibilidad equipos: {metricas.disponibilidad_equipos}")
            except MetricasEficienciaMetrologica.DoesNotExist:
                self.stdout.write("Sin métricas existentes")

            # Manually try to calculate basic metrics
            if equipos.count() > 0:
                equipos_disponibles = equipos.exclude(estado__in=['Fuera de Servicio', 'De Baja']).count()
                disponibilidad = (equipos_disponibles / equipos.count()) * 100
                self.stdout.write(f"Disponibilidad calculada manualmente: {disponibilidad}%")

                # Try to create/update metrics
                from core.views.dashboard_gerencia_simple import calcular_metricas_eficiencia
                self.stdout.write("Intentando calcular métricas...")

                try:
                    metricas_calculadas = calcular_metricas_eficiencia(empresa)
                    if metricas_calculadas:
                        self.stdout.write(f"✅ Métricas calculadas exitosamente:")
                        self.stdout.write(f"   Puntuación: {metricas_calculadas.puntuacion_eficiencia_general}")
                        self.stdout.write(f"   Estado: {metricas_calculadas.estado_eficiencia}")
                    else:
                        self.stdout.write("X Error: calcular_metricas_eficiencia retorno None")
                except Exception as e:
                    self.stdout.write(f"X Error calculando metricas: {e}")

            self.stdout.write("-" * 50)

        self.stdout.write(self.style.SUCCESS('\n=== DEBUG COMPLETED ==='))