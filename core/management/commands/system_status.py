# core/management/commands/system_status.py
# Comando para obtener estado y métricas del sistema

from django.core.management.base import BaseCommand
from core.monitoring import SystemMonitor, AlertManager
import json
import logging

logger = logging.getLogger('core')

class Command(BaseCommand):
    help = 'Muestra estado y métricas del sistema SAM Metrología'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'table', 'summary'],
            default='summary',
            help='Formato de salida'
        )
        parser.add_argument(
            '--alerts',
            action='store_true',
            help='Mostrar solo alertas del sistema'
        )
        parser.add_argument(
            '--health',
            action='store_true',
            help='Mostrar solo health check'
        )
        parser.add_argument(
            '--performance',
            action='store_true',
            help='Mostrar métricas de performance'
        )

    def handle(self, *args, **options):
        output_format = options['format']
        show_alerts = options['alerts']
        show_health = options['health']
        show_performance = options['performance']

        try:
            if show_alerts:
                self.show_alerts(output_format)
            elif show_health:
                self.show_health(output_format)
            elif show_performance:
                self.show_performance(output_format)
            else:
                self.show_complete_status(output_format)

        except Exception as e:
            logger.error(f'Error in system_status command: {e}')
            self.stdout.write(
                self.style.ERROR(f'❌ Error obteniendo estado del sistema: {e}')
            )

    def show_complete_status(self, output_format):
        """Muestra estado completo del sistema."""
        self.stdout.write(
            self.style.SUCCESS('🔍 ESTADO COMPLETO DEL SISTEMA SAM METROLOGÍA')
        )
        self.stdout.write('=' * 60)

        # Health check
        health_data = SystemMonitor.get_system_health()
        self.display_health_data(health_data, output_format)

        # Alertas
        alerts = AlertManager.check_system_alerts()
        self.display_alerts(alerts, output_format)

        # Performance (básico)
        if output_format != 'summary':
            performance_data = SystemMonitor.get_performance_metrics()
            self.display_performance_data(performance_data, output_format)

    def show_health(self, output_format):
        """Muestra solo health check."""
        self.stdout.write(
            self.style.SUCCESS('💚 HEALTH CHECK - SAM METROLOGÍA')
        )
        self.stdout.write('=' * 40)

        health_data = SystemMonitor.get_system_health()
        self.display_health_data(health_data, output_format)

    def show_alerts(self, output_format):
        """Muestra solo alertas."""
        self.stdout.write(
            self.style.WARNING('🚨 ALERTAS DEL SISTEMA')
        )
        self.stdout.write('=' * 30)

        alerts = AlertManager.check_system_alerts()
        self.display_alerts(alerts, output_format)

    def show_performance(self, output_format):
        """Muestra métricas de performance."""
        self.stdout.write(
            self.style.SUCCESS('⚡ MÉTRICAS DE PERFORMANCE')
        )
        self.stdout.write('=' * 35)

        performance_data = SystemMonitor.get_performance_metrics()
        self.display_performance_data(performance_data, output_format)

    def display_health_data(self, health_data, output_format):
        """Muestra datos de salud del sistema."""
        if output_format == 'json':
            self.stdout.write(json.dumps(health_data, indent=2, ensure_ascii=False))
            return

        status = health_data.get('status', 'unknown')
        if status == 'healthy':
            self.stdout.write(self.style.SUCCESS(f'✅ Estado: {status.upper()}'))
        else:
            self.stdout.write(self.style.ERROR(f'❌ Estado: {status.upper()}'))

        if 'error' in health_data:
            self.stdout.write(self.style.ERROR(f'Error: {health_data["error"]}'))
            return

        metrics = health_data.get('metrics', {})

        # Base de datos
        db_metrics = metrics.get('database', {})
        if db_metrics.get('status') == 'healthy':
            self.stdout.write(f'📊 Base de Datos: ✅ OK ({db_metrics.get("response_time_ms", 0):.1f}ms)')
            self.stdout.write(f'   - Empresas: {db_metrics.get("total_empresas", 0)}')
            self.stdout.write(f'   - Equipos: {db_metrics.get("total_equipos", 0)}')
            self.stdout.write(f'   - Usuarios: {db_metrics.get("total_usuarios", 0)}')
        else:
            self.stdout.write(f'📊 Base de Datos: ❌ ERROR')

        # Cache
        cache_metrics = metrics.get('cache', {})
        if cache_metrics.get('status') == 'healthy':
            self.stdout.write(f'🗄️  Cache: ✅ OK ({cache_metrics.get("response_time_ms", 0):.1f}ms)')
        else:
            self.stdout.write(f'🗄️  Cache: ⚠️  {cache_metrics.get("status", "ERROR").upper()}')

        # Storage
        storage_metrics = metrics.get('storage', {})
        if storage_metrics.get('status') == 'healthy':
            self.stdout.write(f'💾 Almacenamiento: ✅ OK')
            self.stdout.write(f'   - Total usado: {storage_metrics.get("total_storage_mb", 0):.1f} MB')
            self.stdout.write(f'   - Promedio por empresa: {storage_metrics.get("avg_storage_per_empresa_mb", 0):.1f} MB')

        # Métricas de negocio
        business_metrics = metrics.get('business', {})
        if business_metrics:
            empresas = business_metrics.get('empresas', {})
            equipos = business_metrics.get('equipos', {})

            self.stdout.write('\n📈 MÉTRICAS DE NEGOCIO:')
            self.stdout.write(f'   🏢 Empresas: {empresas.get("total", 0)} total ({empresas.get("activas", 0)} activas)')
            self.stdout.write(f'   🔧 Equipos: {equipos.get("total", 0)} total ({equipos.get("activos", 0)} activos)')

            actividades = business_metrics.get('actividades_recientes', {})
            self.stdout.write(f'   📅 Esta semana: {actividades.get("calibraciones_esta_semana", 0)} cal, {actividades.get("mantenimientos_esta_semana", 0)} mant')

            proximas = business_metrics.get('proximas_actividades', {})
            if proximas.get('calibraciones_proxima_semana', 0) > 0 or proximas.get('mantenimientos_proxima_semana', 0) > 0:
                self.stdout.write(f'   ⏰ Próxima semana: {proximas.get("calibraciones_proxima_semana", 0)} cal, {proximas.get("mantenimientos_proxima_semana", 0)} mant')

    def display_alerts(self, alerts, output_format):
        """Muestra alertas del sistema."""
        if output_format == 'json':
            self.stdout.write(json.dumps(alerts, indent=2, ensure_ascii=False))
            return

        if not alerts:
            self.stdout.write(self.style.SUCCESS('✅ No hay alertas activas'))
            return

        self.stdout.write(f'\n🚨 {len(alerts)} ALERTA(S) DETECTADA(S):')

        for alert in alerts:
            severity = alert.get('severity', 'unknown')
            alert_type = alert.get('type', 'unknown')
            message = alert.get('message', 'Sin mensaje')

            if severity == 'high':
                icon = '🔴'
                style = self.style.ERROR
            elif severity == 'medium':
                icon = '🟡'
                style = self.style.WARNING
            else:
                icon = '🔵'
                style = self.style.NOTICE

            self.stdout.write(style(f'{icon} [{severity.upper()}] {message}'))

            # Mostrar detalles si existen
            details = alert.get('details')
            if details and output_format != 'summary':
                if isinstance(details, list):
                    for item in details[:3]:  # Mostrar solo primeros 3
                        if isinstance(item, dict):
                            empresa = item.get('empresa', 'Unknown')
                            if 'percentage' in item:
                                self.stdout.write(f'     - {empresa}: {item["percentage"]:.1f}%')
                            elif 'dias_restantes' in item:
                                self.stdout.write(f'     - {empresa}: {item["dias_restantes"]} días')
                    if len(details) > 3:
                        self.stdout.write(f'     ... y {len(details) - 3} más')

    def display_performance_data(self, performance_data, output_format):
        """Muestra datos de performance."""
        if output_format == 'json':
            self.stdout.write(json.dumps(performance_data, indent=2, ensure_ascii=False))
            return

        if 'error' in performance_data:
            self.stdout.write(self.style.ERROR(f'❌ Error: {performance_data["error"]}'))
            return

        self.stdout.write('\n⚡ MÉTRICAS DE PERFORMANCE:')

        cache_stats = performance_data.get('cache_stats', {})
        if cache_stats:
            self.stdout.write(f'📦 Cache: {cache_stats.get("status", "unknown")}')

        db_stats = performance_data.get('database_stats', {})
        if db_stats and 'table_counts' in db_stats:
            self.stdout.write('🗃️  Tablas principales:')
            for table, count in db_stats['table_counts'].items():
                clean_name = table.replace('core_', '').replace('_', ' ').title()
                self.stdout.write(f'   - {clean_name}: {count}')

        error_rate = performance_data.get('error_rate', {})
        if error_rate:
            self.stdout.write(f'⚠️  Errores: {error_rate.get("status", "Sin datos")}')