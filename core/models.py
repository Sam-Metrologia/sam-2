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

# ==============================================================================
# MODELO DE USUARIO PERSONALIZADO (AÑADIDO Y AJUSTADO)
# ==============================================================================

class Empresa(models.Model):
    # Constantes para planes
    PLAN_GRATUITO_EQUIPOS = 5
    PLAN_GRATUITO_ALMACENAMIENTO_MB = 500  # 500MB para plan gratuito
    TRIAL_EQUIPOS = 50
    TRIAL_ALMACENAMIENTO_MB = 2048  # 2GB para trial
    TRIAL_DURACION_DIAS = 7

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
    es_periodo_prueba = models.BooleanField(default=False, verbose_name="¿Es Período de Prueba? (Deprecado)")
    duracion_prueba_dias = models.IntegerField(default=7, verbose_name="Duración Prueba (días)")
    fecha_inicio_plan = models.DateField(blank=True, null=True, verbose_name="Fecha Inicio Plan")
    
    # Campo para el límite de equipos (ahora el único y principal)
    limite_equipos_empresa = models.IntegerField(default=5, verbose_name="Límite Máximo de Equipos")
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
        elif estado_plan in ["Plan Expirado", "Período de Prueba Expirado"]:
            # Plan expirado: reducir a plan gratuito
            return self.PLAN_GRATUITO_EQUIPOS
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
        elif estado_plan in ["Plan Expirado", "Período de Prueba Expirado"]:
            # Plan expirado: reducir a plan gratuito
            return self.PLAN_GRATUITO_ALMACENAMIENTO_MB
        else:
            # Plan activo: usar el límite configurado en la empresa
            return self.limite_almacenamiento_mb

    def get_plan_actual(self):
        """Determina el tipo de plan actual basado en la lógica existente."""
        estado_plan = self.get_estado_suscripcion_display()

        if estado_plan == "Período de Prueba Activo":
            return 'trial'
        elif estado_plan in ["Plan Expirado", "Período de Prueba Expirado"]:
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

    def transicion_a_plan_gratuito(self):
        """
        Transiciona la empresa al plan gratuito usando campos existentes.
        Se usa cuando expira el trial o plan pagado.
        """
        # Limpiar configuración de planes
        self.es_periodo_prueba = False
        self.fecha_inicio_plan = None
        self.duracion_suscripcion_meses = None

        # Aplicar límites del plan gratuito
        self.limite_equipos_empresa = self.PLAN_GRATUITO_EQUIPOS
        self.limite_almacenamiento_mb = self.PLAN_GRATUITO_ALMACENAMIENTO_MB

        # Actualizar estados
        self.estado_suscripcion = 'Expirado'

        self.save()

        # Log de la transición
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Empresa {self.nombre} transicionada a plan gratuito")

    def verificar_y_procesar_expiraciones(self):
        """
        Verifica y procesa automáticamente las expiraciones usando la lógica existente.
        Este método debe ser llamado periódicamente por un comando de mantenimiento.
        """
        estado_plan = self.get_estado_suscripcion_display()
        cambio_realizado = False

        # Si el plan está expirado, transicionar a plan gratuito
        if estado_plan in ["Plan Expirado", "Período de Prueba Expirado"]:
            # Solo transicionar si no está ya en plan gratuito
            if self.limite_equipos_empresa != self.PLAN_GRATUITO_EQUIPOS:
                self.transicion_a_plan_gratuito()
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

        # Crear clave de cache única para esta empresa
        cache_key = f"storage_usage_empresa_{self.id}_v2"

        # Intentar obtener del cache (válido por 10 minutos) con fallback graceful
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

        # Guardar en cache por 10 minutos (600 segundos) con fallback graceful
        try:
            cache.set(cache_key, total_size_mb, 600)
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

    @property
    def has_export_permission(self):
        """Verifica si el usuario tiene permiso para exportar informes."""
        return self.has_perm('core.can_export_reports')


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
    numero_serie = models.CharField(max_length=100, unique=True, blank=True, null=True, verbose_name="Número de Serie")
    
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
            # Convertir Decimal a int para relativedelta si es un número entero
            freq = int(self.frecuencia_calibracion_meses)
            self.proxima_calibracion = latest_calibracion.fecha_calibracion + relativedelta(months=freq)
        else:
            # Si no hay calibraciones previas, proyectar desde la fecha de adquisición o registro del equipo
            base_date = self.fecha_adquisicion if self.fecha_adquisicion else self.fecha_registro.date()
            if base_date:
                freq = int(self.frecuencia_calibracion_meses)
                self.proxima_calibracion = base_date + relativedelta(months=freq)
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
            freq = int(self.frecuencia_mantenimiento_meses)
            self.proximo_mantenimiento = latest_mantenimiento.fecha_mantenimiento + relativedelta(months=freq)
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
                freq = int(self.frecuencia_mantenimiento_meses)
                self.proximo_mantenimiento = base_date + relativedelta(months=freq)
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
            freq = int(self.frecuencia_comprobacion_meses)
            self.proxima_comprobacion = latest_comprobacion.fecha_comprobacion + relativedelta(months=freq)
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
                freq = int(self.frecuencia_comprobacion_meses)
                self.proxima_comprobacion = base_date + relativedelta(months=freq)
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
            freq = int(self.frecuencia_calibracion_meses)
            self.proxima_calibracion = fecha_base + relativedelta(months=freq)
        elif self.fecha_adquisicion:
            freq = int(self.frecuencia_calibracion_meses)
            self.proxima_calibracion = self.fecha_adquisicion + relativedelta(months=freq)
        elif self.fecha_registro:
            freq = int(self.frecuencia_calibracion_meses)
            self.proxima_calibracion = self.fecha_registro.date() + relativedelta(months=freq)
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
            freq = int(self.frecuencia_mantenimiento_meses)
            self.proximo_mantenimiento = fecha_base + relativedelta(months=freq)
        elif self.fecha_adquisicion:
            freq = int(self.frecuencia_mantenimiento_meses)
            self.proximo_mantenimiento = self.fecha_adquisicion + relativedelta(months=freq)
        elif self.fecha_registro:
            freq = int(self.frecuencia_mantenimiento_meses)
            self.proximo_mantenimiento = self.fecha_registro.date() + relativedelta(months=freq)
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
            freq = int(self.frecuencia_comprobacion_meses)
            self.proxima_comprobacion = fecha_base + relativedelta(months=freq)
        elif self.fecha_adquisicion:
            freq = int(self.frecuencia_comprobacion_meses)
            self.proxima_comprobacion = self.fecha_adquisicion + relativedelta(months=freq)
        elif self.fecha_registro:
            freq = int(self.frecuencia_comprobacion_meses)
            self.proxima_comprobacion = self.fecha_registro.date() + relativedelta(months=freq)
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

    class Meta:
        verbose_name = "Solicitud de ZIP"
        verbose_name_plural = "Solicitudes de ZIP"
        ordering = ['position_in_queue', 'created_at']
        indexes = [
            models.Index(fields=['status', 'position_in_queue']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['empresa', 'status']),
        ]

    def __str__(self):
        return f"ZIP {self.id} - {self.user.username} - {self.get_status_display()}"

    def get_estimated_wait_time(self):
        """Calcula tiempo estimado de espera en minutos."""
        if self.status != 'pending':
            return 0

        # Contar solicitudes pendientes antes de esta
        pending_before = ZipRequest.objects.filter(
            status='pending',
            position_in_queue__lt=self.position_in_queue
        ).count()

        # Estimar 4 minutos por ZIP
        return pending_before * 4

    def get_current_position(self):
        """Obtiene la posición actual en la cola."""
        if self.status != 'pending':
            return 0

        return ZipRequest.objects.filter(
            status='pending',
            position_in_queue__lt=self.position_in_queue
        ).count() + 1
