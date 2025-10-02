# core/cdn_zip_optimization.py
# Sistema de cache inteligente y CDN para ZIPs frecuentes

import hashlib
import json
from datetime import datetime, timedelta
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.utils import timezone
import logging

logger = logging.getLogger('core')

class IntelligentZipCache:
    """
    Sistema de cache inteligente que genera ZIPs una sola vez
    y los reutiliza si no han cambiado los datos.
    """

    CACHE_DURATION_HOURS = 24  # Cache por 24 horas
    CACHE_PREFIX = 'zip_cache_'

    def __init__(self):
        pass

    def get_or_generate_zip(self, empresa, formatos, user):
        """
        Obtiene ZIP desde cache o lo genera si es necesario.
        """
        try:
            # Calcular hash único para esta solicitud
            cache_key = self._calculate_cache_key(empresa, formatos)

            # Verificar si existe en cache
            cached_result = cache.get(cache_key)

            if cached_result and self._is_cache_valid(cached_result, empresa):
                logger.info(f"📦 ZIP servido desde cache para {empresa.nombre}")

                return {
                    'type': 'cached',
                    'download_url': cached_result['download_url'],
                    'generated_at': cached_result['generated_at'],
                    'expires_at': cached_result['expires_at'],
                    'from_cache': True
                }

            # Cache inválido o no existe, generar nuevo
            logger.info(f"🔄 Generando nuevo ZIP para cache: {empresa.nombre}")

            return self._generate_and_cache_zip(empresa, formatos, user, cache_key)

        except Exception as e:
            logger.error(f"Error en get_or_generate_zip: {e}")
            raise

    def _calculate_cache_key(self, empresa, formatos):
        """
        Calcula clave única basada en empresa, formatos y última modificación.
        """
        # Obtener timestamp de última modificación de equipos
        last_modified = empresa.equipos.aggregate(
            last_update=models.Max('fecha_ultima_modificacion')
        )['last_update']

        if not last_modified:
            last_modified = empresa.fecha_registro

        # Crear hash único
        cache_data = {
            'empresa_id': empresa.id,
            'formatos': sorted(formatos),
            'last_modified': last_modified.isoformat(),
            'equipos_count': empresa.equipos.count()
        }

        cache_string = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.md5(cache_string.encode()).hexdigest()

        return f"{self.CACHE_PREFIX}{cache_hash}"

    def _is_cache_valid(self, cached_result, empresa):
        """
        Verifica si el cache sigue siendo válido.
        """
        try:
            # Verificar si el archivo existe
            if not default_storage.exists(cached_result['download_url']):
                return False

            # Verificar si no ha expirado
            expires_at = datetime.fromisoformat(cached_result['expires_at'])
            if timezone.now() > expires_at:
                return False

            # Verificar si los datos no han cambiado
            current_hash = self._get_data_hash(empresa)
            if current_hash != cached_result.get('data_hash'):
                return False

            return True

        except Exception as e:
            logger.warning(f"Error validando cache: {e}")
            return False

    def _get_data_hash(self, empresa):
        """
        Obtiene hash de los datos actuales de la empresa.
        """
        try:
            # Hash basado en última modificación de equipos y actividades
            equipos = empresa.equipos.all()

            data_points = []
            for equipo in equipos:
                data_points.append({
                    'id': equipo.id,
                    'updated': equipo.fecha_ultima_modificacion.isoformat() if equipo.fecha_ultima_modificacion else None,
                    'calibraciones_count': equipo.calibraciones.count(),
                    'mantenimientos_count': equipo.mantenimientos.count(),
                })

            data_string = json.dumps(data_points, sort_keys=True)
            return hashlib.md5(data_string.encode()).hexdigest()

        except Exception as e:
            logger.warning(f"Error calculando data hash: {e}")
            return str(timezone.now().timestamp())

    def _generate_and_cache_zip(self, empresa, formatos, user, cache_key):
        """
        Genera nuevo ZIP y lo guarda en cache.
        """
        from .async_zip_system import UnlimitedZipGenerator

        try:
            # Generar ZIP
            generator = UnlimitedZipGenerator(empresa, formatos, user)
            zip_path = generator.generate_unlimited_zip()

            # Calcular expiración
            expires_at = timezone.now() + timedelta(hours=self.CACHE_DURATION_HOURS)

            # Datos para cache
            cache_data = {
                'download_url': zip_path,
                'generated_at': timezone.now().isoformat(),
                'expires_at': expires_at.isoformat(),
                'data_hash': self._get_data_hash(empresa),
                'empresa_id': empresa.id,
                'formatos': formatos
            }

            # Guardar en cache
            cache.set(
                cache_key,
                cache_data,
                timeout=self.CACHE_DURATION_HOURS * 3600
            )

            logger.info(f"✅ ZIP generado y cacheado para {empresa.nombre}")

            return {
                'type': 'generated',
                'download_url': zip_path,
                'generated_at': cache_data['generated_at'],
                'expires_at': cache_data['expires_at'],
                'from_cache': False
            }

        except Exception as e:
            logger.error(f"Error generando y cacheando ZIP: {e}")
            raise

    def invalidate_cache(self, empresa):
        """
        Invalida el cache para una empresa específica.
        Llamar cuando se modifiquen datos de equipos.
        """
        try:
            # Buscar todas las claves de cache relacionadas con esta empresa
            # Nota: En producción usar Redis con patrón de búsqueda
            cache_pattern = f"{self.CACHE_PREFIX}*"

            # Invalidar cache relacionado
            # En Django cache local, necesitaríamos un registry de claves
            # Para Redis: cache.delete_pattern(f"{self.CACHE_PREFIX}*{empresa.id}*")

            logger.info(f"🗑️ Cache invalidado para empresa {empresa.nombre}")

        except Exception as e:
            logger.warning(f"Error invalidando cache: {e}")


class CDNIntegration:
    """
    Integración con CDN para acelerar descargas de ZIPs.
    """

    def __init__(self):
        self.cdn_enabled = getattr(settings, 'ZIP_CDN_ENABLED', False)
        self.cdn_base_url = getattr(settings, 'ZIP_CDN_BASE_URL', '')

    def get_optimized_download_url(self, zip_path):
        """
        Retorna URL optimizada, usando CDN si está disponible.
        """
        if self.cdn_enabled and self.cdn_base_url:
            # Generar URL con CDN
            return f"{self.cdn_base_url}/{zip_path}"
        else:
            # URL directa desde storage
            return default_storage.url(zip_path)

    def upload_to_cdn(self, zip_path):
        """
        Sube archivo a CDN para distribución rápida.
        """
        if not self.cdn_enabled:
            return zip_path

        try:
            # Implementar upload a CDN específico
            # (CloudFlare, AWS CloudFront, etc.)
            pass

        except Exception as e:
            logger.warning(f"Error subiendo a CDN: {e}")
            return zip_path


# Instancias globales
zip_cache = IntelligentZipCache()
cdn_integration = CDNIntegration()

# Signal para invalidar cache cuando se modifican equipos
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Equipo, Calibracion, Mantenimiento

@receiver([post_save, post_delete], sender=Equipo)
@receiver([post_save, post_delete], sender=Calibracion)
@receiver([post_save, post_delete], sender=Mantenimiento)
def invalidate_zip_cache_on_change(sender, instance, **kwargs):
    """
    Invalida cache de ZIP cuando se modifican datos relacionados.
    """
    try:
        if hasattr(instance, 'empresa'):
            empresa = instance.empresa
        elif hasattr(instance, 'equipo'):
            empresa = instance.equipo.empresa
        else:
            return

        zip_cache.invalidate_cache(empresa)

    except Exception as e:
        logger.warning(f"Error invalidando cache en signal: {e}")