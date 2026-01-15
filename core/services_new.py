# core/services_new.py
# Servicios mejorados con seguridad robusta y control de cuotas

import uuid
import re
import os
import logging
import hashlib
from datetime import datetime
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError
from django.db import transaction
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Sum, Count, Prefetch, Q
from django.db import models
from .models import Equipo, Empresa, Calibracion, Mantenimiento, Comprobacion, Documento
from .security import SecureFileValidator, StorageQuotaManager

logger = logging.getLogger('core')

class SecureFileUploadService:
    """Servicio mejorado para manejo seguro de archivos con validación robusta"""

    def __init__(self):
        self.validator = SecureFileValidator()
        self.quota_manager = StorageQuotaManager()
        self.max_file_size = 10 * 1024 * 1024  # 10MB

    def calculate_file_checksum(self, uploaded_file):
        """Calcula el checksum MD5 de un archivo"""
        uploaded_file.seek(0)
        hash_md5 = hashlib.md5()
        for chunk in iter(lambda: uploaded_file.read(4096), b""):
            hash_md5.update(chunk)
        uploaded_file.seek(0)
        return hash_md5.hexdigest()

    def validate_storage_quota(self, empresa, file_size):
        """Valida que el archivo no exceda la cuota de almacenamiento"""
        if empresa:
            self.quota_manager.check_quota_available(empresa, file_size)
        return True

    def upload_file(self, uploaded_file, folder_path, empresa=None, equipo_codigo=None, user=None):
        """Subida segura de archivos con validación completa y control de cuotas"""
        try:
            # Validar archivo con el nuevo sistema de seguridad
            self.validator.validate_filename(uploaded_file.name)
            self.validator.validate_file_content(uploaded_file)

            # Validar cuota de almacenamiento
            if empresa:
                self.validate_storage_quota(empresa, uploaded_file.size)

            # Generar nombre y ruta seguros
            safe_filename = self.validator.generate_secure_filename(uploaded_file.name)
            full_path = self.validator.generate_secure_path(safe_filename, folder_path, equipo_codigo)

            # Calcular checksum
            checksum = self.calculate_file_checksum(uploaded_file)

            # Subir archivo
            file_path = default_storage.save(full_path, uploaded_file)

            # Verificar que el archivo se subió correctamente
            if not default_storage.exists(file_path):
                raise Exception("El archivo no se guardó correctamente")

            # Crear registro en la base de datos si se proporciona empresa
            documento = None
            if empresa:
                documento = Documento.objects.create(
                    nombre_archivo=uploaded_file.name,
                    archivo_s3_path=file_path,
                    tamaño_archivo=uploaded_file.size,
                    tipo_mime=getattr(uploaded_file, 'content_type', 'application/octet-stream'),
                    checksum_md5=checksum,
                    subido_por=user,
                    empresa=empresa
                )

            logger.info(f"Archivo subido exitosamente: {file_path}", extra={
                'original_name': uploaded_file.name,
                'file_size': uploaded_file.size,
                'file_path': file_path,
                'content_type': getattr(uploaded_file, 'content_type', 'unknown'),
                'empresa_id': empresa.id if empresa else None,
                'checksum': checksum,
                'documento_id': documento.id if documento else None
            })

            return {
                'success': True,
                'file_path': file_path,
                'original_name': uploaded_file.name,
                'size': uploaded_file.size,
                'checksum': checksum,
                'documento': documento,
                'url': default_storage.url(file_path) if hasattr(default_storage, 'url') else None
            }

        except ValidationError as e:
            logger.warning(f"Validación de archivo falló: {str(e)}", extra={
                'uploaded_filename': uploaded_file.name if uploaded_file else 'Unknown',
                'file_size': uploaded_file.size if uploaded_file else 0,
                'empresa_id': empresa.id if empresa else None
            })
            return {
                'success': False,
                'error': str(e),
                'file_path': None
            }
        except Exception as e:
            logger.error(f"Error inesperado al subir archivo: {str(e)}", exc_info=True, extra={
                'uploaded_filename': uploaded_file.name if uploaded_file else 'Unknown',
                'empresa_id': empresa.id if empresa else None
            })
            return {
                'success': False,
                'error': f"Error interno del servidor: {str(e)[:100]}...",
                'file_path': None
            }

    def delete_file(self, file_path, empresa=None):
        """Eliminar archivo de forma segura y actualizar cuotas"""
        try:
            if file_path and default_storage.exists(file_path):
                # Eliminar archivo del storage
                default_storage.delete(file_path)

                # Eliminar registro de la base de datos si existe
                if empresa:
                    Documento.objects.filter(
                        archivo_s3_path=file_path,
                        empresa=empresa
                    ).delete()

                logger.info(f"Archivo eliminado: {file_path}", extra={
                    'empresa_id': empresa.id if empresa else None
                })
                return True
            return False
        except Exception as e:
            logger.error(f"Error al eliminar archivo {file_path}: {str(e)}", extra={
                'empresa_id': empresa.id if empresa else None
            })
            return False

    def get_file_url(self, file_path, expire_seconds=3600):
        """Obtiene URL segura para acceder al archivo"""
        try:
            if file_path and default_storage.exists(file_path):
                # Para S3 con archivos privados, generar URL firmada
                url = default_storage.url(file_path, expire=expire_seconds)
                return url
            return None
        except Exception as e:
            logger.error(f"Error generando URL para archivo {file_path}: {str(e)}")
            return None


class OptimizedEquipmentService:
    """Servicio optimizado para equipos con consultas eficientes"""

    def __init__(self):
        self.file_service = SecureFileUploadService()

    def get_dashboard_data(self, empresa, user):
        """Obtener datos del dashboard con consultas optimizadas"""
        cache_key = f"dashboard_data_{empresa.id}_{user.id}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return cached_data

        try:
            # Consulta optimizada con select_related y prefetch_related
            equipos = Equipo.objects.select_related(
                'empresa'
            ).prefetch_related(
                'calibraciones',
                'mantenimientos',
                'comprobaciones'
            ).filter(empresa=empresa)

            # Estadísticas agregadas en una sola consulta
            stats = equipos.aggregate(
                total_equipos=Count('id'),
                equipos_calibrados=Count('id', filter=models.Q(calibraciones__isnull=False)),
                equipos_mantenimiento=Count('id', filter=models.Q(mantenimientos__isnull=False))
            )

            # Cuota de almacenamiento
            quota_info = self.file_service.quota_manager.get_quota_info(empresa)

            # Próximos vencimientos (calibraciones y mantenimientos)
            proximos_vencimientos = self._get_upcoming_expirations(empresa)

            data = {
                'equipos': list(equipos),
                'stats': stats,
                'quota_info': quota_info,
                'proximos_vencimientos': proximos_vencimientos,
                'timestamp': timezone.now()
            }

            # Cache por 5 minutos
            cache.set(cache_key, data, 300)
            return data

        except Exception as e:
            logger.error(f"Error obteniendo datos del dashboard: {str(e)}", extra={
                'empresa_id': empresa.id,
                'user_id': user.id
            })
            raise

    def _get_upcoming_expirations(self, empresa, days_ahead=30):
        """Obtener próximos vencimientos de calibraciones y mantenimientos"""
        from django.utils import timezone
        from datetime import timedelta

        cutoff_date = timezone.now().date() + timedelta(days=days_ahead)

        calibraciones = Calibracion.objects.select_related('equipo').filter(
            equipo__empresa=empresa,
            proxima_fecha_calibracion__lte=cutoff_date,
            proxima_fecha_calibracion__gte=timezone.now().date()
        ).order_by('proxima_fecha_calibracion')[:10]

        mantenimientos = Mantenimiento.objects.select_related('equipo').filter(
            equipo__empresa=empresa,
            proxima_fecha_mantenimiento__lte=cutoff_date,
            proxima_fecha_mantenimiento__gte=timezone.now().date()
        ).order_by('proxima_fecha_mantenimiento')[:10]

        return {
            'calibraciones': list(calibraciones),
            'mantenimientos': list(mantenimientos)
        }

    def get_equipment_list(self, empresa, page=1, search_query=None, filters=None):
        """Lista optimizada de equipos con paginación y filtros"""
        cache_key = f"equipment_list_{empresa.id}_{page}_{hash(str(search_query))}_{hash(str(filters))}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return cached_data

        try:
            queryset = Equipo.objects.select_related(
                'empresa', 'ubicacion', 'proveedor'
            ).prefetch_related(
                'calibraciones__proveedor',
                'mantenimientos',
                'comprobaciones'
            ).filter(empresa=empresa)

            # Aplicar búsqueda
            if search_query:
                queryset = queryset.filter(
                    models.Q(codigo_interno__icontains=search_query) |
                    models.Q(nombre_equipo__icontains=search_query) |
                    models.Q(marca__icontains=search_query) |
                    models.Q(modelo__icontains=search_query)
                )

            # Aplicar filtros
            if filters:
                if filters.get('ubicacion'):
                    queryset = queryset.filter(ubicacion_id=filters['ubicacion'])
                if filters.get('proveedor'):
                    queryset = queryset.filter(proveedor_id=filters['proveedor'])
                if filters.get('estado'):
                    queryset = queryset.filter(estado=filters['estado'])

            # Ordenar
            queryset = queryset.order_by('-fecha_adquisicion', 'codigo_interno')

            # Paginación
            from django.core.paginator import Paginator
            paginator = Paginator(queryset, 25)  # 25 equipos por página
            page_obj = paginator.get_page(page)

            data = {
                'equipos': list(page_obj),
                'page_obj': page_obj,
                'total_count': paginator.count,
                'search_query': search_query,
                'filters': filters
            }

            # Cache por 10 minutos
            cache.set(cache_key, data, 600)
            return data

        except Exception as e:
            logger.error(f"Error obteniendo lista de equipos: {str(e)}", extra={
                'empresa_id': empresa.id,
                'page': page,
                'search_query': search_query
            })
            raise

    def create_equipment_with_files(self, form_data, files, user):
        """Crear equipo con archivos usando el servicio seguro"""
        try:
            with transaction.atomic():
                empresa = user.empresa if not user.is_superuser else form_data.get('empresa')

                if empresa:
                    self._validate_equipment_limit(empresa)

                # Crear equipo
                equipo = Equipo(**form_data)
                equipo.save()

                # Procesar archivos con el servicio seguro
                archivos_resultado = self._process_equipment_files(equipo, files, user)

                # Actualizar equipo con rutas de archivos
                for campo, resultado in archivos_resultado.items():
                    if resultado['success']:
                        setattr(equipo, campo, resultado['file_path'])

                equipo.save()

                # Invalidar cache
                self._invalidate_equipment_cache(empresa.id if empresa else None)

                logger.info(f"Equipo creado con archivos: {equipo.codigo_interno}", extra={
                    'user_id': user.id,
                    'empresa_id': empresa.id if empresa else None,
                    'equipo_id': equipo.id,
                    'archivos_procesados': len([r for r in archivos_resultado.values() if r['success']])
                })

                return {
                    'success': True,
                    'equipo': equipo,
                    'archivos_resultado': archivos_resultado
                }

        except ValidationError as e:
            logger.warning(f"Error de validación creando equipo: {str(e)}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"Error inesperado creando equipo: {str(e)}", exc_info=True)
            return {'success': False, 'error': f"Error interno: {str(e)}"}

    def _validate_equipment_limit(self, empresa):
        """Validar límite de equipos por empresa"""
        limite = empresa.get_limite_equipos()
        if limite and limite != float('inf'):
            current_count = Equipo.objects.filter(empresa=empresa).count()
            if current_count >= limite:
                raise ValidationError(
                    f"La empresa {empresa.nombre} ha alcanzado su límite de {limite} equipos"
                )

    def _process_equipment_files(self, equipo, files, user):
        """Procesar archivos del equipo usando el servicio seguro"""
        archivos_config = {
            'manual_pdf': 'pdfs/manuales',
            'archivo_compra_pdf': 'pdfs/compras',
            'ficha_tecnica_pdf': 'pdfs/fichas_tecnicas',
            'otros_documentos_pdf': 'pdfs/otros',
            'imagen_equipo': 'imagenes_equipos',
        }

        resultados = {}
        for campo, carpeta in archivos_config.items():
            if campo in files:
                resultado = self.file_service.upload_file(
                    files[campo],
                    carpeta,
                    empresa=equipo.empresa,
                    equipo_codigo=equipo.codigo_interno,
                    user=user
                )
                resultados[campo] = resultado

        return resultados

    def _invalidate_equipment_cache(self, empresa_id):
        """Invalidar cache relacionado con equipos"""
        if not empresa_id:
            return

        # Incrementar versión para invalidar cache relacionado
        # Esto invalida todas las claves de cache que usan el versionado
        version_key = f"equipment_version_{empresa_id}"
        current_version = cache.get(version_key, 0)
        cache.set(version_key, current_version + 1, None)  # Sin expiración


class CacheManager:
    """Manager para cache inteligente con versionado"""

    TIMEOUT_SHORT = 300    # 5 minutos
    TIMEOUT_MEDIUM = 1800  # 30 minutos
    TIMEOUT_LONG = 3600    # 1 hora

    @staticmethod
    def get_cache_key(prefix, *args, version=None):
        """Generar clave de cache consistente con versionado"""
        parts = [str(prefix)]
        for arg in args:
            if arg is not None:
                parts.append(str(arg))

        key = '_'.join(parts)

        if version:
            key = f"{key}_v{version}"

        return key

    @staticmethod
    def get_versioned_data(key, empresa_id=None):
        """Obtener datos con versionado automático"""
        if empresa_id:
            version = cache.get(f"equipment_version_{empresa_id}", 0)
            versioned_key = f"{key}_v{version}"
            return cache.get(versioned_key)
        return cache.get(key)

    @staticmethod
    def set_versioned_data(key, data, timeout, empresa_id=None):
        """Guardar datos con versionado automático"""
        if empresa_id:
            version = cache.get(f"equipment_version_{empresa_id}", 0)
            versioned_key = f"{key}_v{version}"
            cache.set(versioned_key, data, timeout)
        else:
            cache.set(key, data, timeout)

    @staticmethod
    def invalidate_equipment_cache(empresa_id):
        """Invalidar cache relacionado con equipos"""
        if not empresa_id:
            return

        # Incrementar versión para invalidar todo el cache relacionado
        version_key = f"equipment_version_{empresa_id}"
        current_version = cache.get(version_key, 0)
        cache.set(version_key, current_version + 1, None)

        logger.info(f"Cache invalidado para empresa {empresa_id}, nueva versión: {current_version + 1}")


# Instancias globales de los servicios
file_upload_service = SecureFileUploadService()
equipment_service = OptimizedEquipmentService()
cache_manager = CacheManager()