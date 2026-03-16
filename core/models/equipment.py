# core/models/equipment.py
# Modelos: Equipo, BajaEquipo, NotificacionVencimiento

from django.db import models
from django.conf import settings
from django.utils import timezone
from core.constants import (
    ESTADO_ACTIVO, ESTADO_INACTIVO, ESTADO_EN_CALIBRACION,
    ESTADO_EN_COMPROBACION, ESTADO_EN_MANTENIMIENTO, ESTADO_DE_BAJA,
    ESTADO_EN_PRESTAMO, EQUIPO_ESTADO_CHOICES,
    PRESTAMO_ACTIVO,
)
from .empresa import Empresa
from .common import get_upload_path, meses_decimales_a_relativedelta


class Equipo(models.Model):
    """Modelo para representar un equipo o instrumento de metrología."""
    TIPO_EQUIPO_CHOICES = [
        ('Equipo de Medición', 'Equipo de Medición'),
        ('Equipo de Referencia', 'Equipo de Referencia'),
        ('Equipo Auxiliar', 'Equipo Auxiliar'),
        ('Otro', 'Otro'),
    ]

    # Usar constantes centralizadas (importadas desde constants.py)
    # Referencia a constante para compatibilidad con tests
    ESTADO_CHOICES = EQUIPO_ESTADO_CHOICES

    codigo_interno = models.CharField(max_length=100, unique=False, help_text="Código interno único por empresa.") # Se valida la unicidad a nivel de formulario/vista
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Equipo")
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='equipos', verbose_name="Empresa")
    tipo_equipo = models.CharField(max_length=50, choices=TIPO_EQUIPO_CHOICES, verbose_name="Tipo de Equipo")
    marca = models.CharField(max_length=100, blank=True, null=True, verbose_name="Marca")
    modelo = models.CharField(max_length=100, blank=True, null=True, verbose_name="Modelo")
    numero_serie = models.CharField(max_length=100, blank=True, null=True, verbose_name="Número de Serie")
    proveedor = models.CharField(max_length=200, blank=True, null=True, verbose_name="Proveedor", help_text="Empresa que vendió el equipo (ej: Multiples, Amazon, etc.)")

    # Campo para la ubicación - ahora como TextField
    ubicacion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ubicación") # Ahora CharField

    responsable = models.CharField(max_length=100, blank=True, null=True, verbose_name="Responsable")
    estado = models.CharField(max_length=50, choices=EQUIPO_ESTADO_CHOICES, default=ESTADO_ACTIVO, verbose_name="Estado")
    fecha_adquisicion = models.DateField(blank=True, null=True, verbose_name="Fecha de Adquisición")
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")

    rango_medida = models.CharField(max_length=100, blank=True, null=True, verbose_name="Rango de Medida")
    resolucion = models.CharField(max_length=100, blank=True, null=True, verbose_name="Resolución")
    error_maximo_permisible = models.CharField(max_length=100, blank=True, null=True, verbose_name="Error Máximo Permisible") # Ahora CharField
    puntos_calibracion = models.TextField(blank=True, null=True, verbose_name="Puntos de Calibración")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")

    # Documentos del Equipo (usando get_upload_path)
    archivo_compra_pdf = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Archivo de Compra (PDF)")
    ficha_tecnica_pdf = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Ficha Técnica (PDF)")
    manual_pdf = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Manual (PDF)")
    otros_documentos_pdf = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Otros Documentos (PDF)")
    imagen_equipo = models.ImageField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Imagen del Equipo") # Un solo campo para imagen

    # Campos de formato (para hoja de vida)
    version_formato = models.CharField(max_length=50, blank=True, null=True, verbose_name="Versión del Formato")
    fecha_version_formato = models.DateField(blank=True, null=True, verbose_name="Fecha de Versión del Formato")
    fecha_version_formato_display = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name="Fecha Formato Display - Hoja de Vida",
        help_text="Formato de fecha para mostrar (YYYY-MM o YYYY-MM-DD)"
    )
    codificacion_formato = models.CharField(max_length=50, blank=True, null=True, verbose_name="Codificación del Formato")

    # Campos para fechas de próximas actividades y frecuencias (Frecuencia en DecimalField)
    fecha_ultima_calibracion = models.DateField(blank=True, null=True, verbose_name="Fecha Última Calibración")
    proxima_calibracion = models.DateField(blank=True, null=True, verbose_name="Próxima Calibración")
    frecuencia_calibracion_meses = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Frecuencia Calibración (meses)")

    fecha_ultimo_mantenimiento = models.DateField(blank=True, null=True, verbose_name="Fecha Último Mantenimiento")
    proximo_mantenimiento = models.DateField(blank=True, null=True, verbose_name="Próximo Mantenimiento")
    frecuencia_mantenimiento_meses = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Frecuencia Mantenimiento (meses)")

    fecha_ultima_comprobacion = models.DateField(blank=True, null=True, verbose_name="Fecha Última Comprobación")
    proxima_comprobacion = models.DateField(blank=True, null=True, verbose_name="Próxima Comprobación")
    frecuencia_comprobacion_meses = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Frecuencia Comprobación (meses)")

    class Meta:
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"
        ordering = ['codigo_interno']
        permissions = [
            ("can_view_equipo", "Can view equipo"),
            ("can_add_equipo", "Can add equipo"),
            ("can_change_equipo", "Can change equipo"),
            ("can_delete_equipo", "Can delete equipo"),
            ("can_export_reports", "Can export reports (PDF, Excel, ZIP)"), # NUEVO PERMISO
        ]
        # Restricción de unicidad a nivel de base de datos para 'codigo_interno' por 'empresa'
        unique_together = ('codigo_interno', 'empresa')


    def __str__(self):
        return f"{self.nombre} ({self.codigo_interno})"

    def save(self, *args, **kwargs):
        """
        Sobreescribe save para calcular las próximas fechas.
        Para equipos nuevos, primero se guarda y luego se calculan las fechas.
        """
        is_new = self.pk is None

        # Primero guardar el objeto
        super().save(*args, **kwargs)

        # Después calcular las próximas fechas (solo si el objeto ya tiene pk)
        if self.pk:
            # Inicializar fechas si es nuevo equipo
            if is_new:
                # Para equipos nuevos, usar las fechas proporcionadas como base
                self.calcular_proxima_calibracion_from_date(self.fecha_ultima_calibracion)
                self.calcular_proximo_mantenimiento_from_date(self.fecha_ultimo_mantenimiento)
                self.calcular_proxima_comprobacion_from_date(self.fecha_ultima_comprobacion)
            else:
                # Para equipos existentes, usar el historial
                self.calcular_proxima_calibracion()
                self.calcular_proximo_mantenimiento()
                self.calcular_proxima_comprobacion()

            # Guardar nuevamente solo las fechas calculadas
            super().save(update_fields=['proxima_calibracion', 'proximo_mantenimiento', 'proxima_comprobacion'])


    def calcular_proxima_calibracion(self):
        """Calcula la próxima fecha de calibración."""
        if self.estado in ['De Baja', 'Inactivo']: # Si está de baja o inactivo, no hay próxima actividad
            self.proxima_calibracion = None
            return

        if self.frecuencia_calibracion_meses is None or self.frecuencia_calibracion_meses <= 0:
            self.proxima_calibracion = None
            return

        latest_calibracion = self.calibraciones.order_by('-fecha_calibracion').first()

        # Si hay una última calibración, calcular a partir de ella
        if latest_calibracion and latest_calibracion.fecha_calibracion:
            # Usar función helper para manejar decimales correctamente
            delta = meses_decimales_a_relativedelta(self.frecuencia_calibracion_meses)
            self.proxima_calibracion = latest_calibracion.fecha_calibracion + delta
        else:
            # Si no hay calibraciones previas, proyectar desde la fecha de adquisición o registro del equipo
            base_date = self.fecha_adquisicion if self.fecha_adquisicion else self.fecha_registro.date()
            if base_date:
                delta = meses_decimales_a_relativedelta(self.frecuencia_calibracion_meses)
                self.proxima_calibracion = base_date + delta
            else:
                self.proxima_calibracion = None

    def calcular_proximo_mantenimiento(self):
        """Calcula la próxima fecha de mantenimiento."""
        if self.estado in ['De Baja', 'Inactivo']: # Si está de baja o inactivo, no hay próxima actividad
            self.proximo_mantenimiento = None
            return

        if self.frecuencia_mantenimiento_meses is None or self.frecuencia_mantenimiento_meses <= 0:
            self.proximo_mantenimiento = None
            return

        latest_mantenimiento = self.mantenimientos.order_by('-fecha_mantenimiento').first()

        if latest_mantenimiento and latest_mantenimiento.fecha_mantenimiento:
            delta = meses_decimales_a_relativedelta(self.frecuencia_mantenimiento_meses)
            self.proximo_mantenimiento = latest_mantenimiento.fecha_mantenimiento + delta
        else:
            # JERARQUÍA CORRECTA: 1. fecha_ultima_mantenimiento, 2. fecha_ultima_calibracion, 3. fecha_adquisicion, 4. fecha_registro
            if self.fecha_ultimo_mantenimiento:
                base_date = self.fecha_ultimo_mantenimiento
            elif self.fecha_ultima_calibracion:
                base_date = self.fecha_ultima_calibracion
            elif self.fecha_adquisicion:
                base_date = self.fecha_adquisicion
            else:
                base_date = self.fecha_registro.date()

            if base_date:
                delta = meses_decimales_a_relativedelta(self.frecuencia_mantenimiento_meses)
                self.proximo_mantenimiento = base_date + delta
            else:
                self.proximo_mantenimiento = None

    def calcular_proxima_comprobacion(self):
        """Calcula la próxima fecha de comprobación."""
        if self.estado in ['De Baja', 'Inactivo']: # Si está de baja o inactivo, no hay próxima actividad
            self.proxima_comprobacion = None
            return

        if self.frecuencia_comprobacion_meses is None or self.frecuencia_comprobacion_meses <= 0:
            self.proxima_comprobacion = None
            return

        latest_comprobacion = self.comprobaciones.order_by('-fecha_comprobacion').first()

        if latest_comprobacion and latest_comprobacion.fecha_comprobacion:
            delta = meses_decimales_a_relativedelta(self.frecuencia_comprobacion_meses)
            self.proxima_comprobacion = latest_comprobacion.fecha_comprobacion + delta
        else:
            # JERARQUÍA CORRECTA: 1. fecha_ultima_comprobacion, 2. fecha_ultima_calibracion, 3. fecha_adquisicion, 4. fecha_registro
            if self.fecha_ultima_comprobacion:
                base_date = self.fecha_ultima_comprobacion
            elif self.fecha_ultima_calibracion:
                base_date = self.fecha_ultima_calibracion
            elif self.fecha_adquisicion:
                base_date = self.fecha_adquisicion
            else:
                base_date = self.fecha_registro.date()

            if base_date:
                delta = meses_decimales_a_relativedelta(self.frecuencia_comprobacion_meses)
                self.proxima_comprobacion = base_date + delta
            else:
                self.proxima_comprobacion = None

    def calcular_proxima_calibracion_from_date(self, fecha_base):
        """Calcula la próxima fecha de calibración desde una fecha base específica."""
        if self.estado in ['De Baja', 'Inactivo']:
            self.proxima_calibracion = None
            return

        if self.frecuencia_calibracion_meses is None or self.frecuencia_calibracion_meses <= 0:
            self.proxima_calibracion = None
            return

        if fecha_base:
            delta = meses_decimales_a_relativedelta(self.frecuencia_calibracion_meses)
            self.proxima_calibracion = fecha_base + delta
        elif self.fecha_adquisicion:
            delta = meses_decimales_a_relativedelta(self.frecuencia_calibracion_meses)
            self.proxima_calibracion = self.fecha_adquisicion + delta
        elif self.fecha_registro:
            delta = meses_decimales_a_relativedelta(self.frecuencia_calibracion_meses)
            self.proxima_calibracion = self.fecha_registro.date() + delta
        else:
            self.proxima_calibracion = None

    def calcular_proximo_mantenimiento_from_date(self, fecha_base):
        """Calcula la próxima fecha de mantenimiento desde una fecha base específica."""
        if self.estado in ['De Baja', 'Inactivo']:
            self.proximo_mantenimiento = None
            return

        if self.frecuencia_mantenimiento_meses is None or self.frecuencia_mantenimiento_meses <= 0:
            self.proximo_mantenimiento = None
            return

        if fecha_base:
            delta = meses_decimales_a_relativedelta(self.frecuencia_mantenimiento_meses)
            self.proximo_mantenimiento = fecha_base + delta
        elif self.fecha_adquisicion:
            delta = meses_decimales_a_relativedelta(self.frecuencia_mantenimiento_meses)
            self.proximo_mantenimiento = self.fecha_adquisicion + delta
        elif self.fecha_registro:
            delta = meses_decimales_a_relativedelta(self.frecuencia_mantenimiento_meses)
            self.proximo_mantenimiento = self.fecha_registro.date() + delta
        else:
            self.proximo_mantenimiento = None

    def calcular_proxima_comprobacion_from_date(self, fecha_base):
        """Calcula la próxima fecha de comprobación desde una fecha base específica."""
        if self.estado in ['De Baja', 'Inactivo']:
            self.proxima_comprobacion = None
            return

        if self.frecuencia_comprobacion_meses is None or self.frecuencia_comprobacion_meses <= 0:
            self.proxima_comprobacion = None
            return

        if fecha_base:
            delta = meses_decimales_a_relativedelta(self.frecuencia_comprobacion_meses)
            self.proxima_comprobacion = fecha_base + delta
        elif self.fecha_adquisicion:
            delta = meses_decimales_a_relativedelta(self.frecuencia_comprobacion_meses)
            self.proxima_comprobacion = self.fecha_adquisicion + delta
        elif self.fecha_registro:
            delta = meses_decimales_a_relativedelta(self.frecuencia_comprobacion_meses)
            self.proxima_comprobacion = self.fecha_registro.date() + delta
        else:
            self.proxima_comprobacion = None

    @property
    def esta_prestado(self):
        """Verifica si el equipo está actualmente prestado."""
        return self.prestamos.filter(estado_prestamo=PRESTAMO_ACTIVO).exists()

    def get_prestamo_activo(self):
        """Obtiene el préstamo activo del equipo, si existe."""
        return self.prestamos.filter(estado_prestamo=PRESTAMO_ACTIVO).first()

    @property
    def responsable_actual(self):
        """
        Retorna el responsable actual del equipo:
        - Si está prestado: nombre del prestatario
        - Si está disponible: nombre de la empresa
        """
        prestamo_activo = self.get_prestamo_activo()
        if prestamo_activo:
            return prestamo_activo.nombre_prestatario
        return self.empresa.nombre if self.empresa else "Sin asignar"


class BajaEquipo(models.Model):
    """Modelo para registrar la baja definitiva de un equipo."""
    equipo = models.OneToOneField(Equipo, on_delete=models.CASCADE, related_name='baja_registro')
    fecha_baja = models.DateField(default=timezone.now, verbose_name="Fecha de Baja") # Ahora con default
    razon_baja = models.TextField(verbose_name="Razón de Baja")
    observaciones = models.TextField(blank=True, null=True)
    documento_baja = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Documento de Baja (PDF)")
    dado_de_baja_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Dado de baja por")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Baja de Equipo"
        verbose_name_plural = "Bajas de Equipo"
        permissions = [
            ("can_view_bajaequipo", "Can view baja equipo"),
            ("can_add_bajaequipo", "Can add baja equipo"),
            ("can_change_bajaequipo", "Can change baja equipo"),
            ("can_delete_bajaequipo", "Can delete baja equipo"),
        ]

    def __str__(self):
        return f"Baja de {self.equipo.nombre} ({self.fecha_baja})"


class NotificacionVencimiento(models.Model):
    """
    Modelo para rastrear notificaciones enviadas para equipos con actividades vencidas.
    Permite enviar recordatorios semanales hasta 3 veces máximo.
    """
    equipo = models.ForeignKey(
        'Equipo',
        on_delete=models.CASCADE,
        related_name='notificaciones_vencimiento',
        verbose_name="Equipo"
    )

    tipo_actividad = models.CharField(
        max_length=20,
        choices=[
            ('calibracion', 'Calibración'),
            ('mantenimiento', 'Mantenimiento'),
            ('comprobacion', 'Comprobación'),
        ],
        verbose_name="Tipo de Actividad"
    )

    fecha_vencimiento = models.DateField(
        verbose_name="Fecha de Vencimiento Original",
        help_text="Fecha en que venció la actividad"
    )

    fecha_notificacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Notificación Enviada"
    )

    numero_recordatorio = models.IntegerField(
        default=1,
        verbose_name="Número de Recordatorio",
        help_text="1 = primer recordatorio, 2 = segundo, 3 = tercero (máximo)"
    )

    actividad_completada = models.BooleanField(
        default=False,
        verbose_name="Actividad Completada",
        help_text="True si la actividad fue completada después de enviar notificación"
    )

    fecha_ultima_revision = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha Última Revisión",
        help_text="Fecha de la próxima actividad cuando se verificó por última vez"
    )

    class Meta:
        verbose_name = "Notificación de Vencimiento"
        verbose_name_plural = "Notificaciones de Vencimiento"
        ordering = ['-fecha_notificacion']
        indexes = [
            models.Index(fields=['equipo', 'tipo_actividad', 'fecha_vencimiento']),
            models.Index(fields=['fecha_notificacion']),
        ]

    def __str__(self):
        return f"{self.equipo.codigo_interno} - {self.tipo_actividad} - Recordatorio #{self.numero_recordatorio}"

    @classmethod
    def puede_enviar_recordatorio(cls, equipo, tipo_actividad, fecha_vencimiento):
        """
        Verifica si se puede enviar un nuevo recordatorio para un equipo y actividad.

        Retorna:
            (puede_enviar, numero_recordatorio) - tupla con booleano y número de recordatorio
        """
        from django.utils import timezone
        # Buscar última notificación para esta actividad
        ultima_notificacion = cls.objects.filter(
            equipo=equipo,
            tipo_actividad=tipo_actividad,
            fecha_vencimiento=fecha_vencimiento
        ).order_by('-numero_recordatorio').first()

        if not ultima_notificacion:
            # Primera vez que se envía notificación
            return (True, 1)

        # Verificar si ya se enviaron 3 recordatorios
        if ultima_notificacion.numero_recordatorio >= 3:
            return (False, None)

        # Verificar si han pasado al menos 7 días desde último recordatorio
        dias_desde_ultimo = (timezone.now().date() - ultima_notificacion.fecha_notificacion.date()).days
        if dias_desde_ultimo < 7:
            return (False, None)

        # Puede enviar el siguiente recordatorio
        return (True, ultima_notificacion.numero_recordatorio + 1)

    @classmethod
    def marcar_actividad_completada(cls, equipo, tipo_actividad, fecha_vencimiento_anterior):
        """
        Marca todas las notificaciones de una actividad como completadas cuando se realiza la actividad.
        """
        cls.objects.filter(
            equipo=equipo,
            tipo_actividad=tipo_actividad,
            fecha_vencimiento=fecha_vencimiento_anterior,
            actividad_completada=False
        ).update(actividad_completada=True)
