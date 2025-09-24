# core/file_validators.py
# Validadores mejorados para archivos subidos con seguridad avanzada

import os
import mimetypes
import magic
from django.core.exceptions import ValidationError
from django.conf import settings
import hashlib
import logging

logger = logging.getLogger(__name__)


class SecureFileValidator:
    """
    Validador de archivos con verificación de contenido y seguridad avanzada
    """

    # Configuración de tipos de archivos permitidos
    ALLOWED_EXTENSIONS = {
        'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'],
        'documents': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt'],
        'archives': ['.zip', '.rar', '.7z']
    }

    # MIME types permitidos
    ALLOWED_MIME_TYPES = {
        'images': [
            'image/jpeg', 'image/png', 'image/gif',
            'image/bmp', 'image/webp'
        ],
        'documents': [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/plain'
        ],
        'archives': [
            'application/zip',
            'application/x-rar-compressed',
            'application/x-7z-compressed'
        ]
    }

    # Tamaños máximos por tipo (en bytes)
    MAX_FILE_SIZES = {
        'images': 10 * 1024 * 1024,    # 10MB
        'documents': 50 * 1024 * 1024,  # 50MB
        'archives': 100 * 1024 * 1024   # 100MB
    }

    # Extensiones y patrones peligrosos
    DANGEROUS_EXTENSIONS = [
        '.exe', '.bat', '.cmd', '.scr', '.pif', '.com', '.cpl', '.dll',
        '.jar', '.js', '.jse', '.php', '.asp', '.aspx', '.jsp', '.pl',
        '.py', '.rb', '.sh', '.ps1', '.vbs', '.wsf', '.reg'
    ]

    # Patrones de contenido peligroso
    DANGEROUS_PATTERNS = [
        b'<script',
        b'javascript:',
        b'vbscript:',
        b'onload=',
        b'onerror=',
        b'<?php',
        b'<%',
        b'#!/bin/sh',
        b'#!/usr/bin/python'
    ]

    def __init__(self, file_type='documents', max_size=None, allowed_extensions=None):
        """
        Inicializa el validador

        Args:
            file_type: Tipo de archivo ('images', 'documents', 'archives')
            max_size: Tamaño máximo en bytes (opcional)
            allowed_extensions: Lista de extensiones permitidas (opcional)
        """
        self.file_type = file_type
        self.max_size = max_size or self.MAX_FILE_SIZES.get(file_type, 10 * 1024 * 1024)
        self.allowed_extensions = allowed_extensions or self.ALLOWED_EXTENSIONS.get(file_type, [])
        self.allowed_mime_types = self.ALLOWED_MIME_TYPES.get(file_type, [])

    def validate(self, uploaded_file):
        """
        Valida un archivo subido completamente
        """
        try:
            # 1. Validar tamaño
            self._validate_file_size(uploaded_file)

            # 2. Validar extensión
            self._validate_extension(uploaded_file.name)

            # 3. Validar MIME type por contenido
            self._validate_mime_type(uploaded_file)

            # 4. Validar contenido por patrones peligrosos
            self._validate_content_security(uploaded_file)

            # 5. Validaciones específicas por tipo
            self._validate_by_file_type(uploaded_file)

            # 6. Generar hash para integridad
            file_hash = self._generate_file_hash(uploaded_file)

            logger.info(f"File validated successfully: {uploaded_file.name} (hash: {file_hash[:16]})")

            return True

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error validating file {uploaded_file.name}: {e}")
            raise ValidationError(f"Error validating file: {str(e)}")

    def _validate_file_size(self, uploaded_file):
        """
        Valida el tamaño del archivo
        """
        if uploaded_file.size > self.max_size:
            size_mb = uploaded_file.size / (1024 * 1024)
            max_mb = self.max_size / (1024 * 1024)
            raise ValidationError(
                f"File too large: {size_mb:.1f}MB. Maximum allowed: {max_mb:.1f}MB"
            )

    def _validate_extension(self, filename):
        """
        Valida la extensión del archivo
        """
        if not filename:
            raise ValidationError("Filename cannot be empty")

        file_ext = os.path.splitext(filename.lower())[1]

        # Verificar extensiones peligrosas
        if file_ext in self.DANGEROUS_EXTENSIONS:
            raise ValidationError(f"Dangerous file type not allowed: {file_ext}")

        # Verificar extensiones permitidas
        if file_ext not in [ext.lower() for ext in self.allowed_extensions]:
            allowed = ', '.join(self.allowed_extensions)
            raise ValidationError(f"File type {file_ext} not allowed. Allowed: {allowed}")

    def _validate_mime_type(self, uploaded_file):
        """
        Valida el MIME type por contenido real del archivo
        """
        try:
            # Leer primeros bytes para detección de MIME
            uploaded_file.seek(0)
            file_header = uploaded_file.read(1024)
            uploaded_file.seek(0)

            # Usar python-magic si está disponible, sino mimetypes
            try:
                import magic
                detected_mime = magic.from_buffer(file_header, mime=True)
            except ImportError:
                # Fallback a mimetypes
                detected_mime, _ = mimetypes.guess_type(uploaded_file.name)

            if detected_mime and detected_mime not in self.allowed_mime_types:
                raise ValidationError(
                    f"Invalid file content. Detected: {detected_mime}. "
                    f"Allowed: {', '.join(self.allowed_mime_types)}"
                )

        except Exception as e:
            logger.warning(f"Could not validate MIME type for {uploaded_file.name}: {e}")
            # No fallar si no se puede detectar el MIME type

    def _validate_content_security(self, uploaded_file):
        """
        Valida el contenido del archivo buscando patrones peligrosos
        """
        try:
            uploaded_file.seek(0)
            # Leer primeros 10KB para análisis de seguridad
            content_sample = uploaded_file.read(10 * 1024)
            uploaded_file.seek(0)

            # Buscar patrones peligrosos
            content_lower = content_sample.lower()
            for pattern in self.DANGEROUS_PATTERNS:
                if pattern in content_lower:
                    raise ValidationError(
                        f"File contains potentially dangerous content: {pattern.decode('utf-8', errors='ignore')}"
                    )

            # Verificar caracteres de control excesivos
            null_count = content_sample.count(b'\x00')
            if null_count > len(content_sample) * 0.3:  # Más del 30% null bytes
                raise ValidationError("File contains excessive null bytes - possible binary exploit")

        except ValidationError:
            raise
        except Exception as e:
            logger.warning(f"Could not scan file content for {uploaded_file.name}: {e}")

    def _validate_by_file_type(self, uploaded_file):
        """
        Validaciones específicas según el tipo de archivo
        """
        if self.file_type == 'images':
            self._validate_image_file(uploaded_file)
        elif self.file_type == 'documents':
            self._validate_document_file(uploaded_file)
        elif self.file_type == 'archives':
            self._validate_archive_file(uploaded_file)

    def _validate_image_file(self, uploaded_file):
        """
        Validaciones específicas para imágenes
        """
        try:
            from PIL import Image

            uploaded_file.seek(0)
            img = Image.open(uploaded_file)

            # Validar dimensiones máximas
            max_width, max_height = 4000, 4000
            if img.width > max_width or img.height > max_height:
                raise ValidationError(
                    f"Image too large: {img.width}x{img.height}px. "
                    f"Maximum: {max_width}x{max_height}px"
                )

            # Verificar formato válido
            if img.format not in ['JPEG', 'PNG', 'GIF', 'BMP', 'WEBP']:
                raise ValidationError(f"Unsupported image format: {img.format}")

            uploaded_file.seek(0)

        except ImportError:
            logger.warning("PIL not available for image validation")
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Invalid image file: {str(e)}")

    def _validate_document_file(self, uploaded_file):
        """
        Validaciones específicas para documentos
        """
        try:
            uploaded_file.seek(0)
            header = uploaded_file.read(100)
            uploaded_file.seek(0)

            # Verificar headers conocidos
            if uploaded_file.name.lower().endswith('.pdf'):
                if not header.startswith(b'%PDF'):
                    raise ValidationError("Invalid PDF file - missing PDF header")

            elif uploaded_file.name.lower().endswith(('.doc', '.docx', '.xls', '.xlsx')):
                # Office files deben empezar con magic numbers específicos
                office_signatures = [
                    b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',  # OLE2 (old Office)
                    b'PK\x03\x04',  # ZIP (new Office)
                ]

                if not any(header.startswith(sig) for sig in office_signatures):
                    raise ValidationError("Invalid Office document - missing proper signature")

        except ValidationError:
            raise
        except Exception as e:
            logger.warning(f"Could not validate document structure: {e}")

    def _validate_archive_file(self, uploaded_file):
        """
        Validaciones específicas para archivos comprimidos
        """
        try:
            uploaded_file.seek(0)
            header = uploaded_file.read(50)
            uploaded_file.seek(0)

            # Verificar signatures de archivos comprimidos
            if uploaded_file.name.lower().endswith('.zip'):
                if not header.startswith(b'PK'):
                    raise ValidationError("Invalid ZIP file - missing ZIP signature")

            elif uploaded_file.name.lower().endswith('.rar'):
                if not header.startswith(b'Rar!'):
                    raise ValidationError("Invalid RAR file - missing RAR signature")

        except ValidationError:
            raise
        except Exception as e:
            logger.warning(f"Could not validate archive structure: {e}")

    def _generate_file_hash(self, uploaded_file):
        """
        Genera hash SHA256 del archivo para integridad
        """
        try:
            uploaded_file.seek(0)
            hash_sha256 = hashlib.sha256()

            for chunk in iter(lambda: uploaded_file.read(4096), b""):
                hash_sha256.update(chunk)

            uploaded_file.seek(0)
            return hash_sha256.hexdigest()

        except Exception as e:
            logger.warning(f"Could not generate file hash: {e}")
            return "unknown"


# Funciones de validación para usar en forms
def validate_image_file(uploaded_file):
    """Validador para archivos de imagen"""
    validator = SecureFileValidator('images')
    validator.validate(uploaded_file)


def validate_document_file(uploaded_file):
    """Validador para archivos de documento"""
    validator = SecureFileValidator('documents')
    validator.validate(uploaded_file)


def validate_archive_file(uploaded_file):
    """Validador para archivos comprimidos"""
    validator = SecureFileValidator('archives')
    validator.validate(uploaded_file)


# Validador personalizable
def create_custom_validator(file_type, max_size_mb=10, allowed_extensions=None):
    """
    Crea un validador personalizado

    Args:
        file_type: Tipo de archivo
        max_size_mb: Tamaño máximo en MB
        allowed_extensions: Lista de extensiones permitidas

    Returns:
        Función validadora
    """
    max_size = max_size_mb * 1024 * 1024

    def validator(uploaded_file):
        custom_validator = SecureFileValidator(
            file_type=file_type,
            max_size=max_size,
            allowed_extensions=allowed_extensions
        )
        custom_validator.validate(uploaded_file)

    return validator


# Clase para análisis de archivos sospechosos
class FileSecurityAnalyzer:
    """
    Analizador avanzado de seguridad para archivos
    """

    @staticmethod
    def analyze_file_risk(uploaded_file):
        """
        Analiza el nivel de riesgo de un archivo
        """
        risk_score = 0
        warnings = []

        try:
            # Análisis básico
            file_ext = os.path.splitext(uploaded_file.name.lower())[1]

            # Riesgo por extensión
            if file_ext in SecureFileValidator.DANGEROUS_EXTENSIONS:
                risk_score += 50
                warnings.append(f"Dangerous extension: {file_ext}")

            # Análisis de contenido
            uploaded_file.seek(0)
            content_sample = uploaded_file.read(5000)
            uploaded_file.seek(0)

            # Buscar patrones sospechosos
            for pattern in SecureFileValidator.DANGEROUS_PATTERNS:
                if pattern in content_sample.lower():
                    risk_score += 20
                    warnings.append(f"Suspicious pattern found: {pattern.decode('utf-8', errors='ignore')}")

            # Análisis de entropía (complejidad)
            entropy = FileSecurityAnalyzer._calculate_entropy(content_sample[:1000])
            if entropy > 7.5:  # Muy alta entropía puede indicar contenido cifrado/comprimido
                risk_score += 10
                warnings.append(f"High entropy detected: {entropy:.2f}")

            # Determinar nivel de riesgo
            if risk_score >= 50:
                risk_level = 'HIGH'
            elif risk_score >= 20:
                risk_level = 'MEDIUM'
            elif risk_score > 0:
                risk_level = 'LOW'
            else:
                risk_level = 'SAFE'

            return {
                'risk_level': risk_level,
                'risk_score': risk_score,
                'warnings': warnings,
                'file_name': uploaded_file.name,
                'file_size': uploaded_file.size
            }

        except Exception as e:
            logger.error(f"Error analyzing file risk: {e}")
            return {
                'risk_level': 'UNKNOWN',
                'risk_score': 0,
                'warnings': [f"Analysis error: {str(e)}"],
                'file_name': uploaded_file.name,
                'file_size': uploaded_file.size
            }

    @staticmethod
    def _calculate_entropy(data):
        """
        Calcula la entropía de Shannon de los datos
        """
        if not data:
            return 0

        # Contar frecuencias
        frequencies = {}
        for byte in data:
            frequencies[byte] = frequencies.get(byte, 0) + 1

        # Calcular entropía
        entropy = 0
        data_length = len(data)

        for freq in frequencies.values():
            probability = freq / data_length
            if probability > 0:
                entropy -= probability * (probability.bit_length() - 1)

        return entropy