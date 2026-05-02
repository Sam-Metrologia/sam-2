# core/models/catalogs.py
# Modelos: Unidad, Ubicacion, Procedimiento, Proveedor

from django.db import models
from .empresa import Empresa
from .common import get_upload_path


# Modelo para las unidades de medida que se pueden usar en los equipos
class Unidad(models.Model):
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
        Empresa,
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
        unique_together = ('nombre', 'empresa') # Unicidad por empresa

    def __str__(self):
        return f"{self.nombre} ({self.empresa.nombre})"

class Procedimiento(models.Model):
    """Modelo para la gestión de procedimientos."""
    nombre = models.CharField(max_length=255)
    codigo = models.CharField(max_length=100, unique=True)
    version = models.CharField(max_length=50, blank=True, null=True)
    fecha_emision = models.DateField(blank=True, null=True)
    documento_pdf = models.FileField(upload_to=get_upload_path, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    # NUEVO CAMPO: Relación con Empresa
    empresa = models.ForeignKey(
        Empresa,
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
        # Asegurar que el código sea único por empresa
        unique_together = ('codigo', 'empresa')

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

    ESTADO_APROBACION_CHOICES = [
        ('aprobado', 'Aprobado'),
        ('en_evaluacion', 'En evaluación'),
        ('suspendido', 'Suspendido'),
        ('no_aplica', 'No aplica'),
    ]

    ENTIDAD_ACREDITADORA_CHOICES = [
        ('ONAC', 'ONAC (Colombia)'),
        ('IDEAM', 'IDEAM (Colombia)'),
        ('ILAC', 'Miembro ILAC'),
        ('DAkkS', 'DAkkS (Alemania)'),
        ('UKAS', 'UKAS (Reino Unido)'),
        ('A2LA', 'A2LA (EE.UU.)'),
        ('otra', 'Otra entidad acreditadora'),
        ('no_acreditado', 'No acreditado'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='proveedores', verbose_name="Empresa")
    tipo_servicio = models.CharField(max_length=50, choices=TIPO_SERVICIO_CHOICES, verbose_name="Tipo de Servicio")
    nombre_contacto = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nombre de Contacto")
    numero_contacto = models.CharField(max_length=20, blank=True, null=True, verbose_name="Número de Contacto")
    nombre_empresa = models.CharField(max_length=200, verbose_name="Nombre de la Empresa")
    correo_electronico = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
    pagina_web = models.URLField(blank=True, null=True, verbose_name="Página Web")
    alcance = models.TextField(blank=True, null=True, verbose_name="Alcance (áreas o magnitudes)")
    servicio_prestado = models.TextField(blank=True, null=True, verbose_name="Servicio Prestado")

    # Campos de acreditación — ISO/IEC 17020:2026 (adquisición de servicios externos)
    laboratorio_acreditado = models.BooleanField(
        default=False,
        verbose_name="¿Laboratorio acreditado?",
        help_text="Aplica principalmente a proveedores de calibración. Marcar si el proveedor cuenta con acreditación vigente."
    )
    entidad_acreditadora = models.CharField(
        max_length=20, choices=ENTIDAD_ACREDITADORA_CHOICES,
        default='no_acreditado', blank=True,
        verbose_name="Entidad acreditadora"
    )
    numero_acreditacion = models.CharField(
        max_length=100, blank=True, default='',
        verbose_name="Número de acreditación",
        help_text="Ej: ONAC-L-0123"
    )
    estado_aprobacion = models.CharField(
        max_length=20, choices=ESTADO_APROBACION_CHOICES,
        default='no_aplica',
        verbose_name="Estado de aprobación"
    )
    fecha_ultima_evaluacion = models.DateField(
        blank=True, null=True,
        verbose_name="Fecha última evaluación del proveedor"
    )

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['nombre_empresa']
        unique_together = ('nombre_empresa', 'empresa',) # La combinación nombre_empresa y empresa debe ser única
        permissions = [
            ("can_view_proveedor", "Can view proveedor"),
            ("can_add_proveedor", "Can add proveedor"),
            ("can_change_proveedor", "Can change proveedor"),
            ("can_delete_proveedor", "Can delete proveedor"),
        ]

    def __str__(self):
        return f"{self.nombre_empresa} ({self.tipo_servicio}) - {self.empresa.nombre}"
