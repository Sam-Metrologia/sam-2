# core/models/loans.py
# Modelos: AgrupacionPrestamo, PrestamoEquipo

from django.db import models
from django.utils import timezone
from core.constants import (
    PRESTAMO_ACTIVO, PRESTAMO_DEVUELTO, PRESTAMO_VENCIDO,
    PRESTAMO_CANCELADO, PRESTAMO_ESTADO_CHOICES,
)
from .users import CustomUser


class AgrupacionPrestamo(models.Model):
    """
    Agrupación opcional para múltiples préstamos relacionados
    Ejemplo: Prestar varios termómetros a la vez para un proceso específico
    """
    nombre = models.CharField(
        max_length=255,
        verbose_name="Nombre de la Agrupación",
        help_text="Ej: Set Termómetros Proceso A"
    )
    prestatario_nombre = models.CharField(
        max_length=255,
        verbose_name="Nombre del Prestatario"
    )
    empresa = models.ForeignKey(
        'Empresa',
        on_delete=models.CASCADE,
        related_name='agrupaciones_prestamo',
        verbose_name="Empresa"
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )

    class Meta:
        verbose_name = "Agrupación de Préstamo"
        verbose_name_plural = "Agrupaciones de Préstamos"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.nombre} - {self.prestatario_nombre}"


class PrestamoEquipo(models.Model):
    """
    Registro de préstamos de equipos a personal interno o externo
    con trazabilidad completa y verificación funcional
    """
    # Usar constantes centralizadas (importadas desde constants.py)
    # ESTADO_CHOICES removido - usar PRESTAMO_ESTADO_CHOICES desde constants.py

    # Información del equipo
    equipo = models.ForeignKey(
        'Equipo',
        on_delete=models.CASCADE,
        related_name='prestamos',
        verbose_name="Equipo"
    )
    empresa = models.ForeignKey(
        'Empresa',
        on_delete=models.CASCADE,
        related_name='prestamos_equipos',
        verbose_name="Empresa"
    )

    # Información del prestatario
    nombre_prestatario = models.CharField(
        max_length=255,
        verbose_name="Nombre del Prestatario"
    )
    cedula_prestatario = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Cédula del Prestatario"
    )
    cargo_prestatario = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Cargo del Prestatario"
    )
    email_prestatario = models.EmailField(
        blank=True,
        verbose_name="Email del Prestatario"
    )
    telefono_prestatario = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Teléfono del Prestatario"
    )

    # Fechas del préstamo
    fecha_prestamo = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha de Préstamo"
    )
    fecha_devolucion_programada = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Devolución Programada"
    )
    fecha_devolucion_real = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Devolución Real"
    )

    # Estado y control
    estado_prestamo = models.CharField(
        max_length=20,
        choices=PRESTAMO_ESTADO_CHOICES,
        default=PRESTAMO_ACTIVO,
        verbose_name="Estado del Préstamo"
    )

    # Verificación funcional
    verificacion_salida = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Verificación Funcional de Salida",
        help_text="Datos de verificación funcional al momento del préstamo"
    )
    verificacion_entrada = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Verificación Funcional de Entrada",
        help_text="Datos de verificación funcional al momento de devolución"
    )

    # Historial y actividades
    actividades_realizadas = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Actividades Realizadas",
        help_text="Historial de actividades realizadas con el equipo durante préstamo"
    )

    # Documentos
    documento_prestamo = models.FileField(
        upload_to='prestamos/',
        null=True,
        blank=True,
        verbose_name="Acta de Préstamo (PDF)"
    )
    documento_devolucion = models.FileField(
        upload_to='prestamos/',
        null=True,
        blank=True,
        verbose_name="Acta de Devolución (PDF)"
    )

    # Observaciones
    observaciones_prestamo = models.TextField(
        blank=True,
        verbose_name="Observaciones del Préstamo"
    )
    observaciones_devolucion = models.TextField(
        blank=True,
        verbose_name="Observaciones de la Devolución"
    )

    # Usuarios responsables
    prestado_por = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='prestamos_autorizados',
        verbose_name="Prestado por"
    )
    recibido_por = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devoluciones_recibidas',
        verbose_name="Recibido por"
    )

    # Agrupación opcional
    agrupacion = models.ForeignKey(
        'AgrupacionPrestamo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prestamos',
        verbose_name="Agrupación",
        help_text="Opcional: agrupa múltiples préstamos relacionados"
    )

    # Timestamps
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Registro"
    )

    class Meta:
        verbose_name = "Préstamo de Equipo"
        verbose_name_plural = "Préstamos de Equipos"
        ordering = ['-fecha_prestamo']
        permissions = [
            ('can_view_prestamo', 'Can view préstamo'),
            ('can_add_prestamo', 'Can add préstamo'),
            ('can_change_prestamo', 'Can change préstamo'),
            ('can_delete_prestamo', 'Can delete préstamo'),
            ('can_view_all_prestamos', 'Can view all company préstamos'),
        ]

    def __str__(self):
        return f"Préstamo {self.equipo.codigo_interno} - {self.nombre_prestatario} ({self.get_estado_prestamo_display()})"

    @property
    def esta_vencido(self):
        """Verifica si el préstamo está vencido"""
        if self.estado_prestamo == PRESTAMO_ACTIVO and self.fecha_devolucion_programada:
            return timezone.now().date() > self.fecha_devolucion_programada
        return False

    @property
    def dias_en_prestamo(self):
        """Calcula la duración del préstamo en días"""
        if self.fecha_devolucion_real:
            return (self.fecha_devolucion_real - self.fecha_prestamo).days
        else:
            return (timezone.now() - self.fecha_prestamo).days

    def devolver(self, user, verificacion_entrada_datos, observaciones=''):
        """
        Registra la devolución del equipo.

        Args:
            user: Usuario que recibe la devolución
            verificacion_entrada_datos: Dict con datos de verificación de entrada
            observaciones: Observaciones adicionales de la devolución
        """
        self.fecha_devolucion_real = timezone.now()
        self.estado_prestamo = PRESTAMO_DEVUELTO
        self.recibido_por = user
        self.verificacion_entrada = verificacion_entrada_datos
        if observaciones:
            self.observaciones_devolucion = observaciones
        self.save()

    def cancelar(self, user, motivo=''):
        """
        Cancela el préstamo (solo si está activo).

        Args:
            user: Usuario que cancela
            motivo: Motivo de la cancelación
        """
        if self.estado_prestamo == PRESTAMO_ACTIVO:
            self.estado_prestamo = PRESTAMO_CANCELADO
            self.recibido_por = user
            self.fecha_devolucion_real = timezone.now()
            if motivo:
                self.observaciones_devolucion = f"CANCELADO: {motivo}"
            self.save()
