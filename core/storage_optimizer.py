# core/storage_optimizer.py
# Optimizaciones avanzadas para cálculo de almacenamiento

from django.core.files.storage import default_storage
from django.core.cache import cache
from django.db import models, connection
from django.utils import timezone
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class StorageCalculator:
    """
    Calculador de almacenamiento optimizado que evita iteraciones N+1
    y utiliza cálculos paralelos y cache inteligente
    """

    def __init__(self, empresa):
        self.empresa = empresa
        self.cache_timeout = 1800  # 30 minutos

    def get_total_storage_used_mb(self) -> float:
        """
        Calcula el uso total de almacenamiento de forma optimizada
        """
        # Cache key con información de invalidación
        cache_key, cache_version = self._get_cache_key()

        # Intentar obtener del cache
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result

        # Calcular usando métodos optimizados
        total_mb = self._calculate_storage_optimized()

        # Guardar en cache
        self._save_to_cache(cache_key, total_mb)

        return total_mb

    def _get_cache_key(self) -> tuple:
        """
        Genera clave de cache con información para invalidación automática
        """
        # Usar timestamp de última modificación para invalidación automática
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT MAX(COALESCE(
                    core_equipo.fecha_registro,
                    core_calibracion.fecha_registro,
                    core_mantenimiento.fecha_registro,
                    core_comprobacion.fecha_registro
                )) as last_modified
                FROM core_empresa
                LEFT JOIN core_equipo ON core_empresa.id = core_equipo.empresa_id
                LEFT JOIN core_calibracion ON core_equipo.id = core_calibracion.equipo_id
                LEFT JOIN core_mantenimiento ON core_equipo.id = core_mantenimiento.equipo_id
                LEFT JOIN core_comprobacion ON core_equipo.id = core_comprobacion.equipo_id
                WHERE core_empresa.id = %s
            """, [self.empresa.id])

            result = cursor.fetchone()
            last_modified = result[0] if result and result[0] else timezone.now()

        cache_version = int(last_modified.timestamp()) if last_modified else 0
        cache_key = f"storage_usage_empresa_{self.empresa.id}_v4_{cache_version}"

        return cache_key, cache_version

    def _get_from_cache(self, cache_key: str) -> Optional[float]:
        """
        Obtiene resultado del cache de forma segura
        """
        try:
            return cache.get(cache_key)
        except Exception as e:
            logger.warning(f"Error accediendo al cache para storage calculation: {e}")
            return None

    def _save_to_cache(self, cache_key: str, value: float) -> None:
        """
        Guarda resultado en cache de forma segura
        """
        try:
            cache.set(cache_key, value, self.cache_timeout)
        except Exception as e:
            logger.warning(f"Error guardando en cache para storage calculation: {e}")

    def _calculate_storage_optimized(self) -> float:
        """
        Calcula el almacenamiento usando métodos optimizados
        """
        total_bytes = 0

        # Logo de empresa
        total_bytes += self._calculate_empresa_files()

        # Archivos de equipos usando SQL optimizado
        total_bytes += self._calculate_equipment_files_sql()

        # Convertir a MB
        return round(total_bytes / (1024 * 1024), 2)

    def _calculate_empresa_files(self) -> int:
        """
        Calcula tamaño de archivos de empresa
        """
        size = 0
        if self.empresa.logo_empresa:
            size += self._get_file_size_safe(self.empresa.logo_empresa)
        return size

    def _calculate_equipment_files_sql(self) -> int:
        """
        Calcula archivos de equipos usando SQL optimizado para evitar N+1
        """
        # Obtener todos los paths de archivos en una sola consulta SQL
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT file_path
                FROM (
                    -- Archivos de equipos
                    SELECT archivo_compra_pdf as file_path FROM core_equipo WHERE empresa_id = %s AND archivo_compra_pdf != ''
                    UNION ALL
                    SELECT ficha_tecnica_pdf FROM core_equipo WHERE empresa_id = %s AND ficha_tecnica_pdf != ''
                    UNION ALL
                    SELECT manual_pdf FROM core_equipo WHERE empresa_id = %s AND manual_pdf != ''
                    UNION ALL
                    SELECT otros_documentos_pdf FROM core_equipo WHERE empresa_id = %s AND otros_documentos_pdf != ''
                    UNION ALL
                    SELECT imagen_equipo FROM core_equipo WHERE empresa_id = %s AND imagen_equipo != ''

                    -- Archivos de calibraciones
                    UNION ALL
                    SELECT c.documento_calibracion
                    FROM core_calibracion c
                    INNER JOIN core_equipo e ON c.equipo_id = e.id
                    WHERE e.empresa_id = %s AND c.documento_calibracion != ''

                    UNION ALL
                    SELECT c.confirmacion_metrologica_pdf
                    FROM core_calibracion c
                    INNER JOIN core_equipo e ON c.equipo_id = e.id
                    WHERE e.empresa_id = %s AND c.confirmacion_metrologica_pdf != ''

                    UNION ALL
                    SELECT c.intervalos_calibracion_pdf
                    FROM core_calibracion c
                    INNER JOIN core_equipo e ON c.equipo_id = e.id
                    WHERE e.empresa_id = %s AND c.intervalos_calibracion_pdf != ''

                    -- Archivos de mantenimientos
                    UNION ALL
                    SELECT m.documento_mantenimiento
                    FROM core_mantenimiento m
                    INNER JOIN core_equipo e ON m.equipo_id = e.id
                    WHERE e.empresa_id = %s AND m.documento_mantenimiento != ''

                    UNION ALL
                    SELECT m.archivo_mantenimiento
                    FROM core_mantenimiento m
                    INNER JOIN core_equipo e ON m.equipo_id = e.id
                    WHERE e.empresa_id = %s AND m.archivo_mantenimiento != ''

                    -- Archivos de comprobaciones
                    UNION ALL
                    SELECT co.documento_comprobacion
                    FROM core_comprobacion co
                    INNER JOIN core_equipo e ON co.equipo_id = e.id
                    WHERE e.empresa_id = %s AND co.documento_comprobacion != ''
                ) file_paths
                WHERE file_path IS NOT NULL AND file_path != ''
            """, [self.empresa.id] * 11)

            file_paths = [row[0] for row in cursor.fetchall()]

        # Calcular tamaños usando concurrencia para mejor performance
        return self._calculate_files_concurrent(file_paths)

    def _calculate_files_concurrent(self, file_paths: List[str]) -> int:
        """
        Calcula tamaños de archivos usando threading para mejor performance
        """
        total_size = 0

        # Para muchos archivos, usar threading
        if len(file_paths) > 50:
            total_size = self._calculate_with_threading(file_paths)
        else:
            # Para pocos archivos, cálculo secuencial es más eficiente
            for file_path in file_paths:
                total_size += self._get_file_size_by_path(file_path)

        return total_size

    def _calculate_with_threading(self, file_paths: List[str]) -> int:
        """
        Cálculo con threading para archivos grandes
        """
        total_size = 0
        max_workers = min(10, len(file_paths))  # Límite de workers

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Crear tasks para cada archivo
                future_to_path = {
                    executor.submit(self._get_file_size_by_path, path): path
                    for path in file_paths
                }

                # Recoger resultados
                for future in as_completed(future_to_path):
                    try:
                        size = future.result(timeout=5)  # Timeout de 5 segundos por archivo
                        total_size += size
                    except Exception as e:
                        path = future_to_path[future]
                        logger.warning(f"Error calculando tamaño de archivo {path}: {e}")

        except Exception as e:
            logger.error(f"Error en cálculo concurrente de archivos: {e}")
            # Fallback a cálculo secuencial
            for path in file_paths:
                total_size += self._get_file_size_by_path(path)

        return total_size

    def _get_file_size_safe(self, file_field) -> int:
        """
        Obtiene tamaño de archivo de forma segura desde field
        """
        if not file_field or not hasattr(file_field, 'name') or not file_field.name:
            return 0

        return self._get_file_size_by_path(file_field.name)

    def _get_file_size_by_path(self, file_path: str) -> int:
        """
        Obtiene tamaño de archivo por path de forma segura
        """
        if not file_path:
            return 0

        try:
            if default_storage.exists(file_path):
                return default_storage.size(file_path)
        except Exception as e:
            logger.debug(f"Error obteniendo tamaño de archivo {file_path}: {e}")

        return 0

    @classmethod
    def invalidate_cache(cls, empresa_id: int) -> None:
        """
        Invalida cache de almacenamiento para una empresa
        """
        try:
            # Patrón para eliminar todas las versiones de cache de esta empresa
            cache_pattern = f"storage_usage_empresa_{empresa_id}_v*"

            # Django no tiene delete_pattern nativo, así que usamos un approach diferente
            # En su lugar, almacenamos una clave de invalidación
            invalidation_key = f"storage_invalidated_empresa_{empresa_id}"
            cache.set(invalidation_key, timezone.now().timestamp(), 7200)  # 2 horas

        except Exception as e:
            logger.warning(f"Error invalidando cache de storage para empresa {empresa_id}: {e}")


# Patch para el modelo Empresa
def get_total_storage_used_mb_optimized(self):
    """
    Versión optimizada del método get_total_storage_used_mb
    """
    calculator = StorageCalculator(self)
    return calculator.get_total_storage_used_mb()


# Función para aplicar el patch
def apply_storage_optimization():
    """
    Aplica la optimización al modelo Empresa
    """
    from .models import Empresa

    # Backup del método original
    if not hasattr(Empresa, '_original_get_total_storage_used_mb'):
        Empresa._original_get_total_storage_used_mb = Empresa.get_total_storage_used_mb

    # Aplicar el método optimizado
    Empresa.get_total_storage_used_mb = get_total_storage_used_mb_optimized


# Función para revertir la optimización
def revert_storage_optimization():
    """
    Revierte la optimización del modelo Empresa
    """
    from .models import Empresa

    if hasattr(Empresa, '_original_get_total_storage_used_mb'):
        Empresa.get_total_storage_used_mb = Empresa._original_get_total_storage_used_mb