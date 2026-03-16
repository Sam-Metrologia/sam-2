# core/models/empresa.py
# Modelos: Empresa, PlanSuscripcion

from django.db import models
from datetime import timedelta
from django.utils import timezone
import decimal
import logging
from dateutil.relativedelta import relativedelta
from core.constants import (
    MODALIDAD_GRATIS, MODALIDAD_PRUEBA, MODALIDAD_PAGO,
    MODALIDAD_PAGO_CHOICES,
)

logger = logging.getLogger('core')


class Empresa(models.Model):
    # Constantes para planes
    PLAN_GRATUITO_EQUIPOS = 5
    PLAN_GRATUITO_ALMACENAMIENTO_MB = 500  # 500MB para plan gratuito
    TRIAL_EQUIPOS = 50
    TRIAL_ALMACENAMIENTO_MB = 500  # 500MB para trial
    TRIAL_DURACION_DIAS = 30

    nombre = models.CharField(max_length=200, unique=True)
    nit = models.CharField(max_length=50, unique=True, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    correos_facturacion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Correos de Facturación",
        help_text="Correos adicionales para recibir facturas (separados por coma). Ej: admin@empresa.com, gerente@empresa.com"
    )
    correos_notificaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name="Correos de Notificaciones",
        help_text="Correos adicionales para notificaciones del sistema (separados por coma). Ej: tecnico@empresa.com, supervisor@empresa.com"
    )
    logo_empresa = models.ImageField(upload_to='empresas_logos/', blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # CAMBIO: Eliminado el campo 'limite_equipos' para usar solo 'limite_equipos_empresa'
    # limite_equipos = models.IntegerField(
    #     default=0,
    #     help_text="Número máximo de equipos que esta empresa puede registrar. 0 para ilimitado.",
    #     blank=True,
    #     null=True
    # )

    # Nuevos campos para la información de formato por empresa (DEPRECADOS - usar campos específicos)
    formato_version_empresa = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Versión del Formato (Empresa) - DEPRECADO"
    )
    formato_fecha_version_empresa = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de Versión del Formato (Empresa) - DEPRECADO"
    )
    formato_fecha_version_empresa_display = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name="Fecha Formato Display - Empresa (General)",
        help_text="Formato de fecha para mostrar (YYYY-MM o YYYY-MM-DD)"
    )
    formato_codificacion_empresa = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Codificación del Formato (Empresa) - DEPRECADO"
    )

    # Campos específicos para CONFIRMACIÓN METROLÓGICA
    confirmacion_codigo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="SAM-CONF-001",
        verbose_name="Código Formato - Confirmación Metrológica",
        help_text="Código del formato de confirmación metrológica (ej: SAM-CONF-001)"
    )
    confirmacion_version = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        default="01",
        verbose_name="Versión Formato - Confirmación Metrológica",
        help_text="Versión del formato de confirmación metrológica (ej: 01, 02, 03)"
    )
    confirmacion_fecha_formato = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha del Formato - Confirmación Metrológica",
        help_text="Fecha de emisión/actualización del formato de confirmación metrológica"
    )
    confirmacion_fecha_formato_display = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name="Fecha Formato Display - Confirmación",
        help_text="Formato de fecha para mostrar (YYYY-MM o YYYY-MM-DD)"
    )

    # Campos específicos para INTERVALOS DE CALIBRACIÓN
    intervalos_codigo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="SAM-INT-001",
        verbose_name="Código Formato - Intervalos de Calibración",
        help_text="Código del formato de intervalos de calibración (ej: SAM-INT-001)"
    )
    intervalos_version = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        default="01",
        verbose_name="Versión Formato - Intervalos de Calibración",
        help_text="Versión del formato de intervalos de calibración (ej: 01, 02, 03)"
    )
    intervalos_fecha_formato = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha del Formato - Intervalos de Calibración",
        help_text="Fecha de emisión/actualización del formato de intervalos de calibración"
    )
    intervalos_fecha_formato_display = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name="Fecha Formato Display - Intervalos",
        help_text="Formato de fecha para mostrar (YYYY-MM o YYYY-MM-DD)"
    )

    # Campos específicos para MANTENIMIENTO
    mantenimiento_codigo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="SAM-MANT-001",
        verbose_name="Código Formato - Mantenimiento",
        help_text="Código del formato de mantenimiento (ej: SAM-MANT-001)"
    )
    mantenimiento_version = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        default="01",
        verbose_name="Versión Formato - Mantenimiento",
        help_text="Versión del formato de mantenimiento (ej: 01, 02, 03)"
    )
    mantenimiento_fecha_formato = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha del Formato - Mantenimiento",
        help_text="Fecha de emisión/actualización del formato de mantenimiento"
    )
    mantenimiento_fecha_formato_display = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name="Fecha Formato Display - Mantenimiento",
        help_text="Formato de fecha para mostrar (YYYY-MM o YYYY-MM-DD)"
    )

    # Campos específicos para COMPROBACIÓN METROLÓGICA
    comprobacion_codigo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="SAM-COMP-001",
        verbose_name="Código Formato - Comprobación Metrológica",
        help_text="Código del formato de comprobación metrológica (ej: SAM-COMP-001)"
    )
    comprobacion_version = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        default="01",
        verbose_name="Versión Formato - Comprobación Metrológica",
        help_text="Versión del formato de comprobación metrológica (ej: 01, 02, 03)"
    )
    comprobacion_fecha_formato = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha del Formato - Comprobación Metrológica",
        help_text="Fecha de emisión/actualización del formato de comprobación metrológica"
    )
    comprobacion_fecha_formato_display = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name="Fecha Formato Display - Comprobación",
        help_text="Formato de fecha para mostrar (YYYY-MM o YYYY-MM-DD)"
    )
    comprobacion_observaciones_formato = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones del Formato - Comprobación",
        help_text="Observaciones o notas que aparecerán en todos los PDFs de comprobación metrológica"
    )

    # Campos específicos para LISTADO DE EQUIPOS
    listado_codigo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="SAM-LIST-001",
        verbose_name="Código Formato - Listado de Equipos",
        help_text="Código del formato de listado de equipos (ej: SAM-LIST-001)"
    )
    listado_version = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        default="01",
        verbose_name="Versión Formato - Listado de Equipos",
        help_text="Versión del formato de listado de equipos (ej: 01, 02, 03)"
    )
    listado_fecha_formato = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha del Formato - Listado de Equipos",
        help_text="Fecha de emisión/actualización del formato de listado de equipos"
    )
    listado_fecha_formato_display = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name="Fecha Formato Display - Listado de Equipos",
        help_text="Formato de fecha para mostrar (YYYY-MM o YYYY-MM-DD)"
    )

    # Prefijo para consecutivo de comprobaciones
    comprobacion_prefijo_consecutivo = models.CharField(
        max_length=10,
        default='CB',
        blank=True,
        verbose_name="Prefijo Consecutivo Comprobaciones",
        help_text="Prefijo para numerar comprobaciones (ej: CB, COMP). Resultado: CB-001, CB-002..."
    )

    # Campos para la lógica de suscripción (Simplificados - DEPRECADOS)
    es_periodo_prueba = models.BooleanField(default=True, verbose_name="¿Es Período de Prueba? (Deprecado)")
    duracion_prueba_dias = models.IntegerField(default=30, verbose_name="Duración Prueba (días)")
    fecha_inicio_plan = models.DateField(blank=True, null=True, verbose_name="Fecha Inicio Plan")

    # Campo para el límite de equipos (ahora el único y principal)
    limite_equipos_empresa = models.IntegerField(default=50, verbose_name="Límite Máximo de Equipos")
    duracion_suscripcion_meses = models.IntegerField(default=12, blank=True, null=True, verbose_name="Duración Suscripción (meses)")

    # Campos para límites de almacenamiento
    limite_almacenamiento_mb = models.IntegerField(
        default=1024,  # 1GB por defecto
        verbose_name="Límite de Almacenamiento (MB)",
        help_text="Límite máximo de almacenamiento en megabytes para archivos de la empresa"
    )

    limite_usuarios_empresa = models.IntegerField(
        default=3,
        verbose_name="Límite de Usuarios",
        help_text="Máximo de usuarios activos permitidos. Base: 3 (técnico, admin, gerente)."
    )

    configurar_usuarios_plan_pendiente = models.BooleanField(
        default=False,
        verbose_name="Configuración de Usuarios Pendiente",
        help_text="True si el cliente debe configurar sus usuarios al próximo login (post-compra de plan)"
    )
    slots_usuarios_pendientes = models.JSONField(
        null=True, blank=True, default=dict,
        verbose_name="Slots de Usuarios Pendientes",
        help_text="Usuarios comprados pero no creados: {tecnicos: N, admins: N, gerentes: N}"
    )

    renovacion_automatica = models.BooleanField(default=False, verbose_name="Renovación Automática")
    wompi_payment_source_id = models.CharField(
        max_length=80, null=True, blank=True,
        verbose_name="Wompi Payment Source ID"
    )
    addons_recurrentes = models.JSONField(
        default=dict, blank=True,
        verbose_name="Add-ons Recurrentes",
        help_text="Add-ons que se cobran automáticamente en cada renovación: {tecnicos, admins, gerentes, bloques_equipos, bloques_storage}"
    )

    acceso_manual_activo = models.BooleanField(default=False, verbose_name="Acceso Manual Activo")
    estado_suscripcion = models.CharField(
        max_length=50,
        choices=[('Activo', 'Activo'), ('Expirado', 'Expirado'), ('Cancelado', 'Cancelado')],
        default='Activo',
        verbose_name="Estado de Suscripción"
    )

    # Campos para soft delete (eliminación suave)
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="Eliminada"
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de eliminación"
    )
    deleted_by = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='empresas_eliminadas',
        verbose_name="Eliminada por"
    )
    delete_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Razón de eliminación"
    )

    # Campos para Dashboard de Gerencia - SAM Business
    tarifa_mensual_sam = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Tarifa Mensual SAM",
        help_text="Tarifa mensual que paga este cliente a SAM por servicios metrológicos"
    )
    fecha_inicio_contrato_sam = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha Inicio Contrato SAM"
    )
    nivel_servicio_sam = models.CharField(
        max_length=50,
        choices=[
            ('Básico', 'Básico'),
            ('Estándar', 'Estándar'),
            ('Premium', 'Premium')
        ],
        default='Estándar',
        verbose_name="Nivel de Servicio SAM"
    )

    # Sistema de suscripción mejorado
    MODALIDAD_PAGO_CHOICES = [
        ('MENSUAL', 'Pago Mensual'),
        ('TRIMESTRAL', 'Pago Trimestral (3 meses)'),
        ('SEMESTRAL', 'Pago Semestral (6 meses)'),
        ('ANUAL', 'Pago Anual (12 meses)'),
    ]

    modalidad_pago = models.CharField(
        max_length=20,
        choices=MODALIDAD_PAGO_CHOICES,
        default='MENSUAL',
        verbose_name="Modalidad de Pago",
        help_text="Modalidad de pago acordada con el cliente"
    )

    valor_pago_acordado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Valor de Pago Acordado",
        help_text="Valor total del pago según la modalidad (ej: $6000 si es semestral)"
    )

    fecha_ultimo_pago = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha Último Pago",
        help_text="Fecha en que se recibió el último pago"
    )

    fecha_proximo_pago = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha Próximo Pago",
        help_text="Fecha esperada del próximo pago"
    )

    # Campos para Dashboard de Gerencia - Cliente ISO 17020
    tipo_organismo = models.CharField(
        max_length=50,
        choices=[
            ('OI', 'Organismo de Inspección'),
            ('Laboratorio', 'Laboratorio de Ensayo'),
            ('Certificacion', 'Entidad de Certificación'),
            ('Industrial', 'Empresa Industrial'),
            ('Otro', 'Otro')
        ],
        default='Industrial',
        verbose_name="Tipo de Organismo"
    )
    normas_aplicables = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="Normas Aplicables",
        help_text="Ej: ISO 17020, ISO 17025, ISO 9001"
    )

    # ── Stats pre-computadas del dashboard ──────────────────────────────────────
    stats_total_equipos = models.IntegerField(default=0)
    stats_equipos_activos = models.IntegerField(default=0)
    stats_equipos_inactivos = models.IntegerField(default=0)
    stats_equipos_de_baja = models.IntegerField(default=0)

    # Dependen de la fecha de hoy — se refrescan a diario por cron
    stats_calibraciones_vencidas = models.IntegerField(default=0)
    stats_calibraciones_proximas = models.IntegerField(default=0)
    stats_mantenimientos_vencidos = models.IntegerField(default=0)
    stats_mantenimientos_proximos = models.IntegerField(default=0)
    stats_comprobaciones_vencidas = models.IntegerField(default=0)
    stats_comprobaciones_proximas = models.IntegerField(default=0)

    # Cumplimiento anual para tortas — formato: {"realizadas": N, "no_cumplidas": N, "pendientes": N}
    stats_compliance_calibracion = models.JSONField(default=dict, blank=True)
    stats_compliance_mantenimiento = models.JSONField(default=dict, blank=True)
    stats_compliance_comprobacion = models.JSONField(default=dict, blank=True)

    # Metadatos
    stats_ultima_actualizacion = models.DateTimeField(null=True, blank=True)
    stats_fecha_calculo = models.DateField(null=True, blank=True)
    # ────────────────────────────────────────────────────────────────────────────

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ['nombre']
        permissions = [
            ("can_view_empresas", "Can view empresas"),
            ("can_add_empresas", "Can add empresas"),
            ("can_change_empresas", "Can change empresas"),
            ("can_delete_empresas", "Can delete empresas"),
        ]

    def __str__(self):
        return self.nombre

    def recalcular_stats_dashboard(self):
        """
        Calcula y persiste las métricas del dashboard para esta empresa.

        Reutiliza las funciones get_projected_activities_for_year() y
        get_projected_maintenance_compliance_for_year() de dashboard.py.
        Se llama desde señales (post_save/post_delete de Equipo, Calibracion,
        Mantenimiento, Comprobacion) y desde el comando de gestión diario.
        """
        from django.db.models import Count, Case, When, IntegerField as IntF
        from django.utils import timezone
        from datetime import date, timedelta
        from core.views.dashboard import (
            get_projected_activities_for_year,
            get_projected_maintenance_compliance_for_year,
        )

        today = date.today()
        fecha_limite = today + timedelta(days=30)
        year = today.year

        equipos = self.equipos.prefetch_related('calibraciones', 'mantenimientos', 'comprobaciones')

        # Conteos básicos — 1 query agregada
        counts = equipos.aggregate(
            total=Count('id'),
            activos=Count(Case(When(estado='Activo', then=1), output_field=IntF())),
            inactivos=Count(Case(When(estado='Inactivo', then=1), output_field=IntF())),
            de_baja=Count(Case(When(estado='De Baja', then=1), output_field=IntF())),
        )

        # Actividades vencidas/proximas — solo equipos activos
        equipos_activos = equipos.exclude(estado__in=['De Baja', 'Inactivo'])
        actividades = equipos_activos.aggregate(
            cal_v=Count(Case(When(
                proxima_calibracion__isnull=False, proxima_calibracion__lt=today, then=1
            ), output_field=IntF())),
            cal_p=Count(Case(When(
                proxima_calibracion__isnull=False,
                proxima_calibracion__gte=today,
                proxima_calibracion__lte=fecha_limite,
                then=1,
            ), output_field=IntF())),
            mant_v=Count(Case(When(
                proximo_mantenimiento__isnull=False, proximo_mantenimiento__lt=today, then=1
            ), output_field=IntF())),
            mant_p=Count(Case(When(
                proximo_mantenimiento__isnull=False,
                proximo_mantenimiento__gte=today,
                proximo_mantenimiento__lte=fecha_limite,
                then=1,
            ), output_field=IntF())),
            comp_v=Count(Case(When(
                proxima_comprobacion__isnull=False, proxima_comprobacion__lt=today, then=1
            ), output_field=IntF())),
            comp_p=Count(Case(When(
                proxima_comprobacion__isnull=False,
                proxima_comprobacion__gte=today,
                proxima_comprobacion__lte=fecha_limite,
                then=1,
            ), output_field=IntF())),
        )

        # Cumplimiento anual — incluye De Baja/Inactivos del año actual (con select_related)
        equipos_para_compliance = equipos.select_related('baja_registro')
        cal_proj = get_projected_activities_for_year(equipos_para_compliance, 'calibracion', year, today)
        comp_proj = get_projected_activities_for_year(equipos_para_compliance, 'comprobacion', year, today)
        mant_proj = get_projected_maintenance_compliance_for_year(equipos_para_compliance, year, today)

        def _contar(proyeccion):
            r = n = p = 0
            for item in proyeccion:
                s = item['status']
                if s == 'Realizado':
                    r += 1
                elif s == 'No Cumplido':
                    n += 1
                else:
                    p += 1
            return {'realizadas': r, 'no_cumplidas': n, 'pendientes': p}

        self.stats_total_equipos = counts['total'] or 0
        self.stats_equipos_activos = counts['activos'] or 0
        self.stats_equipos_inactivos = counts['inactivos'] or 0
        self.stats_equipos_de_baja = counts['de_baja'] or 0
        self.stats_calibraciones_vencidas = actividades['cal_v'] or 0
        self.stats_calibraciones_proximas = actividades['cal_p'] or 0
        self.stats_mantenimientos_vencidos = actividades['mant_v'] or 0
        self.stats_mantenimientos_proximos = actividades['mant_p'] or 0
        self.stats_comprobaciones_vencidas = actividades['comp_v'] or 0
        self.stats_comprobaciones_proximas = actividades['comp_p'] or 0
        self.stats_compliance_calibracion = _contar(cal_proj)
        self.stats_compliance_mantenimiento = _contar(mant_proj)
        self.stats_compliance_comprobacion = _contar(comp_proj)
        self.stats_ultima_actualizacion = timezone.now()
        self.stats_fecha_calculo = today

        self.save(update_fields=[
            'stats_total_equipos', 'stats_equipos_activos', 'stats_equipos_inactivos',
            'stats_equipos_de_baja', 'stats_calibraciones_vencidas', 'stats_calibraciones_proximas',
            'stats_mantenimientos_vencidos', 'stats_mantenimientos_proximos',
            'stats_comprobaciones_vencidas', 'stats_comprobaciones_proximas',
            'stats_compliance_calibracion', 'stats_compliance_mantenimiento',
            'stats_compliance_comprobacion', 'stats_ultima_actualizacion', 'stats_fecha_calculo',
        ])

    def soft_delete(self, user=None, reason=None):
        """
        Elimina la empresa de forma suave (soft delete).
        La empresa no se elimina físicamente, solo se marca como eliminada.
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.delete_reason = reason or "Eliminación manual"
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'delete_reason'])

    def calcular_tarifa_mensual_equivalente(self):
        """
        Calcula la tarifa mensual equivalente basándose en la modalidad de pago.
        Retorna siempre Decimal para mantener precisión en cálculos financieros.
        """
        if not self.valor_pago_acordado:
            return self.tarifa_mensual_sam or decimal.Decimal('0')

        modalidad_meses = {
            'MENSUAL': 1,
            'TRIMESTRAL': 3,
            'SEMESTRAL': 6,
            'ANUAL': 12,
        }

        meses = modalidad_meses.get(self.modalidad_pago, 1)
        return self.valor_pago_acordado / decimal.Decimal(str(meses))

    def get_ingresos_anuales_reales(self):
        """
        Calcula los ingresos anuales reales que esta empresa genera para SAM.
        Retorna Decimal para mantener precisión en cálculos financieros.
        """
        tarifa_mensual = self.calcular_tarifa_mensual_equivalente()
        return tarifa_mensual * decimal.Decimal('12')

    def dias_hasta_proximo_pago(self):
        """
        Calcula los días hasta el próximo pago.
        """
        if not self.fecha_proximo_pago:
            return None

        from datetime import date
        hoy = date.today()
        if self.fecha_proximo_pago > hoy:
            return (self.fecha_proximo_pago - hoy).days
        else:
            return -(hoy - self.fecha_proximo_pago).days  # Días de retraso (negativo)

    def esta_al_dia_con_pagos(self):
        """
        Verifica si la empresa está al día con sus pagos.
        """
        dias = self.dias_hasta_proximo_pago()
        if dias is None:
            return True  # Sin fecha definida, asumimos que está al día
        return dias >= -7  # Permitir 7 días de gracia

    def restore(self, user=None):
        """
        Restaura una empresa previamente eliminada.
        """
        if not self.is_deleted:
            return False, "La empresa no está eliminada"

        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.delete_reason = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'delete_reason'])

        # Log de la restauración
        logger.info(f'Empresa {self.nombre} (ID:{self.id}) restaurada por {user.username if user else "sistema"}')

        return True, "Empresa restaurada exitosamente"

    @classmethod
    def get_deleted_companies(cls):
        """
        Obtiene todas las empresas eliminadas (soft deleted).
        """
        return cls.objects.filter(is_deleted=True).order_by('-deleted_at')

    @classmethod
    def get_active_companies(cls):
        """
        Obtiene todas las empresas activas (no eliminadas).
        """
        return cls.objects.filter(is_deleted=False).order_by('nombre')

    def can_be_restored(self):
        """
        Verifica si la empresa puede ser restaurada.
        """
        return self.is_deleted

    def get_delete_info(self):
        """
        Obtiene información sobre la eliminación.
        """
        if not self.is_deleted:
            return None

        days_since_deletion = (timezone.now() - self.deleted_at).days if self.deleted_at else 0
        days_until_permanent_deletion = max(0, 180 - days_since_deletion)  # 6 meses = 180 días

        return {
            'deleted_at': self.deleted_at,
            'deleted_by': self.deleted_by.username if self.deleted_by else 'Sistema',
            'delete_reason': self.delete_reason or 'Sin razón especificada',
            'days_since_deletion': days_since_deletion,
            'days_until_permanent_deletion': days_until_permanent_deletion,
            'will_be_permanently_deleted_soon': days_until_permanent_deletion <= 30  # Alerta si quedan 30 días o menos
        }

    def should_be_permanently_deleted(self):
        """
        Determina si la empresa debe ser eliminada permanentemente.
        Las empresas eliminadas se conservan por 6 meses (180 días).
        """
        if not self.is_deleted or not self.deleted_at:
            return False

        months_since_deletion = (timezone.now() - self.deleted_at).days
        return months_since_deletion >= 180  # 6 meses = ~180 días

    @classmethod
    def get_companies_for_permanent_deletion(cls):
        """
        Obtiene empresas que deben ser eliminadas permanentemente.
        """
        six_months_ago = timezone.now() - timedelta(days=180)
        return cls.objects.filter(
            is_deleted=True,
            deleted_at__lte=six_months_ago
        )

    @classmethod
    def cleanup_old_deleted_companies(cls, dry_run=False):
        """
        Limpia empresas eliminadas que han pasado el período de retención (6 meses).

        Args:
            dry_run (bool): Si es True, solo retorna las empresas que serían eliminadas sin eliminarlas.

        Returns:
            dict: Información sobre las empresas eliminadas o que serían eliminadas.
        """
        companies_to_delete = cls.get_companies_for_permanent_deletion()

        result = {
            'count': companies_to_delete.count(),
            'companies': [],
            'deleted': []
        }

        for company in companies_to_delete:
            company_info = {
                'id': company.id,
                'name': company.nombre,
                'deleted_at': company.deleted_at,
                'days_since_deletion': (timezone.now() - company.deleted_at).days
            }
            result['companies'].append(company_info)

            if not dry_run:
                try:
                    # Eliminar físicamente la empresa y todos sus datos relacionados
                    company_name = company.nombre
                    company.delete()  # Django eliminará automáticamente datos relacionados según on_delete
                    result['deleted'].append(company_info)
                    logger.info(f'Empresa {company_name} eliminada permanentemente después de 6 meses')
                except Exception as e:
                    logger.error(f'Error eliminando permanentemente empresa {company.nombre}: {e}')

        return result

    def get_limite_equipos(self):
        """Retorna el límite de equipos basado en el sistema de planes existente."""
        if self.acceso_manual_activo:
            # Acceso manual: sin límites
            return float('inf')

        # Usar la lógica existente para determinar el estado del plan
        estado_plan = self.get_estado_suscripcion_display()

        if estado_plan == "Período de Prueba Activo":
            # Durante el trial, usar límite expandido
            return self.TRIAL_EQUIPOS
        elif estado_plan in ["Plan Expirado", "Período de Prueba Expirado", "Expirado"]:
            # Plan expirado: sin acceso (0 equipos permitidos) - datos se conservan
            return 0
        else:
            # Plan activo: usar el límite configurado en la empresa
            return self.limite_equipos_empresa

    def get_limite_almacenamiento(self):
        """Retorna el límite de almacenamiento basado en el sistema de planes existente."""
        if self.acceso_manual_activo:
            # Acceso manual: sin límites
            return float('inf')

        # Usar la lógica existente para determinar el estado del plan
        estado_plan = self.get_estado_suscripcion_display()

        if estado_plan == "Período de Prueba Activo":
            # Durante el trial, usar límite expandido
            return self.TRIAL_ALMACENAMIENTO_MB
        elif estado_plan in ["Plan Expirado", "Período de Prueba Expirado", "Expirado"]:
            # Plan expirado: sin almacenamiento adicional (0 MB) - archivos existentes se conservan
            return 0
        else:
            # Plan activo: usar el límite configurado en la empresa
            return self.limite_almacenamiento_mb

    def get_plan_actual(self):
        """Determina el tipo de plan actual basado en la lógica existente."""
        estado_plan = self.get_estado_suscripcion_display()

        if estado_plan == "Período de Prueba Activo":
            return 'trial'
        elif estado_plan in ["Plan Expirado", "Período de Prueba Expirado", "Expirado"]:
            return 'free'
        elif self.fecha_inicio_plan and self.duracion_suscripcion_meses:
            return 'paid'
        else:
            return 'free'

    def activar_plan_pagado(self, limite_equipos, limite_almacenamiento_mb, duracion_meses=12):
        """
        Activa un plan pagado inmediatamente, usando el sistema de campos existente.

        Args:
            limite_equipos (int): Límite de equipos del nuevo plan
            limite_almacenamiento_mb (int): Límite de almacenamiento en MB
            duracion_meses (int): Duración del plan en meses (default: 12)
        """
        # Detener trial si está activo
        if self.es_periodo_prueba:
            self.es_periodo_prueba = False

        # Configurar plan pagado usando campos existentes
        self.fecha_inicio_plan = timezone.now().date()
        self.duracion_suscripcion_meses = duracion_meses
        self.limite_equipos_empresa = limite_equipos
        self.limite_almacenamiento_mb = limite_almacenamiento_mb

        # Actualizar estados relacionados
        self.estado_suscripcion = 'Activo'

        # Marcar que los usuarios deben configurarse en el próximo login
        self.configurar_usuarios_plan_pendiente = True

        self.save()

        # Restaurar add-ons recurrentes encima del plan base
        if self.addons_recurrentes:
            self.activar_addons(self.addons_recurrentes)

        # Invalidar caché del dashboard para que refleje el nuevo plan inmediatamente
        try:
            from core.signals import invalidate_dashboard_cache
            invalidate_dashboard_cache(self.id)
        except Exception:
            pass

        # Log de la transición
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Plan pagado activado para empresa {self.nombre}: {limite_equipos} equipos, {limite_almacenamiento_mb}MB, {duracion_meses} meses")

    def activar_addons(self, datos_addon):
        """
        Activa add-ons comprados incrementando los límites actuales.
        No toca fechas ni estado de suscripción — solo aumenta límites.

        datos_addon = {
            'tecnicos': N,       # usuarios técnicos adicionales
            'admins': N,         # usuarios admin adicionales
            'gerentes': N,       # usuarios gerente adicionales
            'bloques_equipos': N,  # cada bloque = +50 equipos
            'bloques_storage': N,  # cada bloque = +5 GB
        }
        """
        import logging
        logger = logging.getLogger(__name__)

        usuarios_extra = (
            int(datos_addon.get('tecnicos', 0)) +
            int(datos_addon.get('admins', 0)) +
            int(datos_addon.get('gerentes', 0))
        )
        equipos_extra = int(datos_addon.get('bloques_equipos', 0)) * 50
        storage_extra_mb = int(datos_addon.get('bloques_storage', 0)) * 5 * 1024

        if usuarios_extra > 0:
            self.limite_usuarios_empresa += usuarios_extra
        if equipos_extra > 0:
            self.limite_equipos_empresa += equipos_extra
        if storage_extra_mb > 0:
            self.limite_almacenamiento_mb += storage_extra_mb

        # Acumular slots de usuarios pendientes por rol
        tecnicos = int(datos_addon.get('tecnicos', 0))
        admins = int(datos_addon.get('admins', 0))
        gerentes = int(datos_addon.get('gerentes', 0))
        if tecnicos or admins or gerentes:
            slots = self.slots_usuarios_pendientes or {}
            if tecnicos:
                slots['tecnicos'] = slots.get('tecnicos', 0) + tecnicos
            if admins:
                slots['admins'] = slots.get('admins', 0) + admins
            if gerentes:
                slots['gerentes'] = slots.get('gerentes', 0) + gerentes
            self.slots_usuarios_pendientes = slots

        self.save(update_fields=[
            'limite_usuarios_empresa',
            'limite_equipos_empresa',
            'limite_almacenamiento_mb',
            'slots_usuarios_pendientes',
        ])

        # Invalidar caché del dashboard para que refleje los nuevos límites
        try:
            from core.signals import invalidate_dashboard_cache
            invalidate_dashboard_cache(self.id)
        except Exception:
            pass

        logger.info(
            f"Add-ons activados para empresa {self.nombre}: "
            f"+{usuarios_extra} usuarios, +{equipos_extra} equipos, "
            f"+{storage_extra_mb}MB almacenamiento"
        )

    @property
    def tiene_setup_usuarios_pendiente(self):
        """True si hay alguna configuración de usuarios pendiente post-compra."""
        if self.configurar_usuarios_plan_pendiente:
            return True
        slots = self.slots_usuarios_pendientes or {}
        return any(v > 0 for v in slots.values())

    def activar_periodo_prueba(self, duracion_dias=7):
        """
        Activa un período de prueba usando el sistema existente.
        """
        # Configurar período de prueba usando campos existentes
        self.es_periodo_prueba = True
        self.duracion_prueba_dias = duracion_dias
        self.fecha_inicio_plan = timezone.now().date()

        # Aplicar límites expandidos del trial
        self.limite_equipos_empresa = self.TRIAL_EQUIPOS
        self.limite_almacenamiento_mb = self.TRIAL_ALMACENAMIENTO_MB

        # Actualizar estados
        self.estado_suscripcion = 'Activo'

        self.save()

        # Log de la transición
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Período de prueba activado para empresa {self.nombre}: {duracion_dias} días")

    def marcar_como_expirado(self):
        """
        Marca la empresa como expirada, sin transición a plan gratuito.
        Los datos se conservan pero el acceso queda restringido hasta renovar.
        """
        # Limpiar configuración de planes activos
        self.es_periodo_prueba = False
        self.fecha_inicio_plan = None
        self.duracion_suscripcion_meses = None

        # Marcar como expirado (sin límites funcionales hasta renovar)
        self.estado_suscripcion = 'Expirado'

        self.save()

        # Log de la expiración
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Empresa {self.nombre} marcada como expirada - acceso restringido hasta renovación")

    def verificar_y_procesar_expiraciones(self):
        """
        Verifica y procesa automáticamente las expiraciones usando la lógica existente.
        Este método debe ser llamado periódicamente por un comando de mantenimiento.
        """
        estado_plan = self.get_estado_suscripcion_display()
        cambio_realizado = False

        # Si el plan está expirado, marcar como expirado (sin plan gratuito)
        if estado_plan in ["Plan Expirado", "Período de Prueba Expirado"]:
            # Solo marcar si no está ya marcado como expirado
            if self.estado_suscripcion != 'Expirado':
                self.marcar_como_expirado()
                cambio_realizado = True

        return cambio_realizado

    def get_dias_restantes_plan(self):
        """Retorna los días restantes del plan actual usando fecha de fin existente."""
        fecha_fin = self.get_fecha_fin_plan()

        if fecha_fin:
            remaining = fecha_fin - timezone.localdate()
            return max(0, remaining.days)
        else:
            return float('inf')  # Plan gratuito o sin límite de tiempo

    def get_estado_suscripcion_display(self):
        """Devuelve el estado de la suscripción, considerando el periodo de prueba y la duración del plan."""
        current_date = timezone.localdate()

        if self.es_periodo_prueba and self.fecha_inicio_plan:
            end_date_trial = self.fecha_inicio_plan + timedelta(days=self.duracion_prueba_dias)
            if current_date > end_date_trial:
                return "Período de Prueba Expirado"
            else:
                return "Período de Prueba Activo"
        elif self.fecha_inicio_plan and self.duracion_suscripcion_meses:
            end_date_plan = self.fecha_inicio_plan + relativedelta(months=self.duracion_suscripcion_meses)
            if current_date > end_date_plan:
                return "Plan Expirado"

        # Si no es período de prueba ni plan expirado, devuelve el estado_suscripcion normal
        return self.estado_suscripcion

    def get_fecha_fin_plan(self):
        """Calcula y devuelve la fecha de fin del plan o periodo de prueba."""
        if self.es_periodo_prueba and self.fecha_inicio_plan:
            return self.fecha_inicio_plan + timedelta(days=self.duracion_prueba_dias)
        elif self.fecha_inicio_plan and self.duracion_suscripcion_meses:
            return self.fecha_inicio_plan + relativedelta(months=self.duracion_suscripcion_meses)
        return None # No hay fecha de fin si no hay plan ni prueba

    @property
    def fecha_fin_plan_display(self):
        """Devuelve la fecha de fin del plan para mostrar en templates."""
        return self.get_fecha_fin_plan()

    def get_total_storage_used_mb(self):
        """
        Calcula el uso total de almacenamiento en MB para la empresa.

        Optimizado para evitar timeouts en R2/S3:
        - Cache de 2 horas: la mayoría de las visitas no hacen ninguna llamada a R2.
        - Sin llamadas exists(): cada archivo hace UNA sola llamada a R2 (head_object),
          no dos (exists + size). Esto reduce a la mitad las llamadas.
        - Presupuesto de tiempo de 15s: si R2 es lento, devuelve el valor parcial
          para no matar el worker de Gunicorn.
        """
        import time
        import logging
        from django.core.files.storage import default_storage
        from django.core.cache import cache

        log = logging.getLogger(__name__)

        # Clave de cache estable (sin timestamp) — la invalidación manual
        # se hace desde invalidate_storage_cache() al subir/borrar archivos.
        cache_key = f"storage_usage_empresa_{self.id}_v5"

        try:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        except Exception:
            pass

        def _size(archivo):
            """
            Devuelve el tamaño de un FieldFile en bytes.
            Una sola llamada a R2 (head_object), sin exists() previo.
            Devuelve 0 si el archivo no existe o hay error de red.
            """
            if not archivo or not getattr(archivo, 'name', None):
                return 0
            try:
                return default_storage.size(archivo.name)
            except Exception:
                return 0

        total_size_bytes = 0
        deadline = time.monotonic() + 15  # máximo 15 s de llamadas a R2

        # Logo de la empresa
        total_size_bytes += _size(self.logo_empresa)

        # Equipos y sus actividades
        equipos = self.equipos.prefetch_related(
            'calibraciones', 'mantenimientos', 'comprobaciones'
        ).all()

        CAMPOS_EQUIPO = [
            'archivo_compra_pdf', 'ficha_tecnica_pdf',
            'manual_pdf', 'otros_documentos_pdf', 'imagen_equipo',
        ]
        CAMPOS_CAL = [
            'documento_calibracion',
            'confirmacion_metrologica_pdf',
            'intervalos_calibracion_pdf',
        ]
        CAMPOS_MANT = ['documento_mantenimiento', 'archivo_mantenimiento']

        for equipo in equipos:
            if time.monotonic() > deadline:
                log.warning(
                    f"get_total_storage_used_mb: presupuesto de tiempo agotado "
                    f"para empresa {self.id}. Devolviendo resultado parcial."
                )
                break

            for campo in CAMPOS_EQUIPO:
                total_size_bytes += _size(getattr(equipo, campo, None))

            for cal in equipo.calibraciones.all():
                for campo in CAMPOS_CAL:
                    total_size_bytes += _size(getattr(cal, campo, None))

            for mant in equipo.mantenimientos.all():
                for campo in CAMPOS_MANT:
                    total_size_bytes += _size(getattr(mant, campo, None))

            for comp in equipo.comprobaciones.all():
                total_size_bytes += _size(
                    getattr(comp, 'documento_comprobacion', None)
                )

        total_size_mb = round(total_size_bytes / (1024 * 1024), 2)

        # Guardar en cache 2 horas
        try:
            cache.set(cache_key, total_size_mb, 7200)
        except Exception:
            pass

        return total_size_mb

    def invalidate_storage_cache(self):
        """Invalida el cache de almacenamiento cuando se modifican archivos."""
        from django.core.cache import cache
        cache_key = f"storage_usage_empresa_{self.id}_v5"
        try:
            cache.delete(cache_key)
        except Exception as e:
            # Si hay error con el cache, simplemente continuar
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"No se pudo invalidar cache storage: {e}")

    def get_storage_usage_percentage(self):
        """Calcula el porcentaje de uso de almacenamiento."""
        if self.limite_almacenamiento_mb <= 0:
            return 0

        used_mb = self.get_total_storage_used_mb()
        percentage = (used_mb / self.limite_almacenamiento_mb) * 100
        return min(round(percentage, 1), 100)  # Máximo 100%

    def get_storage_status_class(self):
        """Retorna la clase CSS basada en el porcentaje de uso de almacenamiento."""
        percentage = self.get_storage_usage_percentage()

        if percentage >= 90:
            return 'text-red-700 bg-red-100'
        elif percentage >= 75:
            return 'text-yellow-700 bg-yellow-100'
        elif percentage >= 50:
            return 'text-orange-700 bg-orange-100'
        else:
            return 'text-green-700 bg-green-100'

    @property
    def fecha_fin_plan_status(self):
        """
        Devuelve el CSS class basado en el estado de la fecha de fin del plan.
        - Verde: falta más de 1 mes
        - Amarillo: faltan 15 días o menos
        - Rojo: plan vencido
        """
        fecha_fin = self.get_fecha_fin_plan()
        if not fecha_fin:
            return 'text-gray-500'  # Sin plan definido

        current_date = timezone.localdate()
        dias_restantes = (fecha_fin - current_date).days

        if dias_restantes < 0:
            # Plan vencido
            return 'text-red-600 font-bold bg-red-100 px-2 py-1 rounded'
        elif dias_restantes <= 15:
            # Faltan 15 días o menos
            return 'text-yellow-600 font-bold bg-yellow-100 px-2 py-1 rounded'
        elif dias_restantes <= 30:
            # Falta 1 mes o menos
            return 'text-green-600 font-bold bg-green-100 px-2 py-1 rounded'
        else:
            # Falta más de 1 mes
            return 'text-green-700'


    def save(self, *args, **kwargs):
        """Override save para configurar plan gratuito por defecto en empresas nuevas."""
        # Si es una empresa nueva, configurar plan gratuito por defecto
        if not self.pk:
            # Solo configurar si no se han establecido manualmente
            if not hasattr(self, '_plan_set_manually'):
                # Plan gratuito por defecto - no period de prueba automático
                self.es_periodo_prueba = False
                self.fecha_inicio_plan = None
                self.duracion_suscripcion_meses = None

                # Límites del plan gratuito
                if self.limite_equipos_empresa is None:
                    self.limite_equipos_empresa = self.PLAN_GRATUITO_EQUIPOS

                if self.limite_almacenamiento_mb is None:
                    self.limite_almacenamiento_mb = self.PLAN_GRATUITO_ALMACENAMIENTO_MB

        super().save(*args, **kwargs)


class PlanSuscripcion(models.Model):
    """
    Modelo para definir los diferentes planes de suscripción disponibles.
    Se mantiene si en el futuro se desea una gestión de planes más compleja,
    pero ya no tiene una FK directa desde Empresa para la lógica de uso actual.
    """
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre del Plan")
    limite_equipos = models.IntegerField(default=0, verbose_name="Límite de Equipos")
    precio_mensual = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Precio Mensual")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción del Plan")
    duracion_meses = models.IntegerField(default=0, help_text="Duración del plan en meses (0 para indefinido)", verbose_name="Duración (meses)")

    class Meta:
        verbose_name = "Plan de Suscripción"
        verbose_name_plural = "Planes de Suscripción"
        ordering = ['precio_mensual']
        permissions = [
            ("can_view_plansuscripcion", "Can view plan suscripcion"),
            ("can_add_plansuscripcion", "Can add plan suscripcion"),
            ("can_change_plansuscripcion", "Can change plan suscripcion"),
            ("can_delete_plansuscripcion", "Can delete plan suscripcion"),
        ]

    def __str__(self):
        return self.nombre
