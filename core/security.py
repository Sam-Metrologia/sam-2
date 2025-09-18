# core/security.py
# Sistema de seguridad avanzado para validación de archivos y protección contra ataques

import os
import re
import uuid
import mimetypes
from datetime import datetime

# Sin dependencia de python-magic para mejor compatibilidad
from pathlib import Path
from django.core.exceptions import ValidationError
from django.conf import settings
import logging

logger = logging.getLogger('core.security')

class SecureFileValidator:
    """
    Validador de archivos con seguridad robusta contra:
    - Path traversal attacks
    - MIME type spoofing
    - Malicious file content
    - Executable file uploads
    """

    # Tipos MIME permitidos con sus extensiones correspondientes
    ALLOWED_TYPES = {
        'application/pdf': ['.pdf'],
        'image/jpeg': ['.jpg', '.jpeg'],
        'image/png': ['.png'],
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    }

    # Firmas de archivos (magic numbers) para validación de contenido
    FILE_SIGNATURES = {
        '.pdf': [b'%PDF'],
        '.jpg': [b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\xff\xd8\xff\xdb'],
        '.jpeg': [b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\xff\xd8\xff\xdb'],
        '.png': [b'\x89PNG\r\n\x1a\n'],
        '.xlsx': [b'PK\x03\x04'],  # ZIP signature (XLSX son archivos ZIP)
        '.docx': [b'PK\x03\x04'],  # ZIP signature (DOCX son archivos ZIP)
    }

    # Patrones peligrosos que no deben aparecer en nombres de archivo
    DANGEROUS_PATTERNS = [
        r'\.\.[\\/]',  # Path traversal
        r'^[\\/]',     # Absolute paths
        r'~[\\/]',     # Home directory
        r'%[0-9a-fA-F]{2}',  # URL encoding
        r'<script.*?>',      # Script tags
        r'javascript:',      # JavaScript URLs
        r'vbscript:',       # VBScript URLs
        r'data:',           # Data URLs
        r'file:',           # File URLs
        r'\x00',            # Null bytes
        r'[\x01-\x1f\x7f-\x9f]',  # Control characters
    ]

    # Extensiones ejecutables peligrosas
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.msi', '.msp',
        '.hta', '.htc', '.vbs', '.vbe', '.js', '.jse', '.ws', '.wsf',
        '.wsc', '.wsh', '.ps1', '.ps1xml', '.ps2', '.ps2xml', '.psc1',
        '.psc2', '.msh', '.msh1', '.msh2', '.mshxml', '.msh1xml', '.msh2xml',
        '.scf', '.lnk', '.inf', '.reg', '.dll', '.ocx', '.sys', '.drv',
        '.cpl', '.jar', '.class', '.dex', '.apk', '.ipa', '.dmg', '.pkg',
        '.app', '.bin', '.run', '.deb', '.rpm', '.tar', '.gz', '.zip',
        '.rar', '.7z', '.iso', '.img'
    }

    def __init__(self, max_file_size=10*1024*1024):  # 10MB por defecto
        self.max_file_size = max_file_size

    def validate_filename(self, filename):
        """
        Valida y sanitiza el nombre de archivo
        """
        if not filename:
            raise ValidationError("Nombre de archivo vacío")

        # Obtener solo el nombre base (prevenir path traversal)
        filename = os.path.basename(filename)

        if not filename or filename in ['.', '..']:
            raise ValidationError("Nombre de archivo no válido")

        # Verificar longitud
        if len(filename) > 255:
            raise ValidationError("Nombre de archivo muy largo (máximo 255 caracteres)")

        # Verificar patrones peligrosos
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                raise ValidationError(f"Nombre de archivo contiene patrones no seguros: {pattern}")

        # Verificar extensión
        _, ext = os.path.splitext(filename.lower())

        if ext in self.DANGEROUS_EXTENSIONS:
            raise ValidationError(f"Extensión de archivo peligrosa: {ext}")

        if ext not in [ext for exts in self.ALLOWED_TYPES.values() for ext in exts]:
            raise ValidationError(f"Extensión no permitida: {ext}")

        return self._sanitize_filename(filename)

    def _sanitize_filename(self, filename):
        """
        Sanitiza el nombre de archivo removiendo caracteres peligrosos
        """
        # Separar nombre y extensión
        name, ext = os.path.splitext(filename)

        # Remover caracteres no seguros
        name = re.sub(r'[^\w\-_\.]', '_', name)
        name = re.sub(r'_{2,}', '_', name)  # Múltiples underscores
        name = name.strip('_.-')  # Quitar caracteres al inicio/final

        # Si el nombre quedó vacío, generar uno
        if not name:
            name = f"archivo_{uuid.uuid4().hex[:8]}"

        # Limitar longitud (conservar espacio para timestamp y UUID)
        if len(name) > 100:
            name = name[:100]

        return f"{name}{ext.lower()}"

    def validate_file_content(self, uploaded_file):
        """
        Valida el contenido del archivo usando firmas binarias
        """
        if not uploaded_file:
            raise ValidationError("No se proporcionó archivo")

        # Verificar tamaño
        if uploaded_file.size == 0:
            raise ValidationError("El archivo está vacío")

        if uploaded_file.size > self.max_file_size:
            size_mb = self.max_file_size / (1024 * 1024)
            raise ValidationError(f"Archivo muy grande. Máximo permitido: {size_mb:.1f}MB")

        # Obtener extensión
        _, ext = os.path.splitext(uploaded_file.name.lower())

        # Leer header del archivo para validar firma
        uploaded_file.seek(0)
        header = uploaded_file.read(2048)
        uploaded_file.seek(0)

        # Verificar firma del archivo
        if ext in self.FILE_SIGNATURES:
            signatures = self.FILE_SIGNATURES[ext]
            is_valid = any(header.startswith(sig) for sig in signatures)

            if not is_valid:
                raise ValidationError(f"El archivo no coincide con el formato esperado para {ext}")

        # Verificar contenido malicioso en texto plano
        try:
            # Intentar decodificar como texto para buscar patrones maliciosos
            text_content = header.decode('utf-8', errors='ignore').lower()
            for pattern in self.DANGEROUS_PATTERNS:
                if re.search(pattern, text_content):
                    raise ValidationError("El archivo contiene contenido potencialmente malicioso")
        except:
            # Si no se puede decodificar, no es texto plano (está bien)
            pass

        # Validación MIME type si está disponible
        if hasattr(uploaded_file, 'content_type') and uploaded_file.content_type:
            self._validate_mime_type(uploaded_file.content_type, ext)

    def _validate_mime_type(self, content_type, extension):
        """
        Valida que el MIME type coincida con la extensión
        """
        # Encontrar MIME types válidos para esta extensión
        valid_mime_types = [
            mime_type for mime_type, exts in self.ALLOWED_TYPES.items()
            if extension in exts
        ]

        if content_type not in valid_mime_types:
            logger.warning(f"MIME type mismatch: {content_type} for extension {extension}")
            # Solo advertir, no fallar, ya que algunos navegadores envían MIME types incorrectos

    def generate_secure_filename(self, original_filename, prefix="file"):
        """
        Genera un nombre de archivo seguro y único
        """
        sanitized = self.validate_filename(original_filename)
        name, ext = os.path.splitext(sanitized)

        # Agregar timestamp y UUID para unicidad
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = uuid.uuid4().hex[:8]

        return f"{prefix}_{timestamp}_{unique_id}_{name}{ext}"

    def generate_secure_path(self, filename, folder_path, subfolder=None):
        """
        Genera una ruta segura para el archivo
        """
        # Sanitizar componentes de la ruta
        folder_parts = []

        # Sanitizar folder_path
        if folder_path:
            safe_folder = re.sub(r'[^\w\-_/\\]', '_', str(folder_path))
            safe_folder = re.sub(r'[/\\]+', '/', safe_folder)  # Normalizar separadores
            safe_folder = safe_folder.strip('/')
            if safe_folder:
                folder_parts.append(safe_folder)

        # Sanitizar subfolder si existe
        if subfolder:
            safe_subfolder = re.sub(r'[^\w\-_]', '_', str(subfolder)[:50])
            if safe_subfolder:
                folder_parts.append(safe_subfolder)

        # Construir ruta final
        if folder_parts:
            full_path = '/'.join(folder_parts) + '/' + filename
        else:
            full_path = filename

        # Verificar longitud de ruta
        if len(full_path) > 250:
            raise ValidationError("Ruta de archivo muy larga")

        return full_path


class StorageQuotaManager:
    """
    Gestor de cuotas de almacenamiento por empresa
    """

    def __init__(self):
        self.default_quota = getattr(settings, 'DEFAULT_STORAGE_QUOTA', 1024 * 1024 * 1024)  # 1GB

    def get_company_quota(self, empresa):
        """
        Obtiene la cuota de almacenamiento para una empresa
        """
        if hasattr(empresa, 'limite_almacenamiento_mb') and empresa.limite_almacenamiento_mb:
            return empresa.limite_almacenamiento_mb * 1024 * 1024  # Convertir MB a bytes
        return self.default_quota

    def get_company_usage(self, empresa):
        """
        Calcula el uso actual de almacenamiento de una empresa
        """
        from django.db.models import Sum
        from .models import Documento

        # Sumar tamaños de todos los archivos de la empresa
        usage = Documento.objects.filter(
            empresa=empresa
        ).aggregate(
            total_size=Sum('tamaño_archivo')
        )['total_size'] or 0

        return usage

    def check_quota_available(self, empresa, additional_size):
        """
        Verifica si hay cuota disponible para un archivo adicional
        """
        quota = self.get_company_quota(empresa)
        current_usage = self.get_company_usage(empresa)

        if current_usage + additional_size > quota:
            quota_mb = quota / (1024 * 1024)
            usage_mb = current_usage / (1024 * 1024)
            raise ValidationError(
                f"Cuota de almacenamiento excedida. "
                f"Límite: {quota_mb:.1f}MB, "
                f"Uso actual: {usage_mb:.1f}MB"
            )

        return True

    def get_quota_info(self, empresa):
        """
        Obtiene información detallada de la cuota
        """
        quota = self.get_company_quota(empresa)
        usage = self.get_company_usage(empresa)

        return {
            'quota_bytes': quota,
            'quota_mb': quota / (1024 * 1024),
            'usage_bytes': usage,
            'usage_mb': usage / (1024 * 1024),
            'available_bytes': quota - usage,
            'available_mb': (quota - usage) / (1024 * 1024),
            'usage_percentage': (usage / quota * 100) if quota > 0 else 0
        }