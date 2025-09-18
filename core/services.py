import uuid
import re
import os
import logging
from datetime import datetime
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError
from django.db import transaction
from django.core.cache import cache
from django.utils import timezone
from .models import Equipo, Empresa, Calibracion, Mantenimiento, Comprobacion

logger = logging.getLogger('core')

class EquipmentService:
    """Servicio para lógica de negocio de equipos"""
    
    def __init__(self):
        self.file_service = FileUploadService()
    
    def create_equipment(self, form_data, files, user):
        """Crear equipo con validación completa y manejo de archivos"""
        try:
            with transaction.atomic():
                # Validar límites de empresa
                empresa = user.empresa if not user.is_superuser else form_data.get('empresa')
                if empresa:
                    self._validate_equipment_limit(empresa)
                
                # Crear equipo
                equipo = Equipo(**form_data)
                equipo.save()
                
                # Procesar archivos
                archivos_resultado = self._process_equipment_files(equipo, files)
                
                # Actualizar equipo con rutas de archivos
                for campo, resultado in archivos_resultado.items():
                    if resultado['success']:
                        setattr(equipo, campo, resultado['file_path'])
                
                equipo.save()
                
                # Invalidar cache
                CacheManager.invalidate_equipment_cache(empresa.id if empresa else None)
                
                # Log de auditoría
                logger.info(f"Equipo creado: {equipo.codigo_interno}", extra={
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
    
    def _process_equipment_files(self, equipo, files):
        """Procesar archivos del equipo"""
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
                    equipo.codigo_interno
                )
                resultados[campo] = resultado
        
        return resultados


class FileUploadService:
    """Servicio centralizado para manejo seguro de archivos"""
    
    def __init__(self):
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.allowed_extensions = {
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg', 
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        self.dangerous_patterns = [
            r'\.\./', r'\.\.\\', r'~/', r'/', r'%',
            r'<script', r'javascript:', r'vbscript:', r'onload=',
            r'<?php', r'<%', r'${', r'#{', r'<%='
        ]
    
    def secure_sanitize_filename(self, filename, max_length=100):
        """Sanitización robusta de nombres de archivo"""
        if not filename:
            raise ValidationError("Nombre de archivo vacío")
        
        # Obtener solo el nombre base
        filename = os.path.basename(filename)
        
        # Verificar patrones peligrosos
        filename_lower = filename.lower()
        for pattern in self.dangerous_patterns:
            if re.search(pattern, filename_lower):
                raise ValidationError(f"Nombre de archivo contiene patrones peligrosos: {pattern}")
        
        # Validar extensión
        _, ext = os.path.splitext(filename.lower())
        if ext not in self.allowed_extensions:
            raise ValidationError(f"Extensión {ext} no permitida. Extensiones válidas: {list(self.allowed_extensions.keys())}")
        
        # Remover caracteres peligrosos
        name, ext = os.path.splitext(filename)
        name = re.sub(r'[^\w\-_\.]', '_', name)
        name = re.sub(r'_{2,}', '_', name)
        name = name.strip('_')
        
        if not name:
            name = f"archivo_{uuid.uuid4().hex[:8]}"
        
        # Validar longitud
        if len(name) > max_length - len(ext) - 20:  # Espacio para timestamp
            name = name[:max_length - len(ext) - 20]
        
        return f"{name}{ext}"
    
    def validate_file(self, uploaded_file):
        """Validación completa de archivo"""
        if not uploaded_file:
            raise ValidationError("No se proporcionó archivo")
            
        if uploaded_file.size == 0:
            raise ValidationError("El archivo está vacío")
            
        if uploaded_file.size > self.max_file_size:
            raise ValidationError(f"Archivo muy grande. Máximo: {self.max_file_size/1024/1024:.1f}MB")
        
        # Validar extensión
        _, ext = os.path.splitext(uploaded_file.name.lower())
        if ext not in self.allowed_extensions:
            raise ValidationError(f"Tipo de archivo no permitido: {ext}")
        
        # Validar contenido del archivo (magic numbers)
        if hasattr(uploaded_file, 'read'):
            uploaded_file.seek(0)
            header = uploaded_file.read(2048)  # Leer más bytes para mejor detección
            uploaded_file.seek(0)
            
            # Validaciones específicas por tipo
            if ext == '.pdf':
                if not header.startswith(b'%PDF'):
                    raise ValidationError("El archivo PDF está corrupto o no es válido")
            elif ext in ['.jpg', '.jpeg']:
                if not (header.startswith(b'\xff\xd8\xff') or b'JFIF' in header[:50]):
                    raise ValidationError("El archivo JPEG no es válido")
            elif ext == '.png':
                if not header.startswith(b'\x89PNG\r\n\x1a\n'):
                    raise ValidationError("El archivo PNG no es válido")
            elif ext == '.xlsx':
                # XLSX son archivos ZIP, verificar firma ZIP
                if not header.startswith(b'PK'):
                    raise ValidationError("El archivo Excel no es válido")
            
            # Verificar contenido malicioso
            header_str = header.decode('utf-8', errors='ignore').lower()
            for pattern in self.dangerous_patterns:
                if re.search(pattern, header_str):
                    raise ValidationError("El archivo contiene contenido potencialmente malicioso")
    
    def upload_file(self, uploaded_file, folder_path, equipo_codigo=None):
        """Subida segura de archivos con validación completa"""
        try:
            # Validar archivo
            self.validate_file(uploaded_file)
            
            # Sanitizar nombre
            safe_filename = self.secure_sanitize_filename(uploaded_file.name)
            
            # Generar nombre único para evitar colisiones
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = uuid.uuid4().hex[:8]
            unique_filename = f"{timestamp}_{unique_id}_{safe_filename}"
            
            # Construir ruta segura
            if equipo_codigo:
                safe_codigo = re.sub(r'[^\w\-_]', '_', str(equipo_codigo))[:50]  # Limitar longitud
                full_path = f"{folder_path}/{safe_codigo}/{unique_filename}"
            else:
                full_path = f"{folder_path}/{unique_filename}"
            
            # Verificar que la ruta no exceda límites del sistema
            if len(full_path) > 250:  # Límite conservativo para nombres de archivo
                raise ValidationError("Ruta de archivo muy larga")
            
            # Subir archivo
            file_path = default_storage.save(full_path, uploaded_file)
            
            # Verificar que el archivo se subió correctamente
            if not default_storage.exists(file_path):
                raise Exception("El archivo no se guardó correctamente")
            
            logger.info(f"Archivo subido exitosamente: {file_path}", extra={
                'original_name': uploaded_file.name,
                'file_size': uploaded_file.size,
                'file_path': file_path,
                'content_type': uploaded_file.content_type if hasattr(uploaded_file, 'content_type') else 'unknown'
            })
            
            return {
                'success': True,
                'file_path': file_path,
                'original_name': uploaded_file.name,
                'size': uploaded_file.size,
                'unique_name': unique_filename
            }
            
        except ValidationError as e:
            logger.warning(f"Validación de archivo falló: {str(e)}", extra={
                'filename': uploaded_file.name if uploaded_file else 'Unknown',
                'file_size': uploaded_file.size if uploaded_file else 0
            })
            return {
                'success': False,
                'error': str(e),
                'file_path': None
            }
        except Exception as e:
            logger.error(f"Error inesperado al subir archivo: {str(e)}", exc_info=True, extra={
                'filename': uploaded_file.name if uploaded_file else 'Unknown'
            })
            return {
                'success': False,
                'error': f"Error interno del servidor: {str(e)[:100]}...",  # Limitar longitud del error
                'file_path': None
            }
    
    def delete_file(self, file_path):
        """Eliminar archivo de forma segura"""
        try:
            if file_path and default_storage.exists(file_path):
                default_storage.delete(file_path)
                logger.info(f"Archivo eliminado: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error al eliminar archivo {file_path}: {str(e)}")
            return False


class CacheManager:
    """Manager para cache inteligente"""
    
    TIMEOUT_SHORT = 300    # 5 minutos
    TIMEOUT_MEDIUM = 1800  # 30 minutos  
    TIMEOUT_LONG = 3600    # 1 hora
    
    @staticmethod
    def get_cache_key(prefix, *args):
        """Generar clave de cache consistente"""
        parts = [str(prefix)]
        for arg in args:
            if arg is not None:
                parts.append(str(arg))
        return '_'.join(parts)
    
    @staticmethod
    def invalidate_equipment_cache(empresa_id):
        """Invalidar cache relacionado con equipos"""
        if not empresa_id:
            return
            
        keys_to_delete = [
            CacheManager.get_cache_key('dashboard_stats', empresa_id),
            CacheManager.get_cache_key('equipment_list', empresa_id),
            CacheManager.get_cache_key('equipment_count', empresa_id),
            CacheManager.get_cache_key('equipment_limit_check', empresa_id),
            CacheManager.get_cache_key('activities_summary', empresa_id)
        ]
        
        try:
            cache.delete_many(keys_to_delete)
            logger.debug(f"Cache invalidado para empresa {empresa_id}: {len(keys_to_delete)} claves")
        except Exception as e:
            logger.error(f"Error al invalidar cache: {str(e)}")
    
    @staticmethod  
    def get_or_set(cache_key, calculator_func, timeout=TIMEOUT_SHORT):
        """Cache inteligente con función de cálculo"""
        try:
            data = cache.get(cache_key)
            if data is not None:
                return data
            
            # Calcular datos
            data = calculator_func()
            
            # Verificar que los datos sean serializables
            if data is not None:
                cache.set(cache_key, data, timeout)
            
            return data
            
        except Exception as e:
            logger.error(f"Error en cache get_or_set para clave {cache_key}: {str(e)}")
            # En caso de error, ejecutar la función directamente
            return calculator_func()
    
    @staticmethod
    def increment_counter(key, timeout=TIMEOUT_MEDIUM):
        """Incrementar contador en cache"""
        try:
            current = cache.get(key, 0)
            cache.set(key, current + 1, timeout)
            return current + 1
        except Exception as e:
            logger.error(f"Error al incrementar contador {key}: {str(e)}")
            return 1


class AuditService:
    """Servicio para auditoría y logging de acciones importantes"""
    
    @staticmethod
    def log_equipment_action(action, equipo, user, additional_data=None):
        """Registrar acciones sobre equipos"""
        log_data = {
            'action': action,
            'equipo_id': equipo.id,
            'equipo_codigo': equipo.codigo_interno,
            'user_id': user.id,
            'user_username': user.username,
            'empresa_id': equipo.empresa.id if equipo.empresa else None,
            'timestamp': timezone.now().isoformat()
        }
        
        if additional_data:
            log_data.update(additional_data)
        
        logger.info(f"Acción de equipo: {action}", extra=log_data)
    
    @staticmethod
    def log_file_action(action, file_path, user, equipo=None):
        """Registrar acciones sobre archivos"""
        log_data = {
            'action': action,
            'file_path': file_path,
            'user_id': user.id,
            'user_username': user.username,
            'timestamp': timezone.now().isoformat()
        }
        
        if equipo:
            log_data.update({
                'equipo_id': equipo.id,
                'equipo_codigo': equipo.codigo_interno
            })
        
        logger.info(f"Acción de archivo: {action}", extra=log_data)


class ValidationService:
    """Servicio para validaciones de negocio"""
    
    @staticmethod
    def validate_equipment_data(data, empresa=None):
        """Validar datos de equipo según reglas de negocio"""
        errors = []
        
        # Validar código interno
        codigo = data.get('codigo_interno')
        if codigo:
            if not re.match(r'^[A-Z0-9\-_]{3,20}$', codigo):
                errors.append("El código interno debe tener 3-20 caracteres alfanuméricos, guiones o guiones bajos")
            
            if empresa:
                # Verificar unicidad en la empresa
                exists = Equipo.objects.filter(
                    codigo_interno=codigo, 
                    empresa=empresa
                ).exists()
                if exists:
                    errors.append(f"Ya existe un equipo con código '{codigo}' en {empresa.nombre}")
        
        # Validar fechas
        fecha_adquisicion = data.get('fecha_adquisicion')
        if fecha_adquisicion and fecha_adquisicion > timezone.now().date():
            errors.append("La fecha de adquisición no puede ser futura")
        
        # Validar frecuencias
        for campo in ['frecuencia_calibracion_meses', 'frecuencia_mantenimiento_meses', 'frecuencia_comprobacion_meses']:
            freq = data.get(campo)
            if freq is not None and freq <= 0:
                errors.append(f"La {campo.replace('_', ' ')} debe ser positiva")
        