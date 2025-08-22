# core/models.py
# Ajustado para la lógica de la primera programación de mantenimiento y comprobación
# y para la implementación de planes de suscripción simplificados.

from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from datetime import date, timedelta
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
    # Campos para la lógica de suscripción (Simplificados)
    es_periodo_prueba = models.BooleanField(default=False, verbose_name="¿Es Período de Prueba?")
    duracion_prueba_dias = models.IntegerField(default=30, verbose_name="Duración Prueba (días)")
    fecha_inicio_plan = models.DateField(blank=True, null=True, verbose_name="Fecha Inicio Plan")
    
    # Campo para el límite de equipos (ahora el único y principal)
    limite_equipos_empresa = models.IntegerField(default=5, verbose_name="Límite Máximo de Equipos")
    duracion_suscripcion_meses = models.IntegerField(default=12, blank=True, null=True, verbose_name="Duración Suscripción (meses)")
    
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
        """Retorna el límite de equipos basado en el plan o si es prueba/acceso manual."""
        if self.acceso_manual_activo:
            # Si el acceso es manual, el límite es infinito (o un número muy grande)
            return float('inf') 
        elif self.es_periodo_prueba:
            # Durante el período de prueba, el límite es un valor predefinido (ej. 5 equipos)
            # Podrías usar self.duracion_prueba_dias como límite si así lo deseas,
            # o un valor fijo como 5, 10, etc.
            return 5 # Ejemplo: un límite fijo de 5 equipos durante la prueba
        elif self.limite_equipos_empresa is not None:
            return self.limite_equipos_empresa
        return 0 # Si no hay plan ni prueba activa, el límite es 0

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
        return f"{self.nombre} - Límite: {self.limite_equipos}"


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


# ==============================================================================
# FUNCIONES PARA RUTAS DE SUBIDA DE ARCHIVOS (AJUSTADAS)
# ==============================================================================

def get_upload_path(instance, filename):
    """
    Define la ruta de subida para los archivos de equipo y sus actividades.
    Esta función ahora genera la ruta RELATIVA DENTRO del prefijo MEDIA_LOCATION.
    """
    # Convertir el nombre del archivo a un formato seguro
    safe_filename = filename.replace('/', '_').replace('\\', '_').replace(' ', '_')

    # Determinar la subcarpeta base según el tipo de instancia
    base_folder_segments = []

    if isinstance(instance, Empresa):
        base_folder_segments.append("empresas_logos")
        if instance.nombre:
            base_folder_segments.append(instance.nombre.replace('/', '_').replace('\\', '_').replace(' ', '_'))
    elif isinstance(instance, Equipo):
        base_folder_segments.append("equipos")
        if instance.codigo_interno:
            base_folder_segments.append(instance.codigo_interno.replace('/', '_').replace('\\', '_').replace(' ', '_'))
    elif hasattr(instance, 'equipo') and hasattr(instance.equipo, 'codigo_interno'):
        # Para modelos relacionados con Equipo (Calibracion, Mantenimiento, Comprobacion, BajaEquipo)
        base_folder_segments.append("equipos")
        base_folder_segments.append(instance.equipo.codigo_interno.replace('/', '_').replace('\\', '_').replace(' ', '_'))
    elif isinstance(instance, Procedimiento):
        base_folder_segments.append("procedimientos")
        if instance.codigo:
            base_folder_segments.append(instance.codigo.replace('/', '_').replace('\\', '_').replace(' ', '_'))
    elif isinstance(instance, Documento):
        base_folder_segments.append("generales")
        # Para documentos genéricos, el nombre del archivo ya puede incluir un UUID si es nuevo
        # La ruta final será: media/generales/{safe_filename}
        return os.path.join(settings.AWS_LOCATION, *base_folder_segments, safe_filename)

    if not base_folder_segments:
        raise AttributeError(f"No se pudo determinar la carpeta base para la instancia de tipo {type(instance).__name__}. Asegúrese de que tiene un código o nombre definido.")

    # Determinar subcarpeta específica para el tipo de documento dentro de la base_folder
    sub_subfolder_segments = []
    if isinstance(instance, Calibracion):
        sub_subfolder_segments.append("calibraciones")
        if 'confirmacion' in filename.lower():
            sub_subfolder_segments.append("confirmaciones")
        elif 'intervalos' in filename.lower():
            sub_subfolder_segments.append("intervalos")
        else:
            sub_subfolder_segments.append("certificados")
    elif isinstance(instance, Mantenimiento):
        sub_subfolder_segments.append("mantenimientos")
    elif isinstance(instance, Comprobacion):
        sub_subfolder_segments.append("comprobaciones")
    elif isinstance(instance, BajaEquipo):
        sub_subfolder_segments.append("bajas_equipo")
    elif isinstance(instance, Equipo):
        sub_subfolder_segments.append("documentos_equipo")
        if 'compra' in filename.lower():
            sub_subfolder_segments.append("compra")
        elif 'ficha_tecnica' in filename.lower() or 'ficha-tecnica' in filename.lower():
            sub_subfolder_segments.append("ficha_tecnica")
        elif 'manual' in filename.lower():
            sub_subfolder_segments.append("manuales")
        elif filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            sub_subfolder_segments.append("imagenes")
        else:
            sub_subfolder_segments.append("otros_documentos")
    elif isinstance(instance, Procedimiento):
        pass # La base_folder_segments ya incluye el código del procedimiento

    # Unir todos los segmentos de la ruta, incluyendo settings.AWS_LOCATION al inicio
    # Esto asegura que la ruta final en S3 sea media/ruta/subcarpeta/archivo.ext
    full_path_segments = [settings.AWS_LOCATION] + base_folder_segments + sub_subfolder_segments + [safe_filename]
    # Limpiar segmentos vacíos y unirlos
    return os.path.join(*[s for s in full_path_segments if s])


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
        verbose_name_plural = "Procedimientos" # CORREGIDO: verbose_plural a verbose_name_plural
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
        Sobreescribe save para calcular las próximas fechas antes de guardar
        y para asegurar que solo se llame a super().save() una vez.
        """
        is_new = self.pk is None
        
        # Calcular las próximas fechas ANTES de guardar, para que estén disponibles en el primer save
        # y para que los signals no tengan que recalcular desde cero.
        self.calcular_proxima_calibracion()
        self.calcular_proximo_mantenimiento()
        self.calcular_proxima_comprobacion()

        # Llamar al método save original.
        # Los signals post_save se encargarán de guardar de nuevo con update_fields
        # si se actualizan las fechas de última actividad.
        super().save(*args, **kwargs)


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
            # Si no hay mantenimientos previos, proyectar desde la fecha de adquisición o registro del equipo
            base_date = self.fecha_adquisicion if self.fecha_adquisicion else self.fecha_registro.date()
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
            # Si no hay comprobaciones previas, proyectar desde la fecha de adquisición o registro del equipo
            base_date = self.fecha_adquisicion if self.fecha_adquisicion else self.fecha_registro.date()
            if base_date:
                freq = int(self.frecuencia_comprobacion_meses)
                self.proxima_comprobacion = base_date + relativedelta(months=freq)
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
        if self.archivo_s3_path:
            from django.core.files.storage import default_storage # Importar aquí para evitar dependencia circular
            return default_storage.url(self.archivo_s3_path)
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