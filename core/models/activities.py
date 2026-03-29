# core/models/activities.py
# Modelos: Calibracion, Mantenimiento, Comprobacion

from django.db import models
from .equipment import Equipo
from .catalogs import Proveedor
from .common import get_upload_path, meses_decimales_a_relativedelta


class Calibracion(models.Model):
    """Modelo para registrar las calibraciones de un equipo."""
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='calibraciones')
    fecha_calibracion = models.DateField(verbose_name="Fecha de Calibración")
    # Para vincular al proveedor general:
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True, related_name='calibraciones_realizadas', limit_choices_to={'tipo_servicio__in': ['Calibración', 'Otro']}) # Ajuste en limit_choices_to
    nombre_proveedor = models.CharField(max_length=255, blank=True, null=True, help_text="Nombre del proveedor si no está en la lista.")
    resultado = models.CharField(max_length=100, choices=[('Aprobado', 'Aprobado'), ('No Aprobado', 'No Aprobado')])
    numero_certificado = models.CharField(max_length=100, blank=True, null=True)
    documento_calibracion = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Documento de Calibración (PDF)")
    confirmacion_metrologica_pdf = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Confirmación Metrológica (PDF)")
    intervalos_calibracion_pdf = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Intervalos de Calibración (PDF)") # Nuevo campo
    confirmacion_metrologica_datos = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Datos de Confirmación Metrológica",
        help_text="Datos JSON con puntos de medición, incertidumbres y cálculos"
    )
    intervalos_calibracion_datos = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Datos de Intervalos de Calibración",
        help_text="Datos JSON con método, cálculos y decisión de intervalos"
    )
    observaciones = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # Campos para Dashboard de Gerencia
    costo_calibracion = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Costo de Calibración",
        help_text="Costo total de la calibración"
    )
    tiempo_empleado_horas = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Tiempo Empleado (Horas)",
        help_text="Horas empleadas en la calibración"
    )
    tecnico_asignado_sam = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Técnico Asignado",
        help_text="Técnico que supervisó la calibración"
    )

    # Sistema de Aprobación - Usuario que creó los documentos
    creado_por = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calibraciones_creadas',
        verbose_name="Creado por",
        help_text="Usuario que creó el documento"
    )

    # DEPRECATED: Campos legacy mantenidos por compatibilidad
    # Usar confirmacion_* o intervalos_* según el tipo de documento
    aprobado_por = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calibraciones_aprobadas',
        verbose_name="Aprobado por (legacy)",
        help_text="DEPRECATED - Usar confirmacion_aprobado_por o intervalos_aprobado_por"
    )
    fecha_aprobacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Aprobación (legacy)"
    )
    estado_aprobacion = models.CharField(
        max_length=20,
        choices=[
            ('pendiente', 'Pendiente de Aprobación'),
            ('aprobado', 'Aprobado'),
            ('rechazado', 'Rechazado')
        ],
        default='pendiente',
        verbose_name="Estado de Aprobación (legacy)"
    )
    observaciones_rechazo = models.TextField(
        null=True,
        blank=True,
        verbose_name="Observaciones de Rechazo (legacy)"
    )

    # Sistema de Aprobación - CONFIRMACIÓN METROLÓGICA
    confirmacion_estado_aprobacion = models.CharField(
        max_length=20,
        choices=[
            ('pendiente', 'Pendiente de Aprobación'),
            ('aprobado', 'Aprobado'),
            ('rechazado', 'Rechazado')
        ],
        default='pendiente',
        null=True,
        blank=True,
        verbose_name="Estado de Aprobación - Confirmación"
    )
    confirmacion_aprobado_por = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmaciones_aprobadas',
        verbose_name="Aprobado por - Confirmación"
    )
    confirmacion_fecha_aprobacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Aprobación - Confirmación"
    )
    confirmacion_observaciones_rechazo = models.TextField(
        null=True,
        blank=True,
        verbose_name="Observaciones de Rechazo - Confirmación"
    )

    # Fechas ajustables para auditoría - CONFIRMACIÓN
    confirmacion_fecha_realizacion = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Realización - Confirmación",
        help_text="Fecha en que se realizó la actividad (ajustable para auditoría)"
    )
    confirmacion_fecha_emision = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Emisión PDF - Confirmación",
        help_text="Fecha de emisión del documento (ajustable para auditoría)"
    )
    confirmacion_fecha_aprobacion_ajustable = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Aprobación Ajustable - Confirmación",
        help_text="Fecha de aprobación mostrada en PDF (ajustable para auditoría)"
    )

    # Sistema de Aprobación - INTERVALOS DE CALIBRACIÓN
    intervalos_estado_aprobacion = models.CharField(
        max_length=20,
        choices=[
            ('pendiente', 'Pendiente de Aprobación'),
            ('aprobado', 'Aprobado'),
            ('rechazado', 'Rechazado')
        ],
        default='pendiente',
        null=True,
        blank=True,
        verbose_name="Estado de Aprobación - Intervalos"
    )
    intervalos_aprobado_por = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='intervalos_aprobados',
        verbose_name="Aprobado por - Intervalos"
    )
    intervalos_fecha_aprobacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Aprobación - Intervalos"
    )
    intervalos_observaciones_rechazo = models.TextField(
        null=True,
        blank=True,
        verbose_name="Observaciones de Rechazo - Intervalos"
    )

    # Fechas ajustables para auditoría - INTERVALOS
    intervalos_fecha_realizacion = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Realización - Intervalos",
        help_text="Fecha en que se realizó la actividad (ajustable para auditoría)"
    )
    intervalos_fecha_emision = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Emisión PDF - Intervalos",
        help_text="Fecha de emisión del documento (ajustable para auditoría)"
    )
    intervalos_fecha_aprobacion_ajustable = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Aprobación Ajustable - Intervalos",
        help_text="Fecha de aprobación mostrada en PDF (ajustable para auditoría)"
    )

    class Meta:
        verbose_name = "Calibración"
        verbose_name_plural = "Calibraciones"
        permissions = [
            ("can_view_calibracion", "Can view calibracion"),
            ("can_add_calibracion", "Can add calibracion"),
            ("can_change_calibracion", "Can change calibracion"),
            ("can_delete_calibracion", "Can delete calibracion"),
        ]

    def __str__(self):
        return f"Calibración de {self.equipo.nombre} ({self.fecha_calibracion})"

    @property
    def proxima_actividad_para_este_registro(self):
        """
        Calcula la próxima fecha de calibración basada en la fecha de esta calibración
        y la frecuencia de calibración del equipo.
        """
        if not self.equipo.frecuencia_calibracion_meses or not self.fecha_calibracion:
            return None
        return self.fecha_calibracion + meses_decimales_a_relativedelta(self.equipo.frecuencia_calibracion_meses)

class Mantenimiento(models.Model):
    """Modelo para registrar los mantenimientos de un equipo."""
    TIPO_MANTENIMIENTO_CHOICES = [
        ('Preventivo', 'Preventivo'),
        ('Correctivo', 'Correctivo'),
        ('Predictivo', 'Predictivo'),
        ('Inspección', 'Inspección'),
        ('Otro', 'Otro'),
    ]
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='mantenimientos')
    fecha_mantenimiento = models.DateField(verbose_name="Fecha de Mantenimiento")
    tipo_mantenimiento = models.CharField(max_length=50, choices=TIPO_MANTENIMIENTO_CHOICES)
    # Para vincular al proveedor general:
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True, related_name='mantenimientos_realizados', limit_choices_to={'tipo_servicio__in': ['Mantenimiento', 'Otro']}) # Ajuste en limit_choices_to
    nombre_proveedor = models.CharField(max_length=255, blank=True, null=True, help_text="Nombre del proveedor si no está en la lista.")
    responsable = models.CharField(max_length=255, blank=True, null=True, help_text="Persona o entidad que realizó el mantenimiento.")
    costo = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True, help_text="Descripción detallada del mantenimiento realizado.")
    documento_mantenimiento = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Documento de Mantenimiento (PDF)")
    actividades_realizadas = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Actividades Realizadas",
        help_text="Actividades detalladas del mantenimiento en formato JSON"
    )
    documento_externo = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Documento Externo (Proveedor)")
    documento_interno = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Documento Interno (SAM)")
    observaciones = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # Campos adicionales para Dashboard de Gerencia
    tiempo_empleado_horas = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Tiempo Empleado (Horas)",
        help_text="Horas empleadas en el mantenimiento"
    )
    tecnico_asignado_sam = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Técnico Asignado",
        help_text="Técnico que supervisó el mantenimiento"
    )
    costo_sam_interno = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Costo Interno",
        help_text="Costo interno para realizar este mantenimiento"
    )

    # Fechas ajustables para auditoría - MANTENIMIENTO
    fecha_realizacion = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Realización",
        help_text="Fecha en que se realizó la actividad (ajustable para auditoría)"
    )
    fecha_emision = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Emisión PDF",
        help_text="Fecha de emisión del documento (ajustable para auditoría)"
    )
    fecha_aprobacion_ajustable = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Aprobación Ajustable",
        help_text="Fecha de aprobación mostrada en PDF (ajustable para auditoría)"
    )

    class Meta:
        verbose_name = "Mantenimiento"
        verbose_name_plural = "Mantenimientos"
        permissions = [
            ("can_view_mantenimiento", "Can view mantenimiento"),
            ("can_add_mantenimiento", "Can add mantenimiento"),
            ("can_change_mantenimiento", "Can change mantenimiento"),
            ("can_delete_mantenimiento", "Can delete mantenimiento"),
        ]

    def __str__(self):
        return f"Mantenimiento de {self.equipo.nombre} ({self.fecha_mantenimiento})"

    @property
    def proxima_actividad_para_este_registro(self):
        """
        Calcula la próxima fecha de mantenimiento basada en la fecha de este mantenimiento
        y la frecuencia de mantenimiento del equipo.
        """
        if not self.equipo.frecuencia_mantenimiento_meses or not self.fecha_mantenimiento:
            return None
        return self.fecha_mantenimiento + meses_decimales_a_relativedelta(self.equipo.frecuencia_mantenimiento_meses)

class Comprobacion(models.Model):
    """Modelo para registrar las comprobaciones (verificaciones intermedias) de un equipo."""
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='comprobaciones')
    fecha_comprobacion = models.DateField(verbose_name="Fecha de Comprobación")
    # Para vincular al proveedor general:
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True, related_name='comprobaciones_realizadas', limit_choices_to={'tipo_servicio__in': ['Comprobación', 'Otro']}) # Ajuste en limit_choices_to
    nombre_proveedor = models.CharField(max_length=255, blank=True, null=True, help_text="Nombre del proveedor si no está en la lista.")
    responsable = models.CharField(max_length=255, blank=True, null=True, help_text="Persona que realizó la comprobación.")
    resultado = models.CharField(max_length=100, choices=[('Aprobado', 'Aprobado'), ('No Aprobado', 'No Aprobado')])
    observaciones = models.TextField(blank=True, null=True)
    documento_comprobacion = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Documento de Comprobación (PDF)")
    comprobacion_pdf = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="PDF de Comprobación Metrológica")
    datos_comprobacion = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Datos de Comprobación Metrológica",
        help_text="Datos JSON con puntos de medición, tolerancias y conformidad"
    )
    documento_externo = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Documento Externo (Proveedor)")
    documento_interno = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Documento Interno (SAM)")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # Campos adicionales para Dashboard de Gerencia
    costo_comprobacion = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Costo de Comprobación",
        help_text="Costo total de la comprobación"
    )
    tiempo_empleado_horas = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Tiempo Empleado (Horas)",
        help_text="Horas empleadas en la comprobación"
    )
    tecnico_asignado_sam = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Técnico Asignado",
        help_text="Técnico que supervisó la comprobación"
    )

    # Campos para Equipo de Referencia (usado en comprobaciones)
    equipo_referencia_nombre = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Equipo de Referencia - Nombre",
        help_text="Nombre del equipo de referencia utilizado en la comprobación"
    )
    equipo_referencia_marca = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Equipo de Referencia - Marca",
        help_text="Marca del equipo de referencia"
    )
    equipo_referencia_modelo = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Equipo de Referencia - Modelo",
        help_text="Modelo del equipo de referencia"
    )
    equipo_referencia_certificado = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Equipo de Referencia - Certificado de Calibración",
        help_text="Número de certificado de calibración del equipo de referencia"
    )
    equipos_referencia_adicionales = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Equipos de Referencia Adicionales",
        help_text="Lista de equipos de referencia adicionales (nombre, marca, modelo, certificado)"
    )

    # Sistema de Aprobación
    creado_por = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comprobaciones_creadas',
        verbose_name="Creado por",
        help_text="Usuario que creó el documento"
    )
    aprobado_por = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comprobaciones_aprobadas',
        verbose_name="Aprobado por",
        help_text="Usuario que aprobó la comprobación"
    )
    fecha_aprobacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Aprobación"
    )
    estado_aprobacion = models.CharField(
        max_length=20,
        choices=[
            ('pendiente', 'Pendiente de Aprobación'),
            ('aprobado', 'Aprobado'),
            ('rechazado', 'Rechazado')
        ],
        default='pendiente',
        null=True,
        blank=True,
        verbose_name="Estado de Aprobación"
    )
    observaciones_rechazo = models.TextField(
        null=True,
        blank=True,
        verbose_name="Observaciones de Rechazo",
        help_text="Razón por la cual se rechazó el documento"
    )

    # Fechas ajustables para auditoría - COMPROBACIÓN
    fecha_realizacion = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Realización",
        help_text="Fecha en que se realizó la actividad (ajustable para auditoría)"
    )
    fecha_emision = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Emisión PDF",
        help_text="Fecha de emisión del documento (ajustable para auditoría)"
    )
    fecha_aprobacion_ajustable = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Aprobación Ajustable",
        help_text="Fecha de aprobación mostrada en PDF (ajustable para auditoría)"
    )

    # Consecutivo único por empresa
    consecutivo = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Consecutivo (interno)",
        help_text="Número consecutivo interno de comprobación por empresa"
    )

    consecutivo_texto = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Consecutivo",
        help_text="Consecutivo visible en el PDF (texto libre, ej: CB-001, COMP-2026-01)"
    )

    # Empresa cliente (para comprobaciones a terceros)
    es_servicio_terceros = models.BooleanField(
        default=False,
        verbose_name="Servicio a terceros",
        help_text="Indica si esta comprobación es un servicio para un cliente externo"
    )
    empresa_cliente = models.ForeignKey(
        'Empresa',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comprobaciones_como_cliente',
        verbose_name="Empresa Cliente (existente)",
        help_text="Empresa cliente registrada en el sistema"
    )
    empresa_cliente_nombre = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Nombre Empresa Cliente",
        help_text="Nombre de la empresa cliente (si no está registrada)"
    )
    empresa_cliente_nit = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="NIT Empresa Cliente",
        help_text="NIT de la empresa cliente"
    )
    empresa_cliente_direccion = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Dirección Empresa Cliente",
        help_text="Dirección de la empresa cliente"
    )

    class Meta:
        verbose_name = "Comprobación"
        verbose_name_plural = "Comprobaciones"
        permissions = [
            ("can_view_comprobacion", "Can view comprobacion"),
            ("can_add_comprobacion", "Can add comprobacion"),
            ("can_change_comprobacion", "Can change comprobacion"),
            ("can_delete_comprobacion", "Can delete comprobacion"),
        ]

    def save(self, *args, **kwargs):
        # Auto-generar consecutivo numérico por empresa si no existe
        if self.consecutivo is None and self.equipo and self.equipo.empresa:
            empresa = self.equipo.empresa
            ultimo = Comprobacion.objects.filter(
                equipo__empresa=empresa,
                consecutivo__isnull=False
            ).order_by('-consecutivo').values_list('consecutivo', flat=True).first()
            self.consecutivo = (ultimo or 0) + 1

        # Auto-generar consecutivo_texto si no se proporcionó
        if not self.consecutivo_texto and self.consecutivo is not None and self.equipo and self.equipo.empresa:
            prefijo = self.equipo.empresa.comprobacion_prefijo_consecutivo or 'CB'
            self.consecutivo_texto = f"{prefijo}-{self.consecutivo:03d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Comprobación de {self.equipo.nombre} ({self.fecha_comprobacion})"

    @property
    def consecutivo_formateado(self):
        """Retorna el consecutivo visible. Prioriza texto libre, luego formato automático."""
        if self.consecutivo_texto:
            return self.consecutivo_texto
        if self.consecutivo is None:
            return ''
        prefijo = 'CB'
        if self.equipo and self.equipo.empresa:
            prefijo = self.equipo.empresa.comprobacion_prefijo_consecutivo or 'CB'
        return f"{prefijo}-{self.consecutivo:03d}"

    @property
    def nombre_empresa_cliente_display(self):
        """Retorna el nombre de la empresa cliente (existente o manual)."""
        if self.empresa_cliente:
            return self.empresa_cliente.nombre
        return self.empresa_cliente_nombre or ''

    @property
    def nit_empresa_cliente_display(self):
        """Retorna el NIT de la empresa cliente (existente o manual)."""
        if self.empresa_cliente:
            return self.empresa_cliente.nit or ''
        return self.empresa_cliente_nit or ''

    @property
    def direccion_empresa_cliente_display(self):
        """Retorna la dirección de la empresa cliente (existente o manual)."""
        if self.empresa_cliente:
            return self.empresa_cliente.direccion or ''
        return self.empresa_cliente_direccion or ''

    @property
    def proxima_actividad_para_este_registro(self):
        """
        Calcula la próxima fecha de comprobación basada en la fecha de esta comprobación
        y la frecuencia de comprobación del equipo.
        """
        if not self.equipo.frecuencia_comprobacion_meses or not self.fecha_comprobacion:
            return None
        return self.fecha_comprobacion + meses_decimales_a_relativedelta(self.equipo.frecuencia_comprobacion_meses)
