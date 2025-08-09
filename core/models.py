# core/models.py
# Ajustado para la lógica de la primera programación de mantenimiento y comprobación

from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission # Asegúrate de que Group y Permission estén aquí
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from datetime import date, timedelta
from django.utils import timezone # Importar timezone para obtener la fecha actual con zona horaria
import decimal # Importar el módulo decimal (mantener por si otros campos lo usan o se necesita para importación/exportación de otros numéricos)
import os
from django.utils.translation import gettext_lazy as _
from dateutil.relativedelta import relativedelta # Mantener por si se necesita para otros cálculos, aunque no para este específico
from django.conf import settings # ¡ASEGURARSE DE QUE ESTA LÍNEA ESTÉ PRESENTE!
import calendar # Importar calendar para nombres de meses


# ==============================================================================
# MODELO DE USUARIO PERSONALIZADO (AÑADIDO Y AJUSTADO)
# ==============================================================================

# Define las opciones para los campos Cargo y Sede (si se necesitan)
# Aunque no están en la versión final que generé, los mantengo como referencia
# por si decides reincorporarlos con los related_name correctos si los necesitas.
# CARGO_CHOICES = [
#     ('Gerente', 'Gerente'),
#     ('Coordinador', 'Coordinador'),
#     ('Técnico', 'Técnico'),
#     ('Asistente', 'Asistente'),
#     ('Otro', 'Otro'),
# ]

# SEDE_CHOICES = [
#     ('Sede A', 'Sede A'),
#     ('Sede B', 'Sede B'),
#     ('Sede C', 'Sede C'),
#     ('Otra', 'Otra'),
# ]

class Empresa(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
    nit = models.CharField(max_length=50, unique=True, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    logo_empresa = models.ImageField(upload_to='empresas_logos/', blank=True, null=True) # Simplificado upload_to
    fecha_registro = models.DateTimeField(auto_now_add=True)
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


class CustomUser(AbstractUser):
    """
    Modelo de usuario personalizado para añadir campos adicionales como la empresa a la que pertenece.
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True, related_name='usuarios_empresa') # Cambiado related_name
    # Puedes añadir más campos específicos para tu usuario aquí si es necesario
    # perfil_completo = models.BooleanField(default=False) # Si lo necesitas, descomenta
    # cargo = models.CharField(max_length=50, choices=CARGO_CHOICES, default='Otro') # Si lo necesitas, descomenta
    # sede = models.CharField(max_length=50, choices=SEDE_CHOICES, default='Otra') # Si lo necesitas, descomenta

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
    """Define la ruta de subida para los archivos de equipo y sus actividades."""
    base_code = None
    if isinstance(instance, Equipo):
        base_code = instance.codigo_interno
    elif hasattr(instance, 'equipo') and hasattr(instance.equipo, 'codigo_interno'):
        base_code = instance.equipo.codigo_interno
    
    if not base_code:
        # Si no se puede determinar el código, usar un nombre genérico o lanzar un error
        raise AttributeError(f"No se pudo determinar el código interno del equipo para la instancia de tipo {type(instance).__name__}. Asegúrese de que el equipo tiene un código interno definido.")

    # Convertir el código a un formato seguro para el nombre de archivo
    # Usamos slugify si tu proyecto lo permite o simplemente reemplazamos caracteres
    safe_base_code = base_code.replace('/', '_').replace('\\', '_').replace(' ', '_')

    # Construir la ruta base dentro de MEDIA_ROOT
    base_path = f"equipos/{safe_base_code}/"

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
            subfolder = "documentos_equipos/compra/"
        elif 'ficha_tecnica' in filename.lower() or 'ficha-tecnica' in filename.lower():
            subfolder = "documentos_equipos/ficha_tecnica/"
        elif 'manual' in filename.lower():
            subfolder = "documentos_equipos/manuales/"
        elif filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            subfolder = "imagenes_equipos/"
        else:
            subfolder = "documentos_equipos/otros/"
    
    # Asegurarse de que el nombre del archivo es seguro
    # Es buena práctica normalizar el nombre del archivo para evitar problemas
    # Puedes usar slugify de django.utils.text si lo tienes instalado
    # from django.utils.text import slugify
    # safe_filename = slugify(os.path.splitext(filename)[0]) + os.path.splitext(filename)[1]
    safe_filename = filename # Por simplicidad, se mantiene el nombre original, pero es un punto de mejora

    return os.path.join(base_path, subfolder, safe_filename)


# La función get_empresa_logo_upload_path se ha simplificado y no es necesaria una función separada
# ya que el upload_to de logo_empresa en el modelo Empresa puede ser una cadena directa.


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


class Equipo(models.Model):
    TIPO_EQUIPO_CHOICES = [
        ('Equipo de Medición', 'Equipo de Medición'),
        ('Equipo de Referencia', 'Equipo de Referencia'),
        ('Equipo Auxiliar', 'Equipo Auxiliar'),
        ('Otro', 'Otro'),
    ]

    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('De Baja', 'De Baja'),
        ('En Mantenimiento', 'En Mantenimiento'),
        ('En Calibración', 'En Calibración'),
        ('En Comprobación', 'En Comprobación'),
    ]

    codigo_interno = models.CharField(max_length=100, unique=True, verbose_name="Código Interno")
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Equipo")
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='equipos', verbose_name="Empresa")
    tipo_equipo = models.CharField(max_length=50, choices=TIPO_EQUIPO_CHOICES, verbose_name="Tipo de Equipo")
    marca = models.CharField(max_length=100, blank=True, null=True, verbose_name="Marca")
    modelo = models.CharField(max_length=100, blank=True, null=True, verbose_name="Modelo")
    numero_serie = models.CharField(max_length=100, unique=True, blank=True, null=True, verbose_name="Número de Serie")
    ubicacion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ubicación") # Ahora CharField
    responsable = models.CharField(max_length=100, blank=True, null=True, verbose_name="Responsable")
    estado = models.CharField(max_length=50, choices=ESTADO_CHOICES, default='Activo', verbose_name="Estado")
    fecha_adquisicion = models.DateField(blank=True, null=True, verbose_name="Fecha de Adquisición")
    rango_medida = models.CharField(max_length=100, blank=True, null=True, verbose_name="Rango de Medida")
    resolucion = models.CharField(max_length=100, blank=True, null=True, verbose_name="Resolución")
    error_maximo_permisible = models.CharField(max_length=100, blank=True, null=True, verbose_name="Error Máximo Permisible") # Ahora CharField
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")

    # Campos para documentos
    archivo_compra_pdf = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Archivo de Compra (PDF)")
    ficha_tecnica_pdf = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Ficha Técnica (PDF)")
    manual_pdf = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Manual (PDF)")
    otros_documentos_pdf = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Otros Documentos (PDF)")
    imagen_equipo = models.ImageField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Imagen del Equipo")

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

    def __str__(self):
        return f"{self.nombre} ({self.codigo_interno})"

    # Métodos para calcular próximas fechas (mejorados con fecha de adquisición como base inicial)
    def calcular_proxima_calibracion(self):
        if self.estado == 'De Baja':
            self.proxima_calibracion = None
            return

        base_date = self.fecha_ultima_calibracion
        if not base_date and self.fecha_adquisicion: # Si no hay última calibración, usar fecha de adquisición
            base_date = self.fecha_adquisicion

        frequency = self.frecuencia_calibracion_meses
        
        if base_date and frequency is not None and frequency > 0:
            # Usamos un promedio de 30.4375 días por mes (365.25 / 12) para mayor precisión
            # Redondeamos al día completo más cercano
            total_days = int(round(frequency * decimal.Decimal('30.4375')))
            self.proxima_calibracion = base_date + timedelta(days=total_days)

            # Si la fecha calculada ya pasó, avanzar al próximo ciclo desde hoy
            if self.proxima_calibracion < date.today():
                diff_months = ((date.today().year - base_date.year) * 12 + date.today().month - base_date.month)
                num_intervals_passed = 0
                if frequency > 0:
                    num_intervals_passed = max(0, (diff_months + int(frequency) - 1) // int(frequency))
                
                # Calcular la próxima fecha a partir de la fecha base más los intervalos pasados
                # Esto es para saltar los ciclos ya pasados y empezar desde el ciclo futuro más cercano
                next_base = base_date + relativedelta(months=int(num_intervals_passed * frequency))
                
                # Asegurarse de que next_base sea al menos hoy si la frecuencia es muy pequeña
                if next_base < date.today():
                    next_base = date.today()
                    
                self.proxima_calibracion = next_base + relativedelta(months=int(frequency))

        else:
            self.proxima_calibracion = None

    def calcular_proximo_mantenimiento(self):
        if self.estado == 'De Baja':
            self.proximo_mantenimiento = None
            return

        base_date = self.fecha_ultimo_mantenimiento
        if not base_date and self.fecha_adquisicion:
            base_date = self.fecha_adquisicion

        frequency = self.frecuencia_mantenimiento_meses
            
        if base_date and frequency is not None and frequency > 0:
            total_days = int(round(frequency * decimal.Decimal('30.4375')))
            self.proximo_mantenimiento = base_date + timedelta(days=total_days)

            if self.proximo_mantenimiento < date.today():
                diff_months = ((date.today().year - base_date.year) * 12 + date.today().month - base_date.month)
                num_intervals_passed = 0
                if frequency > 0:
                    num_intervals_passed = max(0, (diff_months + int(frequency) - 1) // int(frequency))
                
                next_base = base_date + relativedelta(months=int(num_intervals_passed * frequency))
                
                if next_base < date.today():
                    next_base = date.today()

                self.proximo_mantenimiento = next_base + relativedelta(months=int(frequency))

        else:
            self.proximo_mantenimiento = None


    def calcular_proxima_comprobacion(self):
        if self.estado == 'De Baja':
            self.proxima_comprobacion = None
            return

        base_date = self.fecha_ultima_comprobacion
        if not base_date and self.fecha_adquisicion:
            base_date = self.fecha_adquisicion

        frequency = self.frecuencia_comprobacion_meses
            
        if base_date and frequency is not None and frequency > 0:
            total_days = int(round(frequency * decimal.Decimal('30.4375')))
            self.proxima_comprobacion = base_date + timedelta(days=total_days)

            if self.proxima_comprobacion < date.today():
                diff_months = ((date.today().year - base_date.year) * 12 + date.today().month - base_date.month)
                num_intervals_passed = 0
                if frequency > 0:
                    num_intervals_passed = max(0, (diff_months + int(frequency) - 1) // int(frequency))
                
                next_base = base_date + relativedelta(months=int(num_intervals_passed * frequency))
                
                if next_base < date.today():
                    next_base = date.today()

                self.proxima_comprobacion = next_base + relativedelta(months=int(frequency))
        else:
            self.proxima_comprobacion = None

    def save(self, *args, **kwargs):
        # Recalcular las fechas próximas antes de guardar el Equipo
        # Esto asegura que los campos proxima_X estén actualizados
        # incluso si el equipo se guarda directamente y no a través de una actividad.
        self.calcular_proxima_calibracion()
        self.calcular_proximo_mantenimiento()
        self.calcular_proxima_comprobacion()
        
        super().save(*args, **kwargs)


# Modelo para Calibración
class Calibracion(models.Model):
    RESULTADO_CHOICES = [
        ('Cumple', 'Cumple'),
        ('No Cumple', 'No Cumple'),
    ]

    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='calibraciones', verbose_name="Equipo")
    fecha_calibracion = models.DateField(verbose_name="Fecha de Calibración")
    nombre_proveedor = models.CharField(max_length=200, verbose_name="Nombre del Proveedor de Calibración", blank=True, null=True)
    resultado = models.CharField(max_length=10, choices=RESULTADO_CHOICES, verbose_name="Resultado", default='Cumple')
    numero_certificado = models.CharField(max_length=100, blank=True, null=True, verbose_name="Número de Certificado")
    documento_calibracion = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Certificado de Calibración (PDF)")
    confirmacion_metrologica_pdf = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Confirmación Metrológica (PDF)")
    intervalos_calibracion_pdf = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Intervalos de Calibración (PDF)") # NUEVO CAMPO
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")

    class Meta:
        verbose_name = "Calibración"
        verbose_name_plural = "Calibraciones"
        ordering = ['-fecha_calibracion']
        permissions = [
            ("can_view_calibracion", "Can view calibracion"),
            ("can_add_calibracion", "Can add calibracion"),
            ("can_change_calibracion", "Can change calibracion"),
            ("can_delete_calibracion", "Can delete calibracion"),
        ]

    def __str__(self):
        return f"Calibración de {self.equipo.nombre} ({self.equipo.codigo_interno}) - {self.fecha_calibracion}"


# Modelo para Mantenimiento
class Mantenimiento(models.Model):
    TIPO_MANTENIMIENTO_CHOICES = [
        ('Preventivo', 'Preventivo'),
        ('Correctivo', 'Correctivo'),
        ('Predictivo', 'Predictivo'),
        ('Inspección', 'Inspección'),
    ]

    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='mantenimientos', verbose_name="Equipo")
    fecha_mantenimiento = models.DateField(verbose_name="Fecha de Mantenimiento")
    nombre_proveedor = models.CharField(max_length=200, verbose_name="Nombre del Proveedor de Mantenimiento", blank=True, null=True)
    responsable = models.CharField(max_length=100, blank=True, null=True, verbose_name="Responsable del Mantenimiento")
    tipo_mantenimiento = models.CharField(max_length=50, choices=TIPO_MANTENIMIENTO_CHOICES, verbose_name="Tipo de Mantenimiento")
    costo = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Costo")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción del Trabajo")
    documento_mantenimiento = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Documento de Mantenimiento (PDF)")

    class Meta:
        verbose_name = "Mantenimiento"
        verbose_name_plural = "Mantenimientos"
        ordering = ['-fecha_mantenimiento']
        permissions = [
            ("can_view_mantenimiento", "Can view mantenimiento"),
            ("can_add_mantenimiento", "Can add mantenimiento"),
            ("can_change_mantenimiento", "Can change mantenimiento"),
            ("can_delete_mantenimiento", "Can delete mantenimiento"),
        ]

    def __str__(self):
        return f"Mantenimiento de {self.equipo.nombre} ({self.equipo.codigo_interno}) - {self.fecha_mantenimiento}"


# Modelo para Comprobación
class Comprobacion(models.Model):
    RESULTADO_CHOICES = [
        ('Aprobado', 'Aprobado'),
        ('Rechazado', 'Rechazado'),
    ]

    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='comprobaciones', verbose_name="Equipo")
    fecha_comprobacion = models.DateField(verbose_name="Fecha de Comprobación")
    nombre_proveedor = models.CharField(max_length=200, verbose_name="Nombre del Proveedor de Comprobación", blank=True, null=True)
    responsable = models.CharField(max_length=100, blank=True, null=True, verbose_name="Responsable de la Comprobación")
    resultado = models.CharField(max_length=10, choices=RESULTADO_CHOICES, verbose_name="Resultado")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    documento_comprobacion = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Documento de Comprobación (PDF)")

    class Meta:
        verbose_name = "Comprobación"
        verbose_name_plural = "Comprobaciones"
        ordering = ['-fecha_comprobacion']
        permissions = [
            ("can_view_comprobacion", "Can view comprobacion"),
            ("can_add_comprobacion", "Can add comprobacion"),
            ("can_change_comprobacion", "Can change comprobacion"),
            ("can_delete_comprobacion", "Can delete comprobacion"),
        ]

    def __str__(self):
        return f"Comprobación de {self.equipo.nombre} ({self.equipo.codigo_interno}) - {self.fecha_comprobacion}"


# Modelo para Baja de Equipo
class BajaEquipo(models.Model):
    equipo = models.OneToOneField(Equipo, on_delete=models.CASCADE, related_name='baja_registro', verbose_name="Equipo")
    razon_baja = models.TextField(verbose_name="Razón de Baja")
    fecha_baja = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Baja")
    dado_de_baja_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Dado de Baja Por")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones Adicionales")
    documento_baja = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Documento de Baja (PDF)")

    class Meta:
        verbose_name = "Baja de Equipo"
        verbose_name_plural = "Bajas de Equipo"
        ordering = ['-fecha_baja']
        permissions = [
            ("can_view_bajaequipo", "Can view baja equipo"),
            ("can_add_bajaequipo", "Can add baja equipo"),
            ("can_change_bajaequipo", "Can change baja equipo"),
            ("can_delete_bajaequipo", "Can delete baja equipo"),
        ]

    def __str__(self):
        return f"Baja de {self.equipo.nombre} ({self.equipo.codigo_interno}) el {self.fecha_baja.strftime('%d/%m/%Y')}"


# Modelo para Ubicación
class Ubicacion(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Ubicación"
        verbose_name_plural = "Ubicaciones"
        ordering = ['nombre']
        permissions = [
            ("can_view_ubicacion", "Can view ubicacion"),
            ("can_add_ubicacion", "Can add ubicacion"),
            ("can_change_ubicacion", "Can change ubicacion"),
            ("can_delete_ubicacion", "Can delete ubicacion"),
        ]

    def __str__(self):
        return self.nombre

# Modelo para Procedimiento
class Procedimiento(models.Model):
    nombre = models.CharField(max_length=200)
    codigo = models.CharField(max_length=50, unique=True)
    version = models.CharField(max_length=20, blank=True, null=True)
    fecha_emision = models.DateField(blank=True, null=True)
    documento_pdf = models.FileField(upload_to='procedimientos/', blank=True, null=True) # Renombrado para claridad

    class Meta:
        verbose_name = "Procedimiento"
        verbose_name_plural = "Procedimientos"
        ordering = ['nombre']
        permissions = [
            ("can_view_procedimiento", "Can view procedimiento"),
            ("can_add_procedimiento", "Can add procedimiento"),
            ("can_change_procedimiento", "Can change procedimiento"),
            ("can_delete_procedimiento", "Can delete procedimiento"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


# Modelo General de Proveedores
class Proveedor(models.Model):
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


# Los modelos ProveedorCalibracion, ProveedorMantenimiento, ProveedorComprobacion
# se han marcado para eliminación ya que el modelo Proveedor General los reemplaza
# y ya no son utilizados en las relaciones ForeignKey de Calibracion, Mantenimiento y Comprobacion
# que ahora usan un CharField 'nombre_proveedor'.
# Puedes eliminarlos o dejarlos si tienes datos históricos o un caso de uso que los justifique,
# pero para el flujo actual son redundantes.
# class ProveedorCalibracion(models.Model):
#     # ...
# class ProveedorMantenimiento(models.Model):
#     # ...
# class ProveedorComprobacion(models.Model):
#     # ...


# ==============================================================================
# SEÑALES DE DJANGO (AJUSTADO Y OPTIMIZADO)
# ==============================================================================

@receiver(post_save, sender=Calibracion)
def update_equipo_calibracion_info(sender, instance, **kwargs):
    equipo = instance.equipo
    latest_calibracion = Calibracion.objects.filter(equipo=equipo).order_by('-fecha_calibracion').first()

    if latest_calibracion:
        equipo.fecha_ultima_calibracion = latest_calibracion.fecha_calibracion
    else:
        equipo.fecha_ultima_calibracion = None
    
    # Recalcular las 3 próximas fechas. La lógica de 'De Baja' se maneja en los métodos del Equipo.
    equipo.calcular_proxima_calibracion()
    equipo.calcular_proximo_mantenimiento()
    equipo.calcular_proxima_comprobacion()
    
    equipo.save(update_fields=[
        'fecha_ultima_calibracion', 'proxima_calibracion',
        'proximo_mantenimiento', 'proxima_comprobacion', 'estado' # Incluir 'estado' si pudiera cambiar
    ])


@receiver(post_delete, sender=Calibracion)
def update_equipo_calibracion_info_on_delete(sender, instance, **kwargs):
    equipo = instance.equipo
    latest_calibracion = Calibracion.objects.filter(equipo=equipo).order_by('-fecha_calibracion').first()
    
    if latest_calibracion:
        equipo.fecha_ultima_calibracion = latest_calibracion.fecha_calibracion
    else:
        equipo.fecha_ultima_calibracion = None
    
    equipo.calcular_proxima_calibracion()
    equipo.calcular_proximo_mantenimiento()
    equipo.calcular_proxima_comprobacion()
        
    equipo.save(update_fields=[
        'fecha_ultima_calibracion', 'proxima_calibracion',
        'proximo_mantenimiento', 'proxima_comprobacion', 'estado'
    ])


@receiver(post_save, sender=Mantenimiento)
def update_equipo_mantenimiento_info(sender, instance, **kwargs):
    equipo = instance.equipo
    latest_mantenimiento = Mantenimiento.objects.filter(equipo=equipo).order_by('-fecha_mantenimiento').first()

    if latest_mantenimiento:
        equipo.fecha_ultimo_mantenimiento = latest_mantenimiento.fecha_mantenimiento
    else:
        equipo.fecha_ultimo_mantenimiento = None
    
    equipo.calcular_proximo_mantenimiento()
    equipo.calcular_proxima_calibracion() # Recalcular también otras fechas
    equipo.calcular_proxima_comprobacion()
        
    equipo.save(update_fields=[
        'fecha_ultimo_mantenimiento', 'proximo_mantenimiento',
        'proxima_calibracion', 'proxima_comprobacion', 'estado'
    ])


@receiver(post_delete, sender=Mantenimiento)
def update_equipo_mantenimiento_info_on_delete(sender, instance, **kwargs):
    equipo = instance.equipo
    latest_mantenimiento = Mantenimiento.objects.filter(equipo=equipo).order_by('-fecha_mantenimiento').first()

    if latest_mantenimiento:
        equipo.fecha_ultimo_mantenimiento = latest_mantenimiento.fecha_mantenimiento
    else:
        equipo.fecha_ultimo_mantenimiento = None
    
    equipo.calcular_proximo_mantenimiento()
    equipo.calcular_proxima_calibracion()
    equipo.calcular_proxima_comprobacion()
        
    equipo.save(update_fields=[
        'fecha_ultimo_mantenimiento', 'proximo_mantenimiento',
        'proxima_calibracion', 'proxima_comprobacion', 'estado'
    ])


@receiver(post_save, sender=Comprobacion)
def update_equipo_comprobacion_info(sender, instance, **kwargs):
    equipo = instance.equipo
    latest_comprobacion = Comprobacion.objects.filter(equipo=equipo).order_by('-fecha_comprobacion').first()

    if latest_comprobacion:
        equipo.fecha_ultima_comprobacion = latest_comprobacion.fecha_comprobacion
    else:
        equipo.fecha_ultima_comprobacion = None
    
    equipo.calcular_proxima_comprobacion()
    equipo.calcular_proxima_calibracion()
    equipo.calcular_proximo_mantenimiento()
        
    equipo.save(update_fields=[
        'fecha_ultima_comprobacion', 'proxima_comprobacion',
        'proxima_calibracion', 'proximo_mantenimiento', 'estado'
    ])


@receiver(post_delete, sender=Comprobacion)
def update_equipo_comprobacion_info_on_delete(sender, instance, **kwargs):
    equipo = instance.equipo
    latest_comprobacion = Comprobacion.objects.filter(equipo=equipo).order_by('-fecha_comprobacion').first()

    if latest_comprobacion:
        equipo.fecha_ultima_comprobacion = latest_comprobacion.fecha_comprobacion
    else:
        equipo.fecha_ultima_comprobacion = None
    
    equipo.calcular_proxima_comprobacion()
    equipo.calcular_proxima_calibracion()
    equipo.calcular_proximo_mantenimiento()
        
    equipo.save(update_fields=[
        'fecha_ultima_comprobacion', 'proxima_comprobacion',
        'proxima_calibracion', 'proximo_mantenimiento', 'estado'
    ])

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

