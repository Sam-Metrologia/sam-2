# core/models/lectura_ia.py
# Modelo: LecturaCertificado — lectura automática (Gemini) del PDF de una calibración.

from django.conf import settings
from django.db import models
from django.utils import timezone

from .activities import Calibracion
from .empresa import Empresa


class LecturaCertificado(models.Model):
    """
    Resultado de leer con IA el certificado (PDF) de una calibración.

    La lectura NO es la confirmación metrológica: es una propuesta que precarga
    el formulario de confirmación. Nada se da por bueno hasta que el técnico
    revisa y guarda la confirmación.

    El estado vive en base de datos para que una lectura sobreviva a un reinicio
    del servidor: si se queda en "procesando" demasiado tiempo se vuelve a tomar.
    """

    ESTADO_PENDIENTE = 'pendiente'
    ESTADO_PROCESANDO = 'procesando'
    ESTADO_LISTO = 'listo'
    ESTADO_FALLO = 'fallo'
    ESTADOS = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_PROCESANDO, 'Leyendo'),
        (ESTADO_LISTO, 'Lista para revisar'),
        (ESTADO_FALLO, 'Falló'),
    ]

    ORIGEN_INDIVIDUAL = 'individual'
    ORIGEN_MASIVA = 'masiva'
    ORIGENES = [
        (ORIGEN_INDIVIDUAL, 'Individual'),
        (ORIGEN_MASIVA, 'Masiva'),
    ]

    calibracion = models.OneToOneField(
        Calibracion, on_delete=models.CASCADE, related_name='lectura_ia')
    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name='lecturas_certificado')
    estado = models.CharField(max_length=12, choices=ESTADOS, default=ESTADO_PENDIENTE, db_index=True)
    origen = models.CharField(max_length=12, choices=ORIGENES, default=ORIGEN_INDIVIDUAL)
    solicitado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='lecturas_certificado')

    intentos = models.PositiveSmallIntegerField(default=0)
    modelo_ia = models.CharField(max_length=60, blank=True, default='')
    # Lo que devolvió Gemini tal cual (para auditoría y para reprocesar sin volver a pagar).
    resultado_crudo = models.JSONField(null=True, blank=True)
    # Datos ya convertidos al formato de la confirmación (v2) que precargan el formulario.
    propuesta = models.JSONField(null=True, blank=True)
    mensaje_error = models.TextField(blank=True, default='')

    tokens_entrada = models.PositiveIntegerField(default=0)
    tokens_salida = models.PositiveIntegerField(default=0)
    segundos = models.FloatField(default=0)

    creado = models.DateTimeField(auto_now_add=True)
    iniciado_en = models.DateTimeField(null=True, blank=True)
    terminado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Lectura de certificado (IA)'
        verbose_name_plural = 'Lecturas de certificado (IA)'
        ordering = ['-creado']

    def __str__(self):
        return f"Lectura {self.get_estado_display()} — calibración {self.calibracion_id}"

    @property
    def en_curso(self):
        return self.estado in (self.ESTADO_PENDIENTE, self.ESTADO_PROCESANDO)

    def marcar_fallo(self, mensaje):
        self.estado = self.ESTADO_FALLO
        self.mensaje_error = str(mensaje)[:2000]
        self.terminado_en = timezone.now()
        self.save(update_fields=['estado', 'mensaje_error', 'terminado_en'])
