# core/models.py
# Ajustado para la lógica de la primera programación de mantenimiento y comprobación
# y para la implementación de planes de suscripción simplificados.

from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from datetime import date, timedelta, datetime
from django.utils import timezone # Importar timezone para obtener la fecha actual con zona horaria
import decimal # Importar el módulo decimal (mantener por si otros campos lo usan o se necesita para importación/exportación de otros numéricos)
import os
from django.utils.translation import gettext_lazy as _
from dateutil.relativedelta import relativedelta
from django.conf import settings # ¡ASEGURARSE DE QUE ESTA LÍNEA ESTÉ PRESENTE!
import calendar # Importar calendar para nombres de meses
import uuid # Importar uuid para generar nombres únicos temporales
import json # Para almacenar configuraciones JSON
import logging # Para logging en métodos de eliminación/restauración

# Configurar logger para este módulo
logger = logging.getLogger('core')


# ==============================================================================
# FUNCIONES AUXILIARES
# ==============================================================================

def meses_decimales_a_relativedelta(meses_decimal):
    """
    Convierte meses decimales a un objeto relativedelta con meses y días.

    Permite frecuencias más precisas como 1.5 meses (1 mes + 15 días)
    o 2.25 meses (2 meses + 7 días).

    Ejemplos:
        - 1.5 meses = 1 mes + 15 días
        - 2.25 meses = 2 meses + 7 días
        - 0.5 meses = 15 días
        - 6.0 meses = 6 meses exactos

    Args:
        meses_decimal (Decimal): Número de meses (puede tener decimales)

    Returns:
        relativedelta: Objeto relativedelta con meses y días calculados
    """
    if meses_decimal is None:
        return relativedelta(months=0)

    # Convertir Decimal a float
    meses_float = float(meses_decimal)

    # Separar parte entera (meses) y decimal (fracción de mes)
    meses_enteros = int(meses_float)
    fraccion_mes = meses_float - meses_enteros

    # Convertir fracción de mes a días (promedio de 30.44 días por mes)
    dias_adicionales = round(fraccion_mes * 30.44)

    return relativedelta(months=meses_enteros, days=dias_adicionales)


# ==============================================================================
# MODELO DE USUARIO PERSONALIZADO (AÑADIDO Y AJUSTADO)
# ==============================================================================

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
    logo_empresa = models.ImageField(upload_to='empresas_logos/', blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    # CAMBIO: Eliminado el campo 'limite_equipos' para usar solo 'limite_equipos_empresa'
    # limite_equipos = models.IntegerField(
    #     default=0,
    #     help_text="Número máximo de equipos que esta empresa puede registrar. 0 para ilimitado.",
    #     blank=True,
    #     null=True
    # )

    # Nuevos campos para la información de formato por empresa
    formato_version_empresa = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Versión del Formato (Empresa)"
    )
    formato_fecha_version_empresa = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de Versión del Formato (Empresa)"
    )
    formato_codificacion_empresa = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Codificación del Formato (Empresa)"
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
        """
        if not self.valor_pago_acordado:
            return self.tarifa_mensual_sam or 0

        modalidad_meses = {
            'MENSUAL': 1,
            'TRIMESTRAL': 3,
            'SEMESTRAL': 6,
            'ANUAL': 12,
        }

        meses = modalidad_meses.get(self.modalidad_pago, 1)
        return float(self.valor_pago_acordado) / meses

    def get_ingresos_anuales_reales(self):
        """
        Calcula los ingresos anuales reales que esta empresa genera para SAM.
        """
        tarifa_mensual = self.calcular_tarifa_mensual_equivalente()
        return tarifa_mensual * 12

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

        # Log de la eliminación
        logger.info(f'Empresa {self.nombre} (ID:{self.id}) eliminada por {user.username if user else "sistema"}')

        return True

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

    def save(self, *args, **kwargs):
        """
        Método save personalizado para auto-configurar Trial en empresas nuevas.
        """
        # Si es una empresa nueva (no tiene PK aún)
        if not self.pk:
            # Auto-configurar Trial de 30 días
            from datetime import date
            if not self.fecha_inicio_plan:
                self.fecha_inicio_plan = date.today()

            # Asegurarse de que esté marcada como período de prueba
            if not hasattr(self, '_skip_auto_trial'):
                self.es_periodo_prueba = True
                self.duracion_prueba_dias = 30

        super().save(*args, **kwargs)

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

        self.save()

        # Log de la transición
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Plan pagado activado para empresa {self.nombre}: {limite_equipos} equipos, {limite_almacenamiento_mb}MB, {duracion_meses} meses")

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
        """Calcula el uso total de almacenamiento en MB para todos los archivos de la empresa."""
        from django.core.files.storage import default_storage
        from django.core.cache import cache
        from django.core.cache.backends.base import InvalidCacheBackendError
        import hashlib
        import time

        # Crear clave de cache única para esta empresa con timestamp de última modificación
        from django.utils import timezone
        last_modified = self.equipos.aggregate(
            last_mod=models.Max('fecha_registro')
        ).get('last_mod', timezone.now())

        # Cache más inteligente con timestamp para invalidación automática
        cache_version = int(last_modified.timestamp()) if last_modified else 0
        cache_key = f"storage_usage_empresa_{self.id}_v3_{cache_version}"

        # Cache válido por 30 minutos para mejor performance
        try:
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
        except Exception as e:
            # Si hay error con el cache (ej. tabla no existe), continuar sin cache
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Cache no disponible para storage calculation: {e}")
            cached_result = None

        total_size_bytes = 0

        # Calcular storage del logo de la empresa
        if self.logo_empresa and hasattr(self.logo_empresa, 'name') and self.logo_empresa.name:
            try:
                if default_storage.exists(self.logo_empresa.name):
                    total_size_bytes += default_storage.size(self.logo_empresa.name)
            except Exception:
                pass

        # Calcular storage de equipos y sus archivos (Optimizado con prefetch)
        equipos_con_relaciones = self.equipos.prefetch_related(
            'calibraciones', 'mantenimientos', 'comprobaciones'
        ).all()

        for equipo in equipos_con_relaciones:
            # Archivos principales del equipo
            campos_archivo_equipo = ['archivo_compra_pdf', 'ficha_tecnica_pdf', 'manual_pdf', 'otros_documentos_pdf', 'imagen_equipo']
            for campo_archivo in campos_archivo_equipo:
                archivo = getattr(equipo, campo_archivo, None)
                if archivo and hasattr(archivo, 'name'):
                    try:
                        if default_storage.exists(archivo.name):
                            total_size_bytes += default_storage.size(archivo.name)
                    except Exception:
                        pass

            # Archivos de calibraciones
            for calibracion in equipo.calibraciones.all():
                # Verificar múltiples campos de archivos en calibraciones
                for campo_archivo in ['documento_calibracion', 'confirmacion_metrologica_pdf', 'intervalos_calibracion_pdf']:
                    archivo = getattr(calibracion, campo_archivo, None)
                    if archivo and hasattr(archivo, 'name'):
                        try:
                            if default_storage.exists(archivo.name):
                                total_size_bytes += default_storage.size(archivo.name)
                        except Exception:
                            pass

            # Archivos de mantenimientos
            for mantenimiento in equipo.mantenimientos.all():
                # Verificar múltiples campos de archivos en mantenimientos
                for campo_archivo in ['documento_mantenimiento', 'archivo_mantenimiento']:
                    archivo = getattr(mantenimiento, campo_archivo, None)
                    if archivo and hasattr(archivo, 'name'):
                        try:
                            if default_storage.exists(archivo.name):
                                total_size_bytes += default_storage.size(archivo.name)
                        except Exception:
                            pass

            # Archivos de comprobaciones
            for comprobacion in equipo.comprobaciones.all():
                if comprobacion.documento_comprobacion and hasattr(comprobacion.documento_comprobacion, 'name'):
                    try:
                        if default_storage.exists(comprobacion.documento_comprobacion.name):
                            total_size_bytes += default_storage.size(comprobacion.documento_comprobacion.name)
                    except Exception:
                        pass

        # Convertir bytes a MB
        total_size_mb = round(total_size_bytes / (1024 * 1024), 2)

        # Guardar en cache por 30 minutos (1800 segundos) para mejor performance
        try:
            cache.set(cache_key, total_size_mb, 1800)
        except Exception as e:
            # Si hay error con el cache, continuar sin guardarlo
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"No se pudo guardar en cache storage calculation: {e}")

        return total_size_mb

    def invalidate_storage_cache(self):
        """Invalida el cache de almacenamiento cuando se modifican archivos."""
        from django.core.cache import cache
        cache_key = f"storage_usage_empresa_{self.id}_v2"
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


class CustomUser(AbstractUser):
    """
    Modelo de usuario personalizado para añadir campos adicionales como la empresa a la que pertenece.
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True, related_name='usuarios_empresa') # Cambiado related_name
    can_access_dashboard_decisiones = models.BooleanField(default=True, help_text="Permite al usuario acceder al dashboard de decisiones")
    is_management_user = models.BooleanField(
        default=False,
        verbose_name="Usuario de Gerencia",
        help_text="Permite al usuario acceder al Dashboard de Gerencia Ejecutiva con métricas financieras y de gestión"
    )

    # Sistema de roles mejorado
    ROLE_CHOICES = [
        ('TECNICO', 'Técnico - Solo operaciones básicas'),
        ('ADMINISTRADOR', 'Administrador - Gestión completa de empresa'),
        ('GERENCIA', 'Gerencia - Acceso a métricas financieras y dashboard ejecutivo'),
    ]

    rol_usuario = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='TECNICO',
        verbose_name="Rol de Usuario",
        help_text="Define el nivel de acceso y permisos del usuario en el sistema"
    )
    
    # Asegúrate de que estos related_name sean ÚNICOS a nivel de la aplicación
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_groups', # related_name único para evitar conflictos
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_user_permissions', # related_name único para evitar conflictos
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        permissions = [
            ("can_view_customuser", "Can view custom user"),
            ("can_add_customuser", "Can add custom user"),
            ("can_change_customuser", "Can change custom user"),
            ("can_delete_customuser", "Can delete custom user"),
        ]

    def __str__(self):
        return self.username

    # Métodos de permisos basados en roles
    def is_tecnico(self):
        """Verifica si el usuario tiene rol de técnico."""
        return self.rol_usuario == 'TECNICO'

    def is_administrador(self):
        """Verifica si el usuario tiene rol de administrador."""
        return self.rol_usuario == 'ADMINISTRADOR'

    def is_gerente(self):
        """Verifica si el usuario tiene rol de gerente."""
        return self.rol_usuario == 'GERENCIA'

    def puede_descargar_informes(self):
        """
        Verifica si el usuario puede descargar informes.
        TÉCNICO: NO
        ADMINISTRADOR: SÍ
        GERENTE: SÍ
        SUPERUSER: SÍ
        """
        if self.is_superuser:
            return True
        return self.rol_usuario in ['ADMINISTRADOR', 'GERENCIA']

    def puede_ver_panel_decisiones(self):
        """
        Verifica si el usuario puede acceder al panel de decisiones.
        TÉCNICO: NO
        ADMINISTRADOR: NO
        GERENTE: SÍ
        SUPERUSER: SÍ
        """
        if self.is_superuser:
            return True
        return self.rol_usuario == 'GERENCIA'

    def puede_gestionar_metrologia(self):
        """
        Verifica si el usuario puede interactuar con metrología (equipos, calibraciones, etc.).
        TODOS los roles pueden gestionar metrología.
        """
        return True

    @property
    def has_export_permission(self):
        """
        Verifica si el usuario tiene permiso para exportar informes.
        Usa el nuevo sistema de roles.
        """
        return self.puede_descargar_informes()


# ==============================================================================
# FUNCIONES PARA RUTAS DE SUBIDA DE ARCHIVOS (AJUSTADAS)
# ==============================================================================

def get_upload_path(instance, filename):
    """Define la ruta de subida para los archivos de equipo y sus actividades."""
    import re
    import os
    
    # Sanitizar el nombre del archivo
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    
    base_code = None
    if isinstance(instance, Equipo):
        base_code = instance.codigo_interno
    elif hasattr(instance, 'equipo') and hasattr(instance.equipo, 'codigo_interno'):
        base_code = instance.equipo.codigo_interno
    elif isinstance(instance, Procedimiento):
        base_code = instance.codigo
    elif isinstance(instance, Documento):
        if instance.pk:
            base_code = f"doc_{instance.pk}"
        else:
            base_code = f"temp_doc_{uuid.uuid4()}"

    if not base_code:
        raise AttributeError(f"No se pudo determinar el código interno del equipo/procedimiento/documento para la instancia de tipo {type(instance).__name__}. Asegúrese de que tiene un código definido.")

    # Sanitizar el código base
    safe_base_code = re.sub(r'[^\w\-_]', '_', str(base_code))

    # Construir la ruta base dentro de MEDIA_ROOT
    base_path = f"documentos/{safe_base_code}/"

    # Determinar subcarpeta específica para el tipo de documento
    subfolder = ""
    if isinstance(instance, Calibracion):
        if 'confirmacion' in filename.lower():
            subfolder = "calibraciones/confirmaciones/"
        elif 'intervalos' in filename.lower():
            subfolder = "calibraciones/intervalos/"
        else: # Por defecto, si no es confirmación o intervalos, es certificado
            subfolder = "calibraciones/certificados/"
    elif isinstance(instance, Mantenimiento):
        subfolder = "mantenimientos/"
    elif isinstance(instance, Comprobacion):
        subfolder = "comprobaciones/"
    elif isinstance(instance, BajaEquipo):
        subfolder = "bajas_equipo/"
    elif isinstance(instance, Equipo):
        # Para los documentos directos del equipo, usar subcarpetas más específicas
        if 'compra' in filename.lower():
            subfolder = "equipos/compra/"
        elif 'ficha_tecnica' in filename.lower() or 'ficha-tecnica' in filename.lower():
            subfolder = "equipos/ficha_tecnica/"
        elif 'manual' in filename.lower():
            subfolder = "equipos/manuales/"
        elif filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            subfolder = "equipos/imagenes/"
        else:
            subfolder = "equipos/otros_documentos/"
    elif isinstance(instance, Procedimiento):
        subfolder = "procedimientos/" # Subcarpeta para documentos de procedimiento
    elif isinstance(instance, Documento): # Nueva subcarpeta para documentos genéricos
        subfolder = "generales/"
    
    # Asegurarse de que el nombre del archivo es seguro
    safe_filename = filename # Por simplicidad, se mantiene el nombre original, pero es un punto de mejora

    return os.path.join(base_path, subfolder, safe_filename)


# ==============================================================================
# MODELOS PRINCIPALES DEL SISTEMA (AJUSTADOS)
# ==============================================================================


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

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='proveedores', verbose_name="Empresa")
    tipo_servicio = models.CharField(max_length=50, choices=TIPO_SERVICIO_CHOICES, verbose_name="Tipo de Servicio")
    nombre_contacto = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nombre de Contacto")
    numero_contacto = models.CharField(max_length=20, blank=True, null=True, verbose_name="Número de Contacto")
    nombre_empresa = models.CharField(max_length=200, verbose_name="Nombre de la Empresa")
    correo_electronico = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
    pagina_web = models.URLField(blank=True, null=True, verbose_name="Página Web")
    alcance = models.TextField(blank=True, null=True, verbose_name="Alcance (áreas o magnitudes)")
    servicio_prestado = models.TextField(blank=True, null=True, verbose_name="Servicio Prestado")

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


class Equipo(models.Model):
    """Modelo para representar un equipo o instrumento de metrología."""
    TIPO_EQUIPO_CHOICES = [
        ('Equipo de Medición', 'Equipo de Medición'),
        ('Equipo de Referencia', 'Equipo de Referencia'),
        ('Equipo Auxiliar', 'Equipo Auxiliar'),
        ('Otro', 'Otro'),
    ]

    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('En Mantenimiento', 'En Mantenimiento'),
        ('En Calibración', 'En Calibración'),
        ('En Comprobación', 'En Comprobación'),
        ('Inactivo', 'Inactivo'), # NUEVO ESTADO: Equipo que no se usa temporalmente
        ('De Baja', 'De Baja'), # Equipo dado de baja, no vuelve a operar
    ]

    codigo_interno = models.CharField(max_length=100, unique=False, help_text="Código interno único por empresa.") # Se valida la unicidad a nivel de formulario/vista
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Equipo")
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='equipos', verbose_name="Empresa")
    tipo_equipo = models.CharField(max_length=50, choices=TIPO_EQUIPO_CHOICES, verbose_name="Tipo de Equipo")
    marca = models.CharField(max_length=100, blank=True, null=True, verbose_name="Marca")
    modelo = models.CharField(max_length=100, blank=True, null=True, verbose_name="Modelo")
    numero_serie = models.CharField(max_length=100, blank=True, null=True, verbose_name="Número de Serie")
    
    # Campo para la ubicación - ahora como TextField
    ubicacion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ubicación") # Ahora CharField

    responsable = models.CharField(max_length=100, blank=True, null=True, verbose_name="Responsable")
    estado = models.CharField(max_length=50, choices=ESTADO_CHOICES, default='Activo', verbose_name="Estado")
    fecha_adquisicion = models.DateField(blank=True, null=True, verbose_name="Fecha de Adquisición")
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    
    rango_medida = models.CharField(max_length=100, blank=True, null=True, verbose_name="Rango de Medida")
    resolucion = models.CharField(max_length=100, blank=True, null=True, verbose_name="Resolución")
    error_maximo_permisible = models.CharField(max_length=100, blank=True, null=True, verbose_name="Error Máximo Permisible") # Ahora CharField
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
            self.ima_comprobacion = latest_comprobacion.fecha_comprobacion + delta
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
            self.ima_calibracion = fecha_base + delta
        elif self.fecha_adquisicion:
            delta = meses_decimales_a_relativedelta(self.frecuencia_calibracion_meses)
            self.ima_calibracion = self.fecha_adquisicion + delta
        elif self.fecha_registro:
            delta = meses_decimales_a_relativedelta(self.frecuencia_calibracion_meses)
            self.ima_calibracion = self.fecha_registro.date() + delta
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
            self.ima_comprobacion = fecha_base + delta
        elif self.fecha_adquisicion:
            delta = meses_decimales_a_relativedelta(self.frecuencia_comprobacion_meses)
            self.ima_comprobacion = self.fecha_adquisicion + delta
        elif self.fecha_registro:
            delta = meses_decimales_a_relativedelta(self.frecuencia_comprobacion_meses)
            self.ima_comprobacion = self.fecha_registro.date() + delta
        else:
            self.proxima_comprobacion = None


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

    class Meta:
        verbose_name = "Comprobación"
        verbose_name_plural = "Comprobaciones"
        permissions = [
            ("can_view_comprobacion", "Can view comprobacion"),
            ("can_add_comprobacion", "Can add comprobacion"),
            ("can_change_comprobacion", "Can change comprobacion"),
            ("can_delete_comprobacion", "Can delete comprobacion"),
        ]

    def __str__(self):
        return f"Comprobación de {self.equipo.nombre} ({self.fecha_comprobacion})"

    @property
    def proxima_actividad_para_este_registro(self):
        """
        Calcula la próxima fecha de comprobación basada en la fecha de esta comprobación
        y la frecuencia de comprobación del equipo.
        """
        if not self.equipo.frecuencia_comprobacion_meses or not self.fecha_comprobacion:
            return None
        return self.fecha_comprobacion + meses_decimales_a_relativedelta(self.equipo.frecuencia_comprobacion_meses)


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

# ==============================================================================
# MODELO PARA DOCUMENTOS GENÉRICOS (NUEVO)
# ==============================================================================

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


# --- Signals para actualizar el estado del equipo y las próximas fechas ---

@receiver(post_save, sender=Calibracion)
def update_equipo_calibracion_info(sender, instance, **kwargs):
    """Actualiza la fecha de la última y próxima calibración del equipo al guardar una calibración."""
    equipo = instance.equipo
    latest_calibracion = Calibracion.objects.filter(equipo=equipo).order_by('-fecha_calibracion').first()

    if latest_calibracion:
        equipo.fecha_ultima_calibracion = latest_calibracion.fecha_calibracion
    else:
        equipo.fecha_ultima_calibracion = None
    
    # Recalcular la próxima calibración, respetando el estado del equipo
    if equipo.estado not in ['De Baja', 'Inactivo']: # SOLO calcular si está Activo, En Mantenimiento, etc.
        equipo.calcular_proxima_calibracion()
    else:
        equipo.proxima_calibracion = None # Si está de baja o inactivo, no hay próxima programación

    equipo.save(update_fields=['fecha_ultima_calibracion', 'proxima_calibracion'])

@receiver(post_delete, sender=Calibracion)
def update_equipo_calibracion_info_on_delete(sender, instance, **kwargs):
    """Actualiza la fecha de la última y próxima calibración del equipo al eliminar una calibración."""
    equipo = instance.equipo
    latest_calibracion = Calibracion.objects.filter(equipo=equipo).order_by('-fecha_calibracion').first()

    if latest_calibracion:
        equipo.fecha_ultima_calibracion = latest_calibracion.fecha_calibracion
    else:
        equipo.fecha_ultima_calibracion = None
    
    if equipo.estado not in ['De Baja', 'Inactivo']: # Recalcular solo si está activo
        equipo.calcular_proxima_calibracion()
    else:
        equipo.proxima_calibracion = None

    equipo.save(update_fields=['fecha_ultima_calibracion', 'proxima_calibracion'])


@receiver(post_save, sender=Mantenimiento)
def update_equipo_mantenimiento_info(sender, instance, **kwargs):
    """Actualiza la fecha del último y próximo mantenimiento del equipo al guardar un mantenimiento."""
    equipo = instance.equipo
    latest_mantenimiento = Mantenimiento.objects.filter(equipo=equipo).order_by('-fecha_mantenimiento').first()

    if latest_mantenimiento:
        equipo.fecha_ultimo_mantenimiento = latest_mantenimiento.fecha_mantenimiento
    else:
        equipo.fecha_ultimo_mantenimiento = None

    if equipo.estado not in ['De Baja', 'Inactivo']: # Recalcular solo si está activo
        equipo.calcular_proximo_mantenimiento()
    else:
        equipo.proximo_mantenimiento = None

    equipo.save(update_fields=['fecha_ultimo_mantenimiento', 'proximo_mantenimiento'])


@receiver(post_delete, sender=Mantenimiento)
def update_equipo_mantenimiento_info_on_delete(sender, instance, **kwargs):
    """Actualiza la fecha del último y próximo mantenimiento del equipo al eliminar un mantenimiento."""
    equipo = instance.equipo
    latest_mantenimiento = Mantenimiento.objects.filter(equipo=equipo).order_by('-fecha_mantenimiento').first()

    if latest_mantenimiento:
        equipo.fecha_ultimo_mantenimiento = latest_mantenimiento.fecha_mantenimiento
    else:
        equipo.fecha_ultimo_mantenimiento = None
    
    if equipo.estado not in ['De Baja', 'Inactivo']: # Recalcular solo si está activo
        equipo.calcular_proximo_mantenimiento()
    else:
        equipo.proximo_mantenimiento = None

    equipo.save(update_fields=['fecha_ultimo_mantenimiento', 'proximo_mantenimiento'])


@receiver(post_save, sender=Comprobacion)
def update_equipo_comprobacion_info(sender, instance, **kwargs):
    """Actualiza la fecha de la última y próxima comprobación del equipo al guardar una comprobación."""
    equipo = instance.equipo
    latest_comprobacion = Comprobacion.objects.filter(equipo=equipo).order_by('-fecha_comprobacion').first()

    if latest_comprobacion:
        equipo.fecha_ultima_comprobacion = latest_comprobacion.fecha_comprobacion
    else:
        equipo.fecha_ultima_comprobacion = None
    
    if equipo.estado not in ['De Baja', 'Inactivo']: # Recalcular solo si está activo
        equipo.calcular_proxima_comprobacion()
    else:
        equipo.proxima_comprobacion = None

    equipo.save(update_fields=['fecha_ultima_comprobacion', 'proxima_comprobacion'])

@receiver(post_delete, sender=Comprobacion)
def update_equipo_comprobacion_info_on_delete(sender, instance, **kwargs):
    """Actualiza la fecha de la última y próxima comprobación del equipo al eliminar una comprobación."""
    equipo = instance.equipo
    latest_comprobacion = Comprobacion.objects.filter(equipo=equipo).order_by('-fecha_comprobacion').first()

    if latest_comprobacion:
        equipo.fecha_ultima_comprobacion = latest_comprobacion.fecha_comprobacion
    else:
        equipo.fecha_ultima_comprobacion = None
    
    if equipo.estado not in ['De Baja', 'Inactivo']: # Recalcular solo si está activo
        equipo.calcular_proxima_comprobacion()
    else:
        equipo.proxima_comprobacion = None

    equipo.save(update_fields=['fecha_ultima_comprobacion', 'proxima_comprobacion'])


@receiver(post_save, sender=BajaEquipo)
def set_equipo_de_baja(sender, instance, created, **kwargs):
    if created: # Solo actuar cuando se crea un nuevo registro de baja
        equipo = instance.equipo
        # Si el equipo no está ya 'De Baja', se cambia el estado
        if equipo.estado != 'De Baja':
            equipo.estado = 'De Baja'
            # Poner a None las próximas fechas si está de baja
            equipo.proxima_calibracion = None
            equipo.proximo_mantenimiento = None
            equipo.proxima_comprobacion = None
            equipo.save(update_fields=['estado', 'proxima_calibracion', 'proximo_mantenimiento', 'proxima_comprobacion'])

@receiver(post_delete, sender=BajaEquipo)
def set_equipo_activo_on_delete_baja(sender, instance, **kwargs):
    equipo = instance.equipo
    # Solo cambiar a 'Activo' si NO quedan otros registros de baja para este equipo
    if not BajaEquipo.objects.filter(equipo=equipo).exists():
        if equipo.estado == 'De Baja': # Solo cambiar si estaba en estado 'De Baja' por este registro
            equipo.estado = 'Activo' # O el estado por defecto que desees
            # Recalcular las próximas fechas después de reactivar
            equipo.calcular_proxima_calibracion()
            equipo.calcular_proximo_mantenimiento()
            equipo.calcular_proxima_comprobacion()
            equipo.save(update_fields=['estado', 'proxima_calibracion', 'proximo_mantenimiento', 'proxima_comprobacion'])


# ================================
# SISTEMA DE COLA PARA ZIP
# ================================

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


class EmailConfiguration(models.Model):
    """Configuración de email para el sistema."""

    email_backend = models.CharField(
        max_length=100,
        default='django.core.mail.backends.smtp.EmailBackend',
        verbose_name="Backend de Email"
    )
    email_host = models.CharField(
        max_length=100,
        default='smtp.gmail.com',
        verbose_name="Servidor SMTP"
    )
    email_port = models.IntegerField(
        default=587,
        verbose_name="Puerto SMTP"
    )
    email_use_tls = models.BooleanField(
        default=True,
        verbose_name="Usar TLS"
    )
    email_use_ssl = models.BooleanField(
        default=False,
        verbose_name="Usar SSL"
    )
    email_host_user = models.EmailField(
        blank=True,
        verbose_name="Usuario SMTP"
    )
    email_host_password = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Contraseña SMTP"
    )
    default_from_email = models.EmailField(
        default='noreply@sammetrologia.com',
        verbose_name="Email de envío por defecto"
    )
    default_from_name = models.CharField(
        max_length=100,
        default='SAM Metrología',
        verbose_name="Nombre de envío por defecto"
    )
    admin_email = models.EmailField(
        blank=True,
        verbose_name="Email de administrador"
    )
    notification_emails = models.TextField(
        blank=True,
        verbose_name="Emails adicionales",
        help_text="Emails adicionales para notificaciones, separados por coma"
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name="Email activo"
    )
    test_email_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Último email de prueba"
    )
    last_error = models.TextField(
        blank=True,
        verbose_name="Último error"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Actualizado por"
    )

    class Meta:
        verbose_name = "Configuración de Email"
        verbose_name_plural = "Configuraciones de Email"

    def __str__(self):
        return f"Email Config - {self.email_host} ({self.get_status_display()})"

    def get_status_display(self):
        return "Activo" if self.is_active else "Inactivo"

    @classmethod
    def get_active_config(cls):
        """Obtiene la configuración de email activa."""
        return cls.objects.filter(is_active=True).first()

    @classmethod
    def get_current_config(cls):
        """Obtiene la configuración actual o crea una por defecto."""
        config = cls.objects.first()
        if not config:
            config = cls.get_or_create_default()
        return config

    @classmethod
    def get_or_create_default(cls):
        """Obtiene la configuración por defecto o la crea si no existe."""
        config, created = cls.objects.get_or_create(
            defaults={
                'email_host': 'smtp.gmail.com',
                'email_port': 587,
                'email_use_tls': True,
                'default_from_email': 'noreply@sammetrologia.com',
                'default_from_name': 'SAM Metrología',
                'is_active': False
            }
        )
        return config

    def send_test_email(self, test_email=None):
        """Envía un email de prueba con esta configuración."""
        from django.core.mail import send_mail
        from django.conf import settings

        try:
            # Configurar temporalmente Django para usar esta configuración
            original_settings = {}
            email_settings = {
                'EMAIL_BACKEND': self.email_backend,
                'EMAIL_HOST': self.email_host,
                'EMAIL_PORT': self.email_port,
                'EMAIL_USE_TLS': self.email_use_tls,
                'EMAIL_USE_SSL': self.email_use_ssl,
                'EMAIL_HOST_USER': self.email_host_user,
                'EMAIL_HOST_PASSWORD': self.email_host_password,
                'DEFAULT_FROM_EMAIL': self.default_from_email,
            }

            for key, value in email_settings.items():
                original_settings[key] = getattr(settings, key, None)
                setattr(settings, key, value)

            # Enviar email de prueba
            recipient = test_email or self.admin_email or self.email_host_user
            if not recipient:
                raise ValueError("No hay destinatario para el email de prueba")

            send_mail(
                subject='Prueba de Configuración de Email - SAM Metrología',
                message=f'''
                Este es un email de prueba del sistema SAM Metrología.

                Configuración utilizada:
                - Servidor: {self.email_host}:{self.email_port}
                - TLS: {self.email_use_tls}
                - Usuario: {self.email_host_user}
                - Fecha: {timezone.now().strftime('%d/%m/%Y %H:%M')}

                Si recibiste este email, la configuración está funcionando correctamente.
                ''',
                from_email=self.default_from_email,
                recipient_list=[recipient],
                fail_silently=False,
            )

            # Actualizar timestamp de prueba
            self.test_email_sent_at = timezone.now()
            self.last_error = ""
            self.save(update_fields=['test_email_sent_at', 'last_error'])

            # Restaurar configuraciones originales
            for key, value in original_settings.items():
                if value is not None:
                    setattr(settings, key, value)
                else:
                    delattr(settings, key)

            return True, "Email de prueba enviado exitosamente"

        except Exception as e:
            self.last_error = str(e)
            self.save(update_fields=['last_error'])

            # Restaurar configuraciones originales
            for key, value in original_settings.items():
                if value is not None:
                    setattr(settings, key, value)
                elif hasattr(settings, key):
                    delattr(settings, key)

            return False, str(e)

    def test_connection(self):
        """Prueba la conexión SMTP sin enviar email."""
        import smtplib
        import ssl

        try:
            # Crear contexto SSL
            context = ssl.create_default_context()

            # Intentar conexión según el tipo de seguridad
            if self.email_use_ssl:
                # SSL (puerto 465)
                server = smtplib.SMTP_SSL(self.email_host, self.email_port, context=context)
            else:
                # TLS (puerto 587) o sin seguridad
                server = smtplib.SMTP(self.email_host, self.email_port)
                if self.email_use_tls:
                    server.starttls(context=context)

            # Intentar login si hay credenciales
            if self.email_host_user and self.email_host_password:
                server.login(self.email_host_user, self.email_host_password)

            # Cerrar conexión
            server.quit()

            # Actualizar último resultado exitoso
            self.last_error = ""
            self.save(update_fields=['last_error'])

            return True, "Conexión SMTP exitosa"

        except Exception as e:
            # Guardar error
            self.last_error = str(e)
            self.save(update_fields=['last_error'])

            return False, str(e)


class SystemScheduleConfig(models.Model):
    """Configuración de programación de tareas del sistema."""

    # Configuración general
    name = models.CharField(max_length=100, default="Default Schedule", verbose_name="Nombre")
    is_active = models.BooleanField(default=True, verbose_name="Activo")

    # Tareas diarias
    maintenance_daily_enabled = models.BooleanField(default=False, verbose_name="Mantenimiento diario")
    maintenance_daily_time = models.TimeField(default="03:00", verbose_name="Hora mantenimiento")
    maintenance_daily_tasks = models.TextField(default="cache,logs", verbose_name="Tareas mantenimiento")

    notifications_daily_enabled = models.BooleanField(default=True, verbose_name="Notificaciones diarias")
    notifications_daily_time = models.TimeField(default="08:00", verbose_name="Hora notificaciones")
    notifications_daily_types = models.TextField(default="consolidated", verbose_name="Tipos notificaciones")

    # Tareas semanales
    maintenance_weekly_enabled = models.BooleanField(default=True, verbose_name="Mantenimiento semanal")
    maintenance_weekly_day = models.CharField(
        max_length=10,
        choices=[
            ('monday', 'Lunes'),
            ('tuesday', 'Martes'),
            ('wednesday', 'Miércoles'),
            ('thursday', 'Jueves'),
            ('friday', 'Viernes'),
            ('saturday', 'Sábado'),
            ('sunday', 'Domingo'),
        ],
        default='sunday',
        verbose_name="Día semanal"
    )
    maintenance_weekly_time = models.TimeField(default="02:00", verbose_name="Hora semanal")
    maintenance_weekly_tasks = models.TextField(default="all", verbose_name="Tareas semanales")

    notifications_weekly_enabled = models.BooleanField(default=True, verbose_name="Notif. semanales")
    notifications_weekly_day = models.CharField(
        max_length=10,
        choices=[
            ('monday', 'Lunes'),
            ('tuesday', 'Martes'),
            ('wednesday', 'Miércoles'),
            ('thursday', 'Jueves'),
            ('friday', 'Viernes'),
            ('saturday', 'Sábado'),
            ('sunday', 'Domingo'),
        ],
        default='monday',
        verbose_name="Día notif. semanal"
    )
    notifications_weekly_time = models.TimeField(default="09:00", verbose_name="Hora notif. semanal")
    notifications_weekly_types = models.TextField(default="weekly", verbose_name="Tipos notif. semanal")

    # Backup mensual
    backup_monthly_enabled = models.BooleanField(default=True, verbose_name="Backup mensual")
    backup_monthly_day = models.IntegerField(default=1, verbose_name="Día del mes backup")
    backup_monthly_time = models.TimeField(default="01:00", verbose_name="Hora backup")
    backup_monthly_include_files = models.BooleanField(default=False, verbose_name="Incluir archivos")

    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Actualizado por"
    )

    class Meta:
        verbose_name = "Configuración de Programación"
        verbose_name_plural = "Configuraciones de Programación"

    def __str__(self):
        return f"Schedule Config - {self.name} ({'Activo' if self.is_active else 'Inactivo'})"

    @classmethod
    def get_or_create_config(cls):
        """Obtiene la configuración actual o crea una por defecto."""
        config = cls.objects.first()
        if not config:
            config = cls.objects.create(
                name="Configuración Principal",
                is_active=True
            )
        return config

    def get_config(self):
        """Retorna configuración en formato diccionario."""
        return {
            'maintenance_daily': {
                'enabled': self.maintenance_daily_enabled,
                'time': self.maintenance_daily_time.strftime('%H:%M'),
                'tasks': self.maintenance_daily_tasks.split(',')
            },
            'notifications_daily': {
                'enabled': self.notifications_daily_enabled,
                'time': self.notifications_daily_time.strftime('%H:%M'),
                'types': self.notifications_daily_types.split(',')
            },
            'maintenance_weekly': {
                'enabled': self.maintenance_weekly_enabled,
                'day': self.maintenance_weekly_day,
                'time': self.maintenance_weekly_time.strftime('%H:%M'),
                'tasks': self.maintenance_weekly_tasks.split(',')
            },
            'notifications_weekly': {
                'enabled': self.notifications_weekly_enabled,
                'day': self.notifications_weekly_day,
                'time': self.notifications_weekly_time.strftime('%H:%M'),
                'types': self.notifications_weekly_types.split(',')
            },
            'backup_monthly': {
                'enabled': self.backup_monthly_enabled,
                'day': self.backup_monthly_day,
                'time': self.backup_monthly_time.strftime('%H:%M'),
                'include_files': self.backup_monthly_include_files
            }
        }

    def save_config(self, config_dict):
        """Guarda configuración desde diccionario."""
        try:
            if 'maintenance_daily' in config_dict:
                self.maintenance_daily_enabled = config_dict['maintenance_daily']['enabled']
                self.maintenance_daily_time = config_dict['maintenance_daily']['time']
                self.maintenance_daily_tasks = ','.join(config_dict['maintenance_daily']['tasks'])

            if 'notifications_daily' in config_dict:
                self.notifications_daily_enabled = config_dict['notifications_daily']['enabled']
                self.notifications_daily_time = config_dict['notifications_daily']['time']
                self.notifications_daily_types = ','.join(config_dict['notifications_daily']['types'])

            if 'maintenance_weekly' in config_dict:
                self.maintenance_weekly_enabled = config_dict['maintenance_weekly']['enabled']
                self.maintenance_weekly_day = config_dict['maintenance_weekly']['day']
                self.maintenance_weekly_time = config_dict['maintenance_weekly']['time']
                self.maintenance_weekly_tasks = ','.join(config_dict['maintenance_weekly']['tasks'])

            if 'notifications_weekly' in config_dict:
                self.notifications_weekly_enabled = config_dict['notifications_weekly']['enabled']
                self.notifications_weekly_day = config_dict['notifications_weekly']['day']
                self.notifications_weekly_time = config_dict['notifications_weekly']['time']
                self.notifications_weekly_types = ','.join(config_dict['notifications_weekly']['types'])

            if 'backup_monthly' in config_dict:
                self.backup_monthly_enabled = config_dict['backup_monthly']['enabled']
                self.backup_monthly_day = config_dict['backup_monthly']['day']
                self.backup_monthly_time = config_dict['backup_monthly']['time']
                self.backup_monthly_include_files = config_dict['backup_monthly']['include_files']

            self.save()
            return True
        except Exception as e:
            logger.error(f'Error saving schedule config: {e}')
            return False

    @classmethod
    def get_default_config(cls):
        """Configuración por defecto."""
        return {
            'maintenance_daily': {
                'enabled': False,
                'time': '03:00',
                'tasks': ['cache', 'logs']
            },
            'notifications_daily': {
                'enabled': True,
                'time': '08:00',
                'types': ['consolidated']
            },
            'maintenance_weekly': {
                'enabled': True,
                'day': 'sunday',
                'time': '02:00',
                'tasks': ['all']
            },
            'notifications_weekly': {
                'enabled': True,
                'day': 'monday',
                'time': '09:00',
                'types': ['weekly']
            },
            'backup_monthly': {
                'enabled': True,
                'day': 1,
                'time': '01:00',
                'include_files': False
            }
        }




# ==============================================================================
# MODELO DE MÉTRICAS DE EFICIENCIA METROLÓGICA
# ==============================================================================

from django.db import models
from django.utils import timezone
from .models import Empresa

class MetricasEficienciaMetrologica(models.Model):
    """
    Modelo para calcular y almacenar métricas de eficiencia metrológica por empresa.
    """
    empresa = models.OneToOneField(
        Empresa,
        on_delete=models.CASCADE,
        related_name='metricas_eficiencia',
        verbose_name="Empresa"
    )

    # Fecha de cálculo de métricas
    fecha_calculo = models.DateTimeField(auto_now=True, verbose_name="Última actualización")
    periodo_analisis = models.CharField(
        max_length=50,
        default="ANUAL",
        choices=[
            ('MENSUAL', 'Mensual'),
            ('TRIMESTRAL', 'Trimestral'),
            ('ANUAL', 'Anual'),
        ],
        verbose_name="Período de análisis"
    )

    # Métricas de Cumplimiento
    cumplimiento_calibraciones = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name="Cumplimiento Calibraciones (%)",
        help_text="Porcentaje de calibraciones realizadas a tiempo"
    )
    cumplimiento_mantenimientos = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name="Cumplimiento Mantenimientos (%)",
        help_text="Porcentaje de mantenimientos realizados a tiempo"
    )
    cumplimiento_comprobaciones = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name="Cumplimiento Comprobaciones (%)",
        help_text="Porcentaje de comprobaciones realizadas a tiempo"
    )

    # Métricas de Eficiencia Operativa
    trazabilidad_documentacion = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name="Trazabilidad Documentación (%)",
        help_text="Porcentaje de equipos con documentación completa"
    )
    disponibilidad_equipos = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name="Disponibilidad Equipos (%)",
        help_text="Porcentaje de equipos operativos y disponibles"
    )
    tiempo_promedio_gestion = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name="Tiempo Promedio Gestión (días)",
        help_text="Tiempo promedio para resolver actividades metrológicas"
    )

    # Métricas de Calidad
    indice_conformidad = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name="Índice de Conformidad (%)",
        help_text="Porcentaje de actividades que cumplen especificaciones"
    )
    eficacia_procesos = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name="Eficacia de Procesos (%)",
        help_text="Efectividad general de los procesos metrológicos"
    )

    # Métricas Financieras de Eficiencia
    costo_promedio_por_equipo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Costo Promedio por Equipo",
        help_text="Costo promedio anual por equipo gestionado"
    )
    retorno_inversion_metrologia = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name="ROI Metrología (%)",
        help_text="Retorno de inversión en servicios metrológicos"
    )

    # Puntuación General de Eficiencia (0-100)
    puntuacion_eficiencia_general = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name="Puntuación General de Eficiencia",
        help_text="Puntuación general de eficiencia metrológica (0-100)"
    )

    # Estados de Eficiencia
    ESTADO_CHOICES = [
        ('EXCELENTE', 'Excelente (90-100%)'),
        ('BUENO', 'Bueno (75-89%)'),
        ('REGULAR', 'Regular (60-74%)'),
        ('DEFICIENTE', 'Deficiente (40-59%)'),
        ('CRITICO', 'Crítico (<40%)'),
    ]
    estado_eficiencia = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='REGULAR',
        verbose_name="Estado de Eficiencia"
    )

    # Observaciones y recomendaciones
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones",
        help_text="Observaciones sobre la eficiencia metrológica"
    )
    recomendaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name="Recomendaciones",
        help_text="Recomendaciones para mejorar la eficiencia"
    )

    class Meta:
        verbose_name = "Métricas de Eficiencia Metrológica"
        verbose_name_plural = "Métricas de Eficiencia Metrológica"
        ordering = ['-fecha_calculo']

    def __str__(self):
        return f"Eficiencia {self.empresa.nombre} - {self.estado_eficiencia} ({self.puntuacion_eficiencia_general}%)"

    def calcular_puntuacion_general(self):
        """Calcula la puntuación general de eficiencia basada en todas las métricas."""
        # Pesos para cada métrica (deben sumar 100) - SIN ROI
        pesos = {
            'cumplimiento': 40,  # 40% - Cumplimiento de actividades
            'operativa': 35,     # 35% - Eficiencia operativa
            'calidad': 25,       # 25% - Calidad de procesos
            # ROI eliminado del análisis
        }

        # Calcular promedio de cumplimiento
        promedio_cumplimiento = (
            self.cumplimiento_calibraciones +
            self.cumplimiento_mantenimientos +
            self.cumplimiento_comprobaciones
        ) / 3

        # Calcular promedio operativo
        promedio_operativo = (
            self.trazabilidad_documentacion +
            self.disponibilidad_equipos +
            (100 - min(self.tiempo_promedio_gestion * 10, 100))  # Convertir días a porcentaje inverso
        ) / 3

        # Calcular promedio de calidad
        promedio_calidad = (
            self.indice_conformidad +
            self.eficacia_procesos
        ) / 2

        # Sin eficiencia financiera (ROI eliminado)

        # Calcular puntuación ponderada SIN ROI
        puntuacion = (
            (promedio_cumplimiento * pesos['cumplimiento'] / 100) +
            (promedio_operativo * pesos['operativa'] / 100) +
            (promedio_calidad * pesos['calidad'] / 100)
        )

        self.puntuacion_eficiencia_general = round(puntuacion, 2)

        # Determinar estado basado en puntuación
        if puntuacion >= 90:
            self.estado_eficiencia = 'EXCELENTE'
        elif puntuacion >= 75:
            self.estado_eficiencia = 'BUENO'
        elif puntuacion >= 60:
            self.estado_eficiencia = 'REGULAR'
        elif puntuacion >= 40:
            self.estado_eficiencia = 'DEFICIENTE'
        else:
            self.estado_eficiencia = 'CRITICO'

        return puntuacion

    def generar_recomendaciones(self):
        """Genera recomendaciones automáticas basadas en las métricas."""
        recomendaciones = []

        # Recomendaciones por cumplimiento
        if self.cumplimiento_calibraciones < 80:
            recomendaciones.append("• Implementar alertas tempranas para calibraciones próximas a vencer")
        if self.cumplimiento_mantenimientos < 80:
            recomendaciones.append("• Establecer programa preventivo de mantenimientos más riguroso")
        if self.cumplimiento_comprobaciones < 80:
            recomendaciones.append("• Mejorar proceso de seguimiento de comprobaciones periódicas")

        # Recomendaciones operativas
        if self.trazabilidad_documentacion < 90:
            recomendaciones.append("• Digitalizar y completar documentación faltante de equipos")
        if self.disponibilidad_equipos < 85:
            recomendaciones.append("• Revisar equipos inactivos y optimizar mantenimiento preventivo")
        if self.tiempo_promedio_gestion > 15:
            recomendaciones.append("• Optimizar tiempos de respuesta en actividades metrológicas")

        # Recomendaciones de calidad
        if self.indice_conformidad < 85:
            recomendaciones.append("• Reforzar capacitación del personal técnico")
        if self.eficacia_procesos < 80:
            recomendaciones.append("• Revisar y mejorar procedimientos operativos estándar")

        # Sin recomendaciones financieras (ROI eliminado)

        self.recomendaciones = "\n".join(recomendaciones) if recomendaciones else "La empresa mantiene un buen nivel de eficiencia metrológica."

    def save(self, *args, **kwargs):
        """Override save para calcular automáticamente métricas al guardar."""
        self.calcular_puntuacion_general()
        self.generar_recomendaciones()
        super().save(*args, **kwargs)


# ==============================================================================
# MODELO DE SEGUIMIENTO DE NOTIFICACIONES VENCIDAS
# ==============================================================================

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


# ==============================================================================
# MODELOS PARA TÉRMINOS Y CONDICIONES
# ==============================================================================

class TerminosYCondiciones(models.Model):
    """
    Modelo para almacenar las diferentes versiones de Términos y Condiciones.
    Solo puede haber una versión activa a la vez.
    """
    version = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Versión",
        help_text="Ejemplo: 1.0, 1.1, 2.0"
    )
    fecha_vigencia = models.DateField(
        verbose_name="Fecha de Vigencia",
        help_text="Fecha desde la cual estos términos están vigentes"
    )
    titulo = models.CharField(
        max_length=255,
        verbose_name="Título",
        default="Contrato de Licencia de Uso y Provisión de Servicios SaaS"
    )
    contenido_html = models.TextField(
        verbose_name="Contenido HTML",
        help_text="Contenido de los términos en formato HTML",
        blank=True,
        null=True
    )
    archivo_pdf = models.FileField(
        upload_to='contratos/',
        verbose_name="Archivo PDF",
        help_text="PDF del contrato firmado",
        blank=True,
        null=True
    )
    activo = models.BooleanField(
        default=False,
        verbose_name="Activo",
        help_text="Solo una versión puede estar activa a la vez"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")

    class Meta:
        verbose_name = "Términos y Condiciones"
        verbose_name_plural = "Términos y Condiciones"
        ordering = ['-fecha_vigencia', '-version']

    def __str__(self):
        estado = "Activo" if self.activo else "Inactivo"
        return f"Términos v{self.version} ({estado})"

    def save(self, *args, **kwargs):
        """
        Si se marca como activo, desactiva todas las demás versiones.
        """
        if self.activo:
            # Desactivar todas las demás versiones
            TerminosYCondiciones.objects.exclude(pk=self.pk).update(activo=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_terminos_activos(cls):
        """
        Retorna los términos y condiciones actualmente activos.
        """
        return cls.objects.filter(activo=True).first()


class AceptacionTerminos(models.Model):
    """
    Modelo para registrar la aceptación de términos y condiciones por parte de los usuarios.
    Cumple con requisitos legales de trazabilidad (Cláusula 11.1 del contrato).
    """
    usuario = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='aceptaciones_terminos',
        verbose_name="Usuario"
    )
    terminos = models.ForeignKey(
        TerminosYCondiciones,
        on_delete=models.PROTECT,
        related_name='aceptaciones',
        verbose_name="Términos y Condiciones"
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='aceptaciones_terminos',
        verbose_name="Empresa",
        null=True,
        blank=True
    )
    fecha_aceptacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Aceptación"
    )
    ip_address = models.GenericIPAddressField(
        verbose_name="Dirección IP",
        help_text="IP desde la cual se aceptaron los términos"
    )
    user_agent = models.TextField(
        verbose_name="User Agent",
        help_text="Información del navegador utilizado",
        blank=True,
        null=True
    )
    aceptado = models.BooleanField(
        default=True,
        verbose_name="Aceptado",
        help_text="Indica si el usuario aceptó los términos"
    )

    class Meta:
        verbose_name = "Aceptación de Términos"
        verbose_name_plural = "Aceptaciones de Términos"
        ordering = ['-fecha_aceptacion']
        unique_together = ['usuario', 'terminos']
        indexes = [
            models.Index(fields=['usuario', 'terminos']),
            models.Index(fields=['fecha_aceptacion']),
        ]

    def __str__(self):
        return f"{self.usuario.username} aceptó v{self.terminos.version} el {self.fecha_aceptacion.strftime('%Y-%m-%d %H:%M')}"

    @classmethod
    def usuario_acepto_terminos_actuales(cls, usuario):
        """
        Verifica si un usuario ha aceptado los términos y condiciones actualmente activos.

        Retorna:
            bool: True si el usuario aceptó los términos actuales, False en caso contrario.
        """
        terminos_activos = TerminosYCondiciones.get_terminos_activos()
        if not terminos_activos:
            # Si no hay términos activos, no se requiere aceptación
            return True

        return cls.objects.filter(
            usuario=usuario,
            terminos=terminos_activos,
            aceptado=True
        ).exists()

    @classmethod
    def crear_aceptacion(cls, usuario, ip_address, user_agent=None):
        """
        Crea un registro de aceptación de términos para un usuario.

        Args:
            usuario: Instancia de CustomUser
            ip_address: Dirección IP del usuario
            user_agent: User agent del navegador (opcional)

        Returns:
            AceptacionTerminos: Instancia creada o None si no hay términos activos
        """
        terminos_activos = TerminosYCondiciones.get_terminos_activos()
        if not terminos_activos:
            logger.warning("No hay términos y condiciones activos para aceptar")
            return None

        # Verificar si ya aceptó estos términos
        if cls.usuario_acepto_terminos_actuales(usuario):
            logger.info(f"Usuario {usuario.username} ya aceptó los términos v{terminos_activos.version}")
            return None

        # Crear nueva aceptación
        aceptacion = cls.objects.create(
            usuario=usuario,
            terminos=terminos_activos,
            empresa=usuario.empresa if hasattr(usuario, 'empresa') else None,
            ip_address=ip_address,
            user_agent=user_agent or '',
            aceptado=True
        )

        logger.info(f"Usuario {usuario.username} aceptó términos v{terminos_activos.version} desde IP {ip_address}")
        return aceptacion


# ==============================================================================
# MODELOS PARA SISTEMA DE MANTENIMIENTO Y ADMINISTRACIÓN
# ==============================================================================

class MaintenanceTask(models.Model):
    """
    Modelo para tareas de mantenimiento ejecutables desde la web.
    Permite a administradores ejecutar comandos sin acceso SSH.
    """
    TASK_STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('running', 'Ejecutando'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
    ]

    TASK_TYPE_CHOICES = [
        ('backup_db', 'Backup de Base de Datos'),
        ('clear_cache', 'Limpiar Cache'),
        ('cleanup_files', 'Limpiar Archivos Temporales'),
        ('run_tests', 'Ejecutar Tests'),
        ('check_system', 'Verificar Estado del Sistema'),
        ('optimize_db', 'Optimizar Base de Datos'),
        ('collect_static', 'Recolectar Archivos Estáticos'),
        ('migrate_db', 'Aplicar Migraciones'),
        ('custom', 'Comando Personalizado'),
    ]

    task_type = models.CharField(
        max_length=50,
        choices=TASK_TYPE_CHOICES,
        verbose_name="Tipo de Tarea"
    )
    status = models.CharField(
        max_length=20,
        choices=TASK_STATUS_CHOICES,
        default='pending',
        verbose_name="Estado"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Inicio de Ejecución"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fin de Ejecución"
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='maintenance_tasks_created',
        verbose_name="Creado por"
    )
    command = models.TextField(
        blank=True,
        null=True,
        verbose_name="Comando Personalizado",
        help_text="Solo para tipo 'custom'"
    )
    parameters = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Parámetros",
        help_text="Parámetros adicionales en formato JSON"
    )
    output = models.TextField(
        blank=True,
        verbose_name="Salida del Comando"
    )
    error_message = models.TextField(
        blank=True,
        verbose_name="Mensaje de Error"
    )
    duration_seconds = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Duración (segundos)"
    )

    class Meta:
        verbose_name = "Tarea de Mantenimiento"
        verbose_name_plural = "Tareas de Mantenimiento"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['task_type']),
        ]

    def __str__(self):
        return f"{self.get_task_type_display()} - {self.get_status_display()}"

    def get_duration_display(self):
        """Retorna duración en formato legible"""
        if self.duration_seconds is None:
            return "N/A"
        if self.duration_seconds < 60:
            return f"{self.duration_seconds:.1f}s"
        minutes = int(self.duration_seconds // 60)
        seconds = int(self.duration_seconds % 60)
        return f"{minutes}m {seconds}s"


class CommandLog(models.Model):
    """
    Log detallado de ejecución de comandos de mantenimiento.
    Guarda historial completo para auditoría.
    """
    task = models.ForeignKey(
        MaintenanceTask,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name="Tarea"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Timestamp"
    )
    level = models.CharField(
        max_length=10,
        choices=[
            ('DEBUG', 'Debug'),
            ('INFO', 'Info'),
            ('WARNING', 'Advertencia'),
            ('ERROR', 'Error'),
        ],
        default='INFO',
        verbose_name="Nivel"
    )
    message = models.TextField(
        verbose_name="Mensaje"
    )

    class Meta:
        verbose_name = "Log de Comando"
        verbose_name_plural = "Logs de Comandos"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['task', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.level} - {self.message[:50]}"


class SystemHealthCheck(models.Model):
    """
    Registro de verificaciones de salud del sistema.
    Se genera automáticamente o manualmente.
    """
    checked_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Verificación"
    )
    checked_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Verificado por"
    )
    overall_status = models.CharField(
        max_length=20,
        choices=[
            ('healthy', 'Saludable'),
            ('warning', 'Advertencia'),
            ('critical', 'Crítico'),
        ],
        default='healthy',
        verbose_name="Estado General"
    )
    database_status = models.CharField(max_length=20, default='unknown')
    cache_status = models.CharField(max_length=20, default='unknown')
    storage_status = models.CharField(max_length=20, default='unknown')

    database_response_time = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Tiempo de Respuesta DB (ms)"
    )
    cache_response_time = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Tiempo de Respuesta Cache (ms)"
    )

    total_empresas = models.IntegerField(default=0)
    total_equipos = models.IntegerField(default=0)
    total_usuarios = models.IntegerField(default=0)

    disk_usage_mb = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Uso de Disco (MB)"
    )

    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Detalles Adicionales"
    )

    notes = models.TextField(
        blank=True,
        verbose_name="Notas"
    )

    class Meta:
        verbose_name = "Verificación de Salud"
        verbose_name_plural = "Verificaciones de Salud"
        ordering = ['-checked_at']
        indexes = [
            models.Index(fields=['-checked_at']),
            models.Index(fields=['overall_status']),
        ]

    def __str__(self):
        return f"Health Check - {self.checked_at.strftime('%Y-%m-%d %H:%M')} - {self.get_overall_status_display()}"