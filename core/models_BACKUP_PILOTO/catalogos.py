# core/models/catalogos.py
"""
Modelos de catálogos básicos para SAM Metrología:
- Unidad: Unidades de medida
- Ubicacion: Ubicaciones físicas de equipos
- Procedimiento: Procedimientos y documentación
- Proveedor: Proveedores de servicios
"""

from django.db import models
from .base import uuid  # Importar uuid de base


class Unidad(models.Model):
    """Modelo para unidades de medida."""
    nombre = models.CharField(max_length=50, unique=True)
    simbolo = models.CharField(max_length=10, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Unidad de Medida"
        verbose_name_plural = "Unidades de Medida"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.simbolo})" if self.simbolo else self.nombre


class Ubicacion(models.Model):
    """Modelo para la gestión de ubicaciones de equipos."""
    nombre = models.CharField(max_length=255, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    empresa = models.ForeignKey(
        'Empresa',  # String reference para evitar import circular
        on_delete=models.CASCADE,
        related_name='ubicaciones',
        verbose_name="Empresa"
    )

    class Meta:
        verbose_name = "Ubicación"
        verbose_name_plural = "Ubicaciones"
        permissions = [
            ("can_view_ubicacion", "Can view ubicacion"),
            ("can_add_ubicacion", "Can add ubicacion"),
            ("can_change_ubicacion", "Can change ubicacion"),
            ("can_delete_ubicacion", "Can delete ubicacion"),
        ]
        unique_together = ('nombre', 'empresa')  # Unicidad por empresa

    def __str__(self):
        return f"{self.nombre} ({self.empresa.nombre})"


def get_upload_path_procedimiento(instance, filename):
    """
    Define la ruta de subida para archivos de procedimiento.
    NOTA: Esta es una versión simplificada solo para Procedimiento.
    La versión completa está en models.py y se migrará después.
    """
    import re
    import os

    # Sanitizar el nombre del archivo
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w\-_\.]', '_', filename)

    # Usar el código del procedimiento
    base_code = instance.codigo

    # Sanitizar el código base
    safe_base_code = re.sub(r'[^\w\-_]', '_', str(base_code))

    # Construir la ruta
    return f"documentos/{safe_base_code}/procedimientos/{filename}"


class Procedimiento(models.Model):
    """Modelo para la gestión de procedimientos."""
    nombre = models.CharField(max_length=255)
    codigo = models.CharField(max_length=100, unique=True)
    version = models.CharField(max_length=50, blank=True, null=True)
    fecha_emision = models.DateField(blank=True, null=True)
    documento_pdf = models.FileField(
        upload_to=get_upload_path_procedimiento,
        blank=True,
        null=True
    )
    observaciones = models.TextField(blank=True, null=True)
    empresa = models.ForeignKey(
        'Empresa',  # String reference para evitar import circular
        on_delete=models.CASCADE,
        related_name='procedimientos',
        verbose_name="Empresa"
    )

    class Meta:
        verbose_name = "Procedimiento"
        verbose_name_plural = "Procedimientos"
        permissions = [
            ("can_view_procedimiento", "Can view procedimiento"),
            ("can_add_procedimiento", "Can add procedimiento"),
            ("can_change_procedimiento", "Can change procedimiento"),
            ("can_delete_procedimiento", "Can delete procedimiento"),
        ]
        unique_together = ('codigo', 'empresa')  # Asegurar que el código sea único por empresa

    def __str__(self):
        return f"{self.nombre} ({self.codigo}) - {self.empresa.nombre}"


class Proveedor(models.Model):
    """Modelo general para proveedores de cualquier tipo de servicio."""
    TIPO_SERVICIO_CHOICES = [
        ('Calibración', 'Calibración'),
        ('Mantenimiento', 'Mantenimiento'),
        ('Comprobación', 'Comprobación'),
        ('Compra', 'Compra'),
        ('Otro', 'Otro'),
    ]

    empresa = models.ForeignKey(
        'Empresa',  # String reference para evitar import circular
        on_delete=models.CASCADE,
        related_name='proveedores',
        verbose_name="Empresa"
    )
    tipo_servicio = models.CharField(
        max_length=50,
        choices=TIPO_SERVICIO_CHOICES,
        verbose_name="Tipo de Servicio"
    )
    nombre_contacto = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Nombre de Contacto"
    )
    numero_contacto = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Número de Contacto"
    )
    nombre_empresa = models.CharField(max_length=200, verbose_name="Nombre de la Empresa")
    correo_electronico = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
    pagina_web = models.URLField(blank=True, null=True, verbose_name="Página Web")
    alcance = models.TextField(blank=True, null=True, verbose_name="Alcance (áreas o magnitudes)")
    servicio_prestado = models.TextField(blank=True, null=True, verbose_name="Servicio Prestado")

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['nombre_empresa']
        unique_together = ('nombre_empresa', 'empresa')  # La combinación debe ser única
        permissions = [
            ("can_view_proveedor", "Can view proveedor"),
            ("can_add_proveedor", "Can add proveedor"),
            ("can_change_proveedor", "Can change proveedor"),
            ("can_delete_proveedor", "Can delete proveedor"),
        ]

    def __str__(self):
        return f"{self.nombre_empresa} ({self.tipo_servicio}) - {self.empresa.nombre}"
