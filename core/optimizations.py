# core/optimizations.py
# Optimizaciones para queries N+1 y mejoras de performance

from django.db import models
from django.db.models import Count, Prefetch, Q
from datetime import date, timedelta
from .models import Equipo, Calibracion, Mantenimiento, Comprobacion, Empresa
from .constants import ESTADO_ACTIVO, ESTADO_INACTIVO, ESTADO_DE_BAJA


class OptimizedQueries:
    """Clase con queries optimizadas para evitar N+1 y mejorar performance"""

    @staticmethod
    def get_equipos_optimized(empresa=None, user=None):
        """
        Obtiene equipos con todos los relacionados prefetcheados
        para evitar queries N+1. Solo equipos de empresas activas.
        """
        queryset = Equipo.objects.select_related(
            'empresa'
        ).filter(
            empresa__is_deleted=False  # Solo equipos de empresas activas
        ).prefetch_related(
            # Prefetch calibraciones con orden por fecha descendente
            Prefetch(
                'calibraciones',
                queryset=Calibracion.objects.select_related('proveedor').order_by('-fecha_calibracion')
            ),
            # Prefetch mantenimientos con orden por fecha descendente
            Prefetch(
                'mantenimientos',
                queryset=Mantenimiento.objects.select_related('proveedor').order_by('-fecha_mantenimiento')
            ),
            # Prefetch comprobaciones con orden por fecha descendente
            Prefetch(
                'comprobaciones',
                queryset=Comprobacion.objects.select_related('proveedor').order_by('-fecha_comprobacion')
            ),
            'baja_registro'
        )

        # Aplicar filtros según empresa y usuario
        if user and not user.is_superuser:
            if user.empresa:
                queryset = queryset.filter(empresa=user.empresa)
            else:
                queryset = Equipo.objects.none()
        elif empresa:
            queryset = queryset.filter(empresa=empresa)

        return queryset.order_by('codigo_interno')

    @staticmethod
    def get_empresas_with_stats():
        """
        Obtiene empresas activas (no eliminadas) con estadísticas pre-calculadas
        para mejorar performance en dashboard
        """
        return Empresa.objects.filter(is_deleted=False).annotate(
            total_equipos=Count('equipos'),
            equipos_activos=Count('equipos', filter=Q(equipos__estado=ESTADO_ACTIVO)),
            equipos_mantenimiento=Count('equipos', filter=Q(equipos__estado='En Mantenimiento')),
            equipos_baja=Count('equipos', filter=Q(equipos__estado=ESTADO_DE_BAJA))
        ).order_by('nombre')

    @staticmethod
    def get_dashboard_equipos(user, selected_company_id=None):
        """
        Query optimizada para dashboard con todas las estadísticas necesarias.
        Solo equipos de empresas activas.
        """
        base_query = Equipo.objects.select_related('empresa').filter(empresa__is_deleted=False)

        if not user.is_superuser:
            if user.empresa:
                base_query = base_query.filter(empresa=user.empresa)
                selected_company_id = str(user.empresa.id)
            else:
                return Equipo.objects.none(), []

        if selected_company_id:
            try:
                base_query = base_query.filter(empresa_id=selected_company_id)
            except (ValueError, TypeError):
                pass

        return base_query, Empresa.objects.filter(is_deleted=False).order_by('nombre')

    @staticmethod
    def get_equipos_with_activities_count(empresa=None, user=None):
        """
        Obtiene equipos con conteo de actividades para optimizar dashboard.
        Solo equipos de empresas activas.
        """
        queryset = Equipo.objects.select_related('empresa').filter(empresa__is_deleted=False).annotate(
            total_calibraciones=Count('calibraciones'),
            total_mantenimientos=Count('mantenimientos'),
            total_comprobaciones=Count('comprobaciones'),
            # Conteo de actividades este año
            calibraciones_este_ano=Count(
                'calibraciones',
                filter=Q(calibraciones__fecha_calibracion__year=date.today().year)
            ),
            mantenimientos_este_ano=Count(
                'mantenimientos',
                filter=Q(mantenimientos__fecha_mantenimiento__year=date.today().year)
            ),
            comprobaciones_este_ano=Count(
                'comprobaciones',
                filter=Q(comprobaciones__fecha_comprobacion__year=date.today().year)
            )
        )

        # Aplicar filtros
        if user and not user.is_superuser:
            if user.empresa:
                queryset = queryset.filter(empresa=user.empresa)
            else:
                return Equipo.objects.none()
        elif empresa:
            queryset = queryset.filter(empresa=empresa)

        return queryset.order_by('codigo_interno')

    @staticmethod
    def get_proximas_actividades(user, days_ahead=30):
        """
        Obtiene actividades próximas de forma optimizada.
        SOLO incluye actividades futuras (no vencidas).
        """
        today = date.today()
        fecha_limite = today + timedelta(days=days_ahead)

        base_query = Equipo.objects.select_related('empresa').filter(
            empresa__is_deleted=False  # Solo equipos de empresas activas
        ).exclude(
            estado__in=[ESTADO_DE_BAJA, ESTADO_INACTIVO]
        )

        if not user.is_superuser and user.empresa:
            base_query = base_query.filter(empresa=user.empresa)
        elif not user.is_superuser:
            base_query = Equipo.objects.none()

        # Queries optimizadas para cada tipo de actividad
        # IMPORTANTE: proxima_X__gte=today excluye actividades vencidas
        calibraciones_proximas = base_query.filter(
            proxima_calibracion__isnull=False,
            proxima_calibracion__gte=today,  # Solo futuras (no vencidas)
            proxima_calibracion__lte=fecha_limite
        ).order_by('proxima_calibracion')

        mantenimientos_proximos = base_query.filter(
            proximo_mantenimiento__isnull=False,
            proximo_mantenimiento__gte=today,  # Solo futuras (no vencidas)
            proximo_mantenimiento__lte=fecha_limite
        ).order_by('proximo_mantenimiento')

        comprobaciones_proximas = base_query.filter(
            proxima_comprobacion__isnull=False,
            proxima_comprobacion__gte=today,  # Solo futuras (no vencidas)
            proxima_comprobacion__lte=fecha_limite
        ).order_by('proxima_comprobacion')

        return {
            'calibraciones': calibraciones_proximas,
            'mantenimientos': mantenimientos_proximos,
            'comprobaciones': comprobaciones_proximas
        }

    @staticmethod
    def get_empresa_equipment_count(empresa_id):
        """
        Obtiene conteo de equipos de forma optimizada usando cache
        """
        from django.core.cache import cache

        cache_key = f"empresa_equipment_count_{empresa_id}"
        count = cache.get(cache_key)

        if count is None:
            # Solo contar equipos de empresas activas
            count = Equipo.objects.filter(empresa_id=empresa_id, empresa__is_deleted=False).count()
            # Cache por 5 minutos
            cache.set(cache_key, count, 300)

        return count

    @staticmethod
    def invalidate_empresa_cache(empresa_id):
        """
        Invalida cache relacionado con una empresa específica
        """
        from django.core.cache import cache

        cache_keys = [
            f"empresa_equipment_count_{empresa_id}",
            f"storage_usage_empresa_{empresa_id}",
        ]

        cache.delete_many(cache_keys)


class BulkOperations:
    """Operaciones en bulk para mejorar performance"""

    @staticmethod
    def bulk_update_equipment_dates(equipos):
        """
        Actualiza fechas de equipos en bulk
        """
        equipos_to_update = []

        for equipo in equipos:
            equipo.calcular_proxima_calibracion()
            equipo.calcular_proximo_mantenimiento()
            equipo.calcular_proxima_comprobacion()
            equipos_to_update.append(equipo)

        if equipos_to_update:
            Equipo.objects.bulk_update(
                equipos_to_update,
                ['proxima_calibracion', 'proximo_mantenimiento', 'proxima_comprobacion'],
                batch_size=100
            )

    @staticmethod
    def bulk_create_equipos(equipos_data):
        """
        Crea equipos en bulk de forma eficiente
        """
        equipos = [Equipo(**data) for data in equipos_data]

        return Equipo.objects.bulk_create(
            equipos,
            batch_size=100,
            ignore_conflicts=True
        )


class CacheHelpers:
    """Helpers para gestión de cache optimizada"""

    @staticmethod
    def get_cached_empresa_stats(empresa_id, timeout=300):
        """
        Obtiene estadísticas de empresa desde cache
        """
        from django.core.cache import cache

        cache_key = f"empresa_stats_{empresa_id}"
        stats = cache.get(cache_key)

        if stats is None:
            try:
                empresa = Empresa.objects.get(id=empresa_id)
                stats = {
                    'total_equipos': Equipo.objects.filter(empresa=empresa, empresa__is_deleted=False).count(),
                    'equipos_activos': Equipo.objects.filter(empresa=empresa, estado=ESTADO_ACTIVO, empresa__is_deleted=False).count(),
                    'storage_used': empresa.get_total_storage_used_mb(),
                    'storage_limit': empresa.limite_almacenamiento_mb,
                    'equipment_limit': empresa.get_limite_equipos()
                }
                cache.set(cache_key, stats, timeout)
            except Empresa.DoesNotExist:
                stats = {}

        return stats

    @staticmethod
    def invalidate_empresa_stats(empresa_id):
        """
        Invalida estadísticas de empresa en cache
        """
        from django.core.cache import cache
        cache.delete(f"empresa_stats_{empresa_id}")


# Función de utilidad para aplicar optimizaciones a views existentes
def optimize_view_queries(view_func):
    """
    Decorador que se puede aplicar a views para optimizar queries automáticamente
    """
    from functools import wraps

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Aquí se pueden añadir optimizaciones automáticas
        return view_func(request, *args, **kwargs)

    return wrapper