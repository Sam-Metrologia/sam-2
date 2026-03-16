# core/models/documents.py
# Modelos: Documento, ZipRequest, NotificacionZip

from django.db import models
from django.conf import settings


class Documento(models.Model):
    """
    Modelo para almacenar información sobre documentos genéricos subidos.
    Puede ser usado para PDFs u otros archivos no directamente asociados a un equipo/actividad específica.
    """
    nombre_archivo = models.CharField(max_length=255, verbose_name="Nombre del Archivo")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    # Este campo almacenará la ruta relativa o clave del objeto en S3
    archivo_s3_path = models.CharField(max_length=500, blank=True, null=True, verbose_name="Ruta en S3")

    # Campos para control de almacenamiento
    tamaño_archivo = models.BigIntegerField(default=0, verbose_name="Tamaño del Archivo (bytes)")
    tipo_mime = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tipo MIME")
    checksum_md5 = models.CharField(max_length=32, blank=True, null=True, verbose_name="Checksum MD5")
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Subido por"
    )
    fecha_subida = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Subida")
    empresa = models.ForeignKey(
        'Empresa', # Usa 'Empresa' como cadena si Empresa está definida más arriba o abajo
        on_delete=models.CASCADE,
        related_name='documentos_generales',
        verbose_name="Empresa Asociada",
        null=True, # Puede ser null si es un documento global o si el usuario no tiene empresa
        blank=True
    )

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        ordering = ['-fecha_subida']
        permissions = [
            ("can_view_documento", "Can view documento"),
            ("can_add_documento", "Can add documento"),
            ("can_change_documento", "Can change documento"),
            ("can_delete_documento", "Can delete documento"),
        ]

    def __str__(self):
        return f"{self.nombre_archivo} ({self.empresa.nombre if self.empresa else 'N/A'})"

    def get_absolute_s3_url(self):
        """Devuelve la URL pública del archivo en S3 si existe."""
        if self.nombre_archivo:
            ruta_s3 = f'pdfs/{self.nombre_archivo}'
            from django.core.files.storage import default_storage # Importar aquí para evitar dependencia circular
            return default_storage.url(ruta_s3)
        return None


class ZipRequest(models.Model):
    """Modelo para manejar cola de generación de archivos ZIP."""

    STATUS_CHOICES = [
        ('pending', 'En Cola'),
        ('processing', 'Procesando'),
        ('completed', 'Completado'),
        ('failed', 'Error'),
        ('expired', 'Expirado'),
    ]

    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, verbose_name="Usuario")
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE, verbose_name="Empresa")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Estado")
    position_in_queue = models.IntegerField(verbose_name="Posición en Cola")
    parte_numero = models.IntegerField(default=1, verbose_name="Número de Parte")
    total_partes = models.IntegerField(default=1, verbose_name="Total de Partes")
    rango_equipos_inicio = models.IntegerField(null=True, blank=True, verbose_name="Código Equipo Inicio")
    rango_equipos_fin = models.IntegerField(null=True, blank=True, verbose_name="Código Equipo Fin")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creado en")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Iniciado en")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Completado en")

    # Archivo generado
    file_path = models.CharField(max_length=500, null=True, blank=True, verbose_name="Ruta del Archivo")
    file_size = models.BigIntegerField(null=True, blank=True, verbose_name="Tamaño del Archivo (bytes)")

    # Información adicional
    error_message = models.TextField(null=True, blank=True, verbose_name="Mensaje de Error")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Expira en")

    # Campos para progreso en tiempo real (Fase 3)
    progress_percentage = models.IntegerField(default=0, verbose_name="Progreso (%)")
    current_step = models.CharField(max_length=200, null=True, blank=True, verbose_name="Paso Actual")
    total_equipos = models.IntegerField(null=True, blank=True, verbose_name="Total de Equipos")
    equipos_procesados = models.IntegerField(default=0, verbose_name="Equipos Procesados")
    estimated_completion = models.DateTimeField(null=True, blank=True, verbose_name="Tiempo Estimado de Finalización")

    def get_current_position(self):
        """Obtiene la posición actual en la cola."""
        if self.status not in ['pending', 'processing']:
            return None
        return self.position_in_queue

    def get_estimated_wait_time(self):
        """Obtiene el tiempo estimado de espera."""
        if self.estimated_completion:
            return self.estimated_completion.strftime('%H:%M:%S')
        return "Calculando..."

    def get_time_until_ready(self):
        """Obtiene el tiempo hasta que esté listo."""
        if self.status == 'completed':
            return "Listo"
        elif self.status == 'failed':
            return "Error"
        elif self.status == 'expired':
            return "Expirado"
        else:
            return self.get_estimated_wait_time()

    def get_detailed_status_message(self):
        """Obtiene un mensaje detallado del estado."""
        status_messages = {
            'pending': f'En cola - Posición {self.position_in_queue}',
            'processing': f'Procesando - {self.progress_percentage}% completado',
            'completed': 'ZIP listo para descarga',
            'failed': f'Error: {self.error_message or "Error desconocido"}',
            'expired': 'El archivo ha expirado',
        }
        return status_messages.get(self.status, 'Estado desconocido')

    class Meta:
        verbose_name = "Solicitud de ZIP"
        verbose_name_plural = "Solicitudes de ZIP"
        ordering = ['position_in_queue', 'created_at']


class NotificacionZip(models.Model):
    """Modelo para notificaciones push de ZIPs completados."""

    TIPO_CHOICES = [
        ('zip_ready', 'ZIP Listo'),
        ('zip_failed', 'ZIP Falló'),
        ('zip_expired', 'ZIP Expirado'),
    ]

    STATUS_CHOICES = [
        ('unread', 'No Leída'),
        ('read', 'Leída'),
        ('dismissed', 'Descartada'),
    ]

    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, verbose_name="Usuario")
    zip_request = models.ForeignKey('ZipRequest', on_delete=models.CASCADE, verbose_name="Solicitud ZIP")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unread', verbose_name="Estado")

    titulo = models.CharField(max_length=200, verbose_name="Título")
    mensaje = models.TextField(verbose_name="Mensaje")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creado en")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Leído en")

    class Meta:
        verbose_name = "Notificación ZIP"
        verbose_name_plural = "Notificaciones ZIP"
        ordering = ['-created_at']

    def __str__(self):
        return f"Notificación {self.tipo} - {self.user.username} - {self.get_status_display()}"
