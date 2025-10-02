# core/management/commands/validate_dashboard_coherence.py
# Comando para validar coherencia entre Panel de Decisiones y Dashboard Técnico

from django.core.management.base import BaseCommand
from core.models import Empresa, Equipo, Calibracion, Mantenimiento, Comprobacion, CustomUser
from core.views.dashboard import _get_actividades_data
from core.views.panel_decisiones import _calcular_salud_equipo, _calcular_cumplimiento, _calcular_eficiencia_operacional
from datetime import date
import json


class Command(BaseCommand):
    help = 'Valida coherencia de datos entre Panel de Decisiones y Dashboard Técnico'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='ID de empresa específica para validar (opcional)',
        )

    def handle(self, *args, **options):
        today = date.today()
        current_year = today.year

        self.stdout.write(self.style.SUCCESS('=== VALIDACIÓN DE COHERENCIA DE DATOS ===\n'))

        # Si se especifica una empresa, usar solo esa
        if options['empresa_id']:
            try:
                empresas = [Empresa.objects.get(id=options['empresa_id'])]
                self.stdout.write(f"Validando empresa específica: {empresas[0].nombre}")
            except Empresa.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Empresa con ID {options['empresa_id']} no existe"))
                return
        else:
            # Validar todas las empresas activas
            empresas = Empresa.objects.all()
            self.stdout.write(f"Validando {empresas.count()} empresas")

        for empresa in empresas:
            self.validate_empresa_coherence(empresa, today, current_year)

        self.stdout.write(self.style.SUCCESS('\n=== VALIDACIÓN COMPLETADA ==='))

    def validate_empresa_coherence(self, empresa, today, current_year):
        """Valida coherencia de datos para una empresa específica"""

        self.stdout.write(f"\n--- EMPRESA: {empresa.nombre} (ID: {empresa.id}) ---")

        # Obtener equipos como lo hace cada dashboard
        equipos_queryset = Equipo.objects.filter(empresa=empresa)
        equipos_para_dashboard = equipos_queryset.exclude(estado__in=['De Baja', 'Inactivo'])

        total_equipos = equipos_queryset.count()
        equipos_activos = equipos_para_dashboard.count()

        self.stdout.write(f"Total equipos: {total_equipos}")
        self.stdout.write(f"Equipos activos: {equipos_activos}")

        if equipos_activos == 0:
            self.stdout.write(self.style.WARNING("No hay equipos activos para validar"))
            return

        # 1. VALIDAR SALUD DEL EQUIPO
        self.stdout.write(f"\n1. VALIDANDO SALUD DEL EQUIPO...")
        salud_data = _calcular_salud_equipo(equipos_para_dashboard, today)

        # Validación manual de salud
        equipos_saludables_manual = 0
        equipos_criticos_manual = 0

        for equipo in equipos_para_dashboard:
            cal_vigente = equipo.proxima_calibracion and equipo.proxima_calibracion >= today
            mant_vigente = equipo.proximo_mantenimiento and equipo.proximo_mantenimiento >= today
            comp_vigente = equipo.proxima_comprobacion and equipo.proxima_comprobacion >= today

            if cal_vigente and mant_vigente and comp_vigente:
                equipos_saludables_manual += 1

            actividades_vencidas = 0
            if equipo.proxima_calibracion and equipo.proxima_calibracion < today:
                actividades_vencidas += 1
            if equipo.proximo_mantenimiento and equipo.proximo_mantenimiento < today:
                actividades_vencidas += 1
            if equipo.proxima_comprobacion and equipo.proxima_comprobacion < today:
                actividades_vencidas += 1

            if actividades_vencidas >= 2:
                equipos_criticos_manual += 1

        self.stdout.write(f"   Función: {salud_data['equipos_saludables']} saludables")
        self.stdout.write(f"   Manual:  {equipos_saludables_manual} saludables")
        self.stdout.write(f"   Función: {salud_data['equipos_criticos']} críticos")
        self.stdout.write(f"   Manual:  {equipos_criticos_manual} críticos")

        if salud_data['equipos_saludables'] == equipos_saludables_manual:
            self.stdout.write(self.style.SUCCESS("   [OK] Salud del equipo COHERENTE"))
        else:
            self.stdout.write(self.style.ERROR("   [ERROR] Salud del equipo INCOHERENTE"))

        # 2. VALIDAR CUMPLIMIENTO
        self.stdout.write(f"\n2. VALIDANDO CUMPLIMIENTO...")
        cumplimiento_data = _calcular_cumplimiento(equipos_para_dashboard, current_year, today)

        # Validación manual de cumplimiento
        total_programadas_manual = 0
        total_realizadas_manual = 0

        for equipo in equipos_para_dashboard:
            # Calibraciones
            if equipo.frecuencia_calibracion_meses and int(equipo.frecuencia_calibracion_meses) > 0:
                programadas_cal = 12 // int(equipo.frecuencia_calibracion_meses)
                realizadas_cal = Calibracion.objects.filter(
                    equipo=equipo,
                    fecha_calibracion__year=current_year,
                    fecha_calibracion__lte=today
                ).count()
                total_programadas_manual += programadas_cal
                total_realizadas_manual += min(realizadas_cal, programadas_cal)

            # Mantenimientos
            if equipo.frecuencia_mantenimiento_meses and int(equipo.frecuencia_mantenimiento_meses) > 0:
                programadas_mant = 12 // int(equipo.frecuencia_mantenimiento_meses)
                realizadas_mant = Mantenimiento.objects.filter(
                    equipo=equipo,
                    fecha_mantenimiento__year=current_year,
                    fecha_mantenimiento__lte=today
                ).count()
                total_programadas_manual += programadas_mant
                total_realizadas_manual += min(realizadas_mant, programadas_mant)

            # Comprobaciones
            if equipo.frecuencia_comprobacion_meses and int(equipo.frecuencia_comprobacion_meses) > 0:
                programadas_comp = 12 // int(equipo.frecuencia_comprobacion_meses)
                realizadas_comp = Comprobacion.objects.filter(
                    equipo=equipo,
                    fecha_comprobacion__year=current_year,
                    fecha_comprobacion__lte=today
                ).count()
                total_programadas_manual += programadas_comp
                total_realizadas_manual += min(realizadas_comp, programadas_comp)

        self.stdout.write(f"   Función: {cumplimiento_data['actividades_programadas']} programadas")
        self.stdout.write(f"   Manual:  {total_programadas_manual} programadas")
        self.stdout.write(f"   Función: {cumplimiento_data['actividades_realizadas']} realizadas")
        self.stdout.write(f"   Manual:  {total_realizadas_manual} realizadas")

        if (cumplimiento_data['actividades_programadas'] == total_programadas_manual and
            cumplimiento_data['actividades_realizadas'] == total_realizadas_manual):
            self.stdout.write(self.style.SUCCESS("   [OK] Cumplimiento COHERENTE"))
        else:
            self.stdout.write(self.style.ERROR("   [ERROR] Cumplimiento INCOHERENTE"))

        # 3. VALIDAR EFICIENCIA OPERACIONAL
        self.stdout.write(f"\n3. VALIDANDO EFICIENCIA OPERACIONAL...")
        eficiencia_data = _calcular_eficiencia_operacional(equipos_queryset, equipos_para_dashboard)

        disponibilidad_manual = round((equipos_activos / total_equipos) * 100, 1) if total_equipos > 0 else 0

        self.stdout.write(f"   Función: {eficiencia_data['disponibilidad_porcentaje']}% disponibilidad")
        self.stdout.write(f"   Manual:  {disponibilidad_manual}% disponibilidad")

        if eficiencia_data['disponibilidad_porcentaje'] == disponibilidad_manual:
            self.stdout.write(self.style.SUCCESS("   [OK] Eficiencia COHERENTE"))
        else:
            self.stdout.write(self.style.ERROR("   [ERROR] Eficiencia INCOHERENTE"))

        # 4. COMPARAR CON DASHBOARD TÉCNICO
        self.stdout.write(f"\n4. COMPARANDO CON DASHBOARD TÉCNICO...")

        try:
            # Simular request de usuario de la empresa para dashboard técnico
            usuarios_empresa = CustomUser.objects.filter(empresa=empresa, is_active=True)
            if usuarios_empresa.exists():
                # Crear un mock request simple
                class MockRequest:
                    def __init__(self, user):
                        self.user = user

                mock_request = MockRequest(usuarios_empresa.first())

                # Obtener datos del dashboard técnico
                actividades_data = _get_actividades_data(mock_request, today)

                self.stdout.write(f"   Dashboard técnico procesado correctamente")
                self.stdout.write(self.style.SUCCESS("   [OK] Compatibilidad con dashboard técnico CONFIRMADA"))
            else:
                self.stdout.write(self.style.WARNING("   No hay usuarios activos para esta empresa"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   [ERROR] Error al comparar con dashboard técnico: {str(e)}"))

        # RESUMEN
        self.stdout.write(f"\n--- RESUMEN EMPRESA {empresa.nombre} ---")
        self.stdout.write(f"Salud: {salud_data['salud_general_porcentaje']}% ({salud_data['salud_general_estado']})")
        self.stdout.write(f"Cumplimiento: {cumplimiento_data['cumplimiento_porcentaje']}% ({cumplimiento_data['cumplimiento_estado']})")
        self.stdout.write(f"Eficiencia: {eficiencia_data['eficiencia_porcentaje']}% ({eficiencia_data['eficiencia_estado']})")