# core/models.py
# Ajustado para la lógica de la primera programación de mantenimiento y comprobación

from django.db import models
from django.contrib.auth.models import AbstractUser
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


# Función para la ruta de subida de archivos
def get_upload_path(instance, filename):
    """Define la ruta de subida para los archivos de equipo y sus actividades."""
    base_code = None
    if isinstance(instance, Equipo):
        base_code = instance.codigo_interno
    elif hasattr(instance, 'equipo') and hasattr(instance.equipo, 'codigo_interno'):
        base_code = instance.equipo.codigo_interno
    
    if not base_code:
        # Si no se puede determinar el código, usar un nombre genérico o lanzar un error
        # Considera si quieres que esto sea un error fatal o una ruta por defecto.
        # Por ahora, lanzamos un error para que se corrija el origen del problema.
        raise AttributeError(f"No se pudo determinar el código interno del equipo para la instancia de tipo {type(instance).__name__}. Asegúrese de que el equipo tiene un código interno definido.")

    # Convertir el código a un formato seguro para el nombre de archivo
    safe_base_code = base_code.replace('/', '_').replace('\\', '_')

    # Construir la ruta base dentro de MEDIA_ROOT
    base_path = f"equipos/{safe_base_code}/" # Usar safe_base_code aquí

    # Determinar subcarpeta específica para el tipo de documento
    if isinstance(instance, Calibracion):
        # Para archivos de calibración, diferenciar entre certificado, confirmación e intervalos
        if 'confirmacion' in filename.lower():
            subfolder = "calibraciones/confirmaciones/"
        elif 'intervalos' in filename.lower(): # Nueva subcarpeta para intervalos
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
        if 'compra' in filename.lower(): # Simple heurística, puedes refinarla
            subfolder = "documentos_equipos/compra/"
        elif 'ficha_tecnica' in filename.lower() or 'ficha-tecnica' in filename.lower():
            subfolder = "documentos_equipos/ficha_tecnica/"
        elif 'manual' in filename.lower():
            subfolder = "documentos_equipos/manuales/"
        elif filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')): # Para la imagen del equipo
            subfolder = "imagenes_equipos/"
        else: # Otros documentos del equipo
            subfolder = "documentos_equipos/otros/"
    else:
        subfolder = "" # Carpeta por defecto si no se reconoce el tipo

    return os.path.join(base_path, subfolder, filename)


def get_empresa_logo_upload_path(instance, filename):
    """Define la ruta de subida para el logo de la empresa."""
    # Asegura que el nombre de la empresa sea seguro para la ruta del archivo
    safe_company_name = instance.nombre.replace(' ', '_').lower()
    return os.path.join(f"empresas/{safe_company_name}/", filename)


class Empresa(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
    nit = models.CharField(max_length=50, unique=True, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    # Nuevo campo para el logo de la empresa
    logo_empresa = models.ImageField(upload_to=get_empresa_logo_upload_path, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True) # Añadido para consistencia
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
    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True, related_name='usuarios')
    # Puedes añadir más campos específicos para tu usuario aquí si es necesario

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        permissions = [
            ("can_view_customuser", "Can view custom user"), # Corregido a singular para consistencia
            ("can_add_customuser", "Can add custom user"),
            ("can_change_customuser", "Can change custom user"),
            ("can_delete_customuser", "Can delete custom user"),
        ]

    def __str__(self):
        return self.username


class Ubicacion(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Ubicación"
        verbose_name_plural = "Ubicaciones" # ¡CORREGIDO AQUÍ!
        ordering = ['nombre']
        permissions = [ # Añadidos permisos para Ubicacion
            ("can_view_ubicacion", "Can view ubicacion"),
            ("can_add_ubicacion", "Can add ubicacion"),
            ("can_change_ubicacion", "Can change ubicacion"),
            ("can_delete_ubicacion", "Can delete ubicacion"),
        ]

    def __str__(self):
        return self.nombre

class Procedimiento(models.Model):
    nombre = models.CharField(max_length=200) # Ya no unique=True
    codigo = models.CharField(max_length=50, unique=True) # Este sí debe ser único
    version = models.CharField(max_length=20, blank=True, null=True)
    fecha_emision = models.DateField(blank=True, null=True)
    documento_pdf = models.FileField(upload_to='procedimientos/', blank=True, null=True) # Renombrado para claridad
    # observaciones = models.TextField(blank=True, null=True) # Eliminado, no estaba en el forms ni admin

    class Meta:
        verbose_name = "Procedimiento"
        verbose_name_plural = "Procedimientos"
        ordering = ['nombre']
        permissions = [ # Añadidos permisos para Procedimiento
            ("can_view_procedimiento", "Can view procedimiento"),
            ("can_add_procedimiento", "Can add procedimiento"),
            ("can_change_procedimiento", "Can change procedimiento"),
            ("can_delete_procedimiento", "Can delete procedimiento"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


# Proveedores (se mantienen, pero Calibracion ya no usará ProveedorCalibracion)
class ProveedorCalibracion(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
    contacto = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True) # Añadido para consistencia

    class Meta:
        verbose_name = "Proveedor de Calibración"
        verbose_name_plural = "Proveedores de Calibración"
        ordering = ['nombre']
        permissions = [ # Añadidos permisos para ProveedorCalibracion
            ("can_view_proveedorcalibracion", "Can view proveedor calibracion"),
            ("can_add_proveedorcalibracion", "Can add proveedor calibracion"),
            ("can_change_proveedorcalibracion", "Can change proveedor calibracion"),
            ("can_delete_proveedorcalibracion", "Can delete proveedor calibracion"),
        ]

    def __str__(self):
        return self.nombre

class ProveedorMantenimiento(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
    contacto = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True) # Añadido para consistencia

    class Meta:
        verbose_name = "Proveedor de Mantenimiento"
        verbose_name_plural = "Proveedores de Mantenimiento"
        ordering = ['nombre']
        permissions = [ # Añadidos permisos para ProveedorMantenimiento
            ("can_view_proveedormantenimiento", "Can view proveedor mantenimiento"),
            ("can_add_proveedormantenimiento", "Can add proveedor mantenimiento"),
            ("can_change_proveedormantenimiento", "Can change proveedor mantenimiento"),
            ("can_delete_proveedormantenimiento", "Can delete proveedor mantenimiento"),
        ]

    def __str__(self):
        return self.nombre

class ProveedorComprobacion(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
    contacto = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True) # Añadido para consistencia

    class Meta:
        verbose_name = "Proveedor de Comprobación"
        verbose_name_plural = "Proveedores de Comprobación"
        ordering = ['nombre']
        permissions = [ # Añadidos permisos para ProveedorComprobacion
            ("can_view_proveedorcomprobacion", "Can view proveedor comprobacion"),
            ("can_add_proveedorcomprobacion", "Can add proveedor comprobacion"),
            ("can_change_proveedorcomprobacion", "Can change proveedor comprobacion"),
            ("can_delete_proveedorcomprobacion", "Can delete proveedor comprobacion"),
        ]

    def __str__(self):
        return self.nombre

# NUEVO MODELO: Proveedor General
class Proveedor(models.Model):
    TIPO_SERVICIO_CHOICES = [
        ('Calibración', 'Calibración'),
        ('Mantenimiento', 'Mantenimiento'),
        ('Comprobación', 'Comprobación'),
        ('Compra', 'Compra'),
        ('Otro', 'Otro'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='proveedores', verbose_name="Empresa") # Nuevo campo
    tipo_servicio = models.CharField(max_length=50, choices=TIPO_SERVICIO_CHOICES, verbose_name="Tipo de Servicio")
    nombre_contacto = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nombre de Contacto")
    numero_contacto = models.CharField(max_length=20, blank=True, null=True, verbose_name="Número de Contacto")
    nombre_empresa = models.CharField(max_length=200, verbose_name="Nombre de la Empresa") # Ya no unique=True
    correo_electronico = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
    pagina_web = models.URLField(blank=True, null=True, verbose_name="Página Web")
    alcance = models.TextField(blank=True, null=True, verbose_name="Alcance (áreas o magnitudes)")
    servicio_prestado = models.TextField(blank=True, null=True, verbose_name="Servicio Prestado")

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['nombre_empresa']
        # Añadir unique_together para asegurar que la combinación nombre_empresa y empresa sea única
        unique_together = ('nombre_empresa', 'empresa',)
        permissions = [
            ("can_view_proveedor", "Can view proveedor"),
            ("can_add_proveedor", "Can add proveedor"),
            ("can_change_proveedor", "Can change proveedor"),
            ("can_delete_proveedor", "Can delete proveedor"),
        ]

    def __str__(self):
        return f"{self.nombre_empresa} ({self.tipo_servicio}) - {self.empresa.nombre}"


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
    # CAMBIO AQUÍ: Ubicación ahora es CharField
    ubicacion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ubicación")
    responsable = models.CharField(max_length=100, blank=True, null=True, verbose_name="Responsable")
    estado = models.CharField(max_length=50, choices=ESTADO_CHOICES, default='Activo', verbose_name="Estado")
    fecha_adquisicion = models.DateField(blank=True, null=True, verbose_name="Fecha de Adquisición")
    rango_medida = models.CharField(max_length=100, blank=True, null=True, verbose_name="Rango de Medida")
    resolucion = models.CharField(max_length=100, blank=True, null=True, verbose_name="Resolución")
    # CAMBIO AQUÍ: Error Máximo Permisible ahora es CharField
    error_maximo_permisible = models.CharField(max_length=100, blank=True, null=True, verbose_name="Error Máximo Permisible")
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

    # Campos para fechas de próximas actividades y frecuencias
    fecha_ultima_calibracion = models.DateField(blank=True, null=True, verbose_name="Fecha Última Calibración")
    proxima_calibracion = models.DateField(blank=True, null=True, verbose_name="Próxima Calibración")
    # Frecuencia ahora solo aquí
    frecuencia_calibracion_meses = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Frecuencia Calibración (meses)")

    fecha_ultimo_mantenimiento = models.DateField(blank=True, null=True, verbose_name="Fecha Último Mantenimiento")
    proximo_mantenimiento = models.DateField(blank=True, null=True, verbose_name="Próximo Mantenimiento")
    # Frecuencia ahora solo aquí
    frecuencia_mantenimiento_meses = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Frecuencia Mantenimiento (meses)")

    fecha_ultima_comprobacion = models.DateField(blank=True, null=True, verbose_name="Fecha Última Comprobación")
    proxima_comprobacion = models.DateField(blank=True, null=True, verbose_name="Próxima Comprobación")
    # Frecuencia ahora solo aquí
    frecuencia_comprobacion_meses = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name="Frecuencia Comprobación (meses)")

    class Meta:
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"
        ordering = ['codigo_interno']
        permissions = [
            ("can_view_equipo", "Can view equipo"),
            ("can_add_equipo", "Can add equipo"),
            ("can_change_equipo", "Can change equipo"),
            ("can_delete_equipo", "Can delete equipo"), # Este permiso se mantiene para superusuarios
            ("can_export_reports", "Can export reports (PDF, Excel, ZIP)"), # NUEVO PERMISO
        ]

    def __str__(self):
        return f"{self.nombre} ({self.codigo_interno})"

    # Métodos para calcular próximas fechas
    def calcular_proxima_calibracion(self):
        # Si el equipo está de baja, no calcular próximas fechas
        if self.estado == 'De Baja':
            self.proxima_calibracion = None
            return

        base_date = self.fecha_ultima_calibracion
        if not base_date and self.fecha_adquisicion: # Si no hay última calibración, usar fecha de adquisición
            base_date = self.fecha_adquisicion

        frequency = self.frecuencia_calibracion_meses
        
        if base_date and frequency is not None and frequency > 0:
            # Usamos un promedio de 30.4375 días por mes (365.25 / 12) para mayor precisión
            total_days = int(round(frequency * decimal.Decimal('30.4375')))
            self.proxima_calibracion = base_date + timedelta(days=total_days)
        else:
            self.proxima_calibracion = None

    def calcular_proximo_mantenimiento(self):
        # Si el equipo está de baja, no calcular próximas fechas
        if self.estado == 'De Baja':
            self.proximo_mantenimiento = None
            return

        base_date = self.fecha_ultimo_mantenimiento
        if not base_date: # Si no hay último mantenimiento registrado
            # La primera programación se basa en la fecha de última calibración o adquisición
            if self.fecha_ultima_calibracion:
                base_date = self.fecha_ultima_calibracion
            elif self.fecha_adquisicion:
                base_date = self.fecha_adquisicion
            
            # Si tenemos una fecha base y una frecuencia, calculamos la primera fecha programada
            if base_date and self.frecuencia_mantenimiento_meses is not None and self.frecuencia_mantenimiento_meses > 0:
                total_days = int(round(self.frecuencia_mantenimiento_meses * decimal.Decimal('30.4375')))
                self.proximo_mantenimiento = base_date + timedelta(days=total_days)
            else:
                self.proximo_mantenimiento = None
        else: # Si ya hay un mantenimiento registrado, la próxima fecha se basa en el último
            frequency = self.frecuencia_mantenimiento_meses
            if base_date and frequency is not None and frequency > 0:
                total_days = int(round(frequency * decimal.Decimal('30.4375')))
                self.proximo_mantenimiento = base_date + timedelta(days=total_days)
            else:
                self.proximo_mantenimiento = None


    def calcular_proxima_comprobacion(self):
        # Si el equipo está de baja, no calcular próximas fechas
        if self.estado == 'De Baja':
            self.proxima_comprobacion = None
            return

        base_date = self.fecha_ultima_comprobacion
        if not base_date: # Si no hay última comprobación registrada
            # La primera programación se basa en la fecha de última calibración o adquisición
            if self.fecha_ultima_calibracion:
                base_date = self.fecha_ultima_calibracion
            elif self.fecha_adquisicion:
                base_date = self.fecha_adquisicion

            # Si tenemos una fecha base y una frecuencia, calculamos la primera fecha programada
            if base_date and self.frecuencia_comprobacion_meses is not None and self.frecuencia_comprobacion_meses > 0:
                total_days = int(round(self.frecuencia_comprobacion_meses * decimal.Decimal('30.4375')))
                self.proxima_comprobacion = base_date + timedelta(days=total_days)
            else:
                self.proxima_comprobacion = None
        else: # Si ya hay una comprobación registrada, la próxima fecha se basa en la última
            frequency = self.frecuencia_comprobacion_meses
            if base_date and frequency is not None and frequency > 0:
                total_days = int(round(frequency * decimal.Decimal('30.4375')))
                self.proxima_comprobacion = base_date + timedelta(days=total_days)
            else:
                self.proxima_comprobacion = None

    def save(self, *args, **kwargs):
        # Recalcular las fechas próximas antes de guardar el Equipo
        # Esto se hace aquí para que los campos proxima_X se actualicen
        # antes de que las señales post_save de Calibracion/Mantenimiento/Comprobacion
        # intenten leerlos o si el equipo se guarda directamente.
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
    # Mantengo CharField para flexibilidad, pero podría ser ForeignKey a Proveedor si se desea un control estricto
    nombre_proveedor = models.CharField(max_length=200, verbose_name="Nombre del Proveedor de Calibración", blank=True, null=True)
    resultado = models.CharField(max_length=10, choices=RESULTADO_CHOICES, verbose_name="Resultado", default='Cumple')
    numero_certificado = models.CharField(max_length=100, blank=True, null=True, verbose_name="Número de Certificado")
    documento_calibracion = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Certificado de Calibración (PDF)")
    confirmacion_metrologica_pdf = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Confirmación Metrológica (PDF)")
    intervalos_calibracion_pdf = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Intervalos de Calibración (PDF)") # NUEVO CAMPO
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    # Frecuencia eliminada de aquí

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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs) # Guarda la instancia de Calibracion primero
        # La actualización del Equipo se hace en la señal para asegurar la última calibración
        pass


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
    # Mantengo CharField para flexibilidad
    nombre_proveedor = models.CharField(max_length=200, verbose_name="Nombre del Proveedor de Mantenimiento", blank=True, null=True)
    responsable = models.CharField(max_length=100, blank=True, null=True, verbose_name="Responsable del Mantenimiento")
    tipo_mantenimiento = models.CharField(max_length=50, choices=TIPO_MANTENIMIENTO_CHOICES, verbose_name="Tipo de Mantenimiento")
    costo = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Costo")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción del Trabajo")
    documento_mantenimiento = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Documento de Mantenimiento (PDF)")
    # Frecuencia eliminada de aquí

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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        pass # La señal post_save se encargará de esto


# Modelo para Comprobación
class Comprobacion(models.Model):
    RESULTADO_CHOICES = [
        ('Aprobado', 'Aprobado'),
        ('Rechazado', 'Rechazado'),
    ]

    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='comprobaciones', verbose_name="Equipo")
    fecha_comprobacion = models.DateField(verbose_name="Fecha de Comprobación")
    # Mantengo CharField para flexibilidad
    nombre_proveedor = models.CharField(max_length=200, verbose_name="Nombre del Proveedor de Comprobación", blank=True, null=True)
    responsable = models.CharField(max_length=100, blank=True, null=True, verbose_name="Responsable de la Comprobación")
    resultado = models.CharField(max_length=10, choices=RESULTADO_CHOICES, verbose_name="Resultado")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    documento_comprobacion = models.FileField(upload_to=get_upload_path, blank=True, null=True, verbose_name="Documento de Comprobación (PDF)")
    # Frecuencia eliminada de aquí

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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        pass # La señal post_save se encargará de esto


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

@receiver(post_save, sender=BajaEquipo)
def set_equipo_de_baja(sender, instance, created, **kwargs):
    if created:
        equipo = instance.equipo
        equipo.estado = 'De Baja'
        equipo.save(update_fields=['estado'])

@receiver(post_delete, sender=BajaEquipo)
def set_equipo_activo_on_delete_baja(sender, instance, **kwargs):
    equipo = instance.equipo
    # Solo cambiar a 'Activo' si no hay otros registros de baja para el mismo equipo
    if not BajaEquipo.objects.filter(equipo=equipo).exists():
        equipo.estado = 'Activo' # O el estado por defecto que desees
        equipo.save(update_fields=['estado'])


# --- SEÑALES PARA ACTUALIZAR FECHAS EN EL MODELO EQUIPO ---

@receiver(post_save, sender=Calibracion)
def update_equipo_calibracion_info(sender, instance, **kwargs):
    equipo = instance.equipo
    # Encontrar la calibración más reciente para este equipo
    latest_calibracion = Calibracion.objects.filter(equipo=equipo).order_by('-fecha_calibracion').first()

    if latest_calibracion:
        equipo.fecha_ultima_calibracion = latest_calibracion.fecha_calibracion
    else:
        # Si no hay calibraciones, resetear los campos
        equipo.fecha_ultima_calibracion = None
    
    # Recalcular proxima_calibracion explícitamente antes de guardar
    # Solo recalcular si el equipo NO está de baja
    if equipo.estado != 'De Baja':
        equipo.calcular_proxima_calibracion()
        # ¡IMPORTANTE! Recalcular mantenimiento y comprobacion aquí también
        equipo.calcular_proximo_mantenimiento()
        equipo.calcular_proxima_comprobacion()
    else:
        equipo.proxima_calibracion = None # Asegurar que se ponga a None si está de baja
        equipo.proximo_mantenimiento = None # También establecer a None si el equipo está de baja
        equipo.proxima_comprobacion = None # También establecer a None si el equipo está de baja
    
    # Guardar el equipo, incluyendo proxima_calibracion, proximo_mantenimiento y proxima_comprobacion en update_fields
    # Esto asegura que el valor calculado se persista en la DB
    equipo.save(update_fields=[
        'fecha_ultima_calibracion', 'proxima_calibracion',
        'proximo_mantenimiento', 'proxima_comprobacion'
    ])


@receiver(post_delete, sender=Calibracion)
def update_equipo_calibracion_info_on_delete(sender, instance, **kwargs):
    equipo = instance.equipo
    # Encontrar la calibración más reciente después de la eliminación
    latest_calibracion = Calibracion.objects.filter(equipo=equipo).order_by('-fecha_calibracion').first()

    if latest_calibracion:
        equipo.fecha_ultima_calibracion = latest_calibracion.fecha_calibracion
    else:
        # Si no quedan calibraciones, resetear los campos
        equipo.fecha_ultima_calibracion = None
    
    # Recalcular proxima_calibracion explícitamente antes de guardar
    # Solo recalcular si el equipo NO está de baja
    if equipo.estado != 'De Baja':
        equipo.calcular_proxima_calibracion()
        # ¡IMPORTANTE! Recalcular mantenimiento y comprobacion aquí también
        equipo.calcular_proximo_mantenimiento()
        equipo.calcular_proxima_comprobacion()
    else:
        equipo.proxima_calibracion = None # Asegurar que se ponga a None si está de baja
        equipo.proximo_mantenimiento = None # También establecer a None si el equipo está de baja
        equipo.proxima_comprobacion = None # También establecer a None si el equipo está de baja
    
    equipo.save(update_fields=[
        'fecha_ultima_calibracion', 'proxima_calibracion',
        'proximo_mantenimiento', 'proxima_comprobacion'
    ])


@receiver(post_save, sender=Mantenimiento)
def update_equipo_mantenimiento_info(sender, instance, **kwargs):
    equipo = instance.equipo
    latest_mantenimiento = Mantenimiento.objects.filter(equipo=equipo).order_by('-fecha_mantenimiento').first()

    if latest_mantenimiento:
        equipo.fecha_ultimo_mantenimiento = latest_mantenimiento.fecha_mantenimiento
    else:
        equipo.fecha_ultimo_mantenimiento = None
    
    if equipo.estado != 'De Baja':
        equipo.calcular_proximo_mantenimiento() # Recalcular antes de guardar
    else:
        equipo.proximo_mantenimiento = None

    equipo.save(update_fields=['fecha_ultimo_mantenimiento', 'proximo_mantenimiento'])

@receiver(post_delete, sender=Mantenimiento)
def update_equipo_mantenimiento_info_on_delete(sender, instance, **kwargs):
    equipo = instance.equipo
    latest_mantenimiento = Mantenimiento.objects.filter(equipo=equipo).order_by('-fecha_mantenimiento').first()

    if latest_mantenimiento:
        equipo.fecha_ultimo_mantenimiento = latest_mantenimiento.fecha_mantenimiento
    else:
        equipo.fecha_ultimo_mantenimiento = None
    
    if equipo.estado != 'De Baja':
        equipo.calcular_proximo_mantenimiento() # Recalcular antes de guardar
    else:
        equipo.proximo_mantenimiento = None

    equipo.save(update_fields=['fecha_ultimo_mantenimiento', 'proximo_mantenimiento'])


@receiver(post_save, sender=Comprobacion)
def update_equipo_comprobacion_info(sender, instance, **kwargs):
    equipo = instance.equipo
    latest_comprobacion = Comprobacion.objects.filter(equipo=equipo).order_by('-fecha_comprobacion').first()

    if latest_comprobacion:
        equipo.fecha_ultima_comprobacion = latest_comprobacion.fecha_comprobacion
    else:
        equipo.fecha_ultima_comprobacion = None
    
    if equipo.estado != 'De Baja':
        equipo.calcular_proxima_comprobacion() # Recalcular antes de guardar
    else:
        equipo.proxima_comprobacion = None

    equipo.save(update_fields=['fecha_ultima_comprobacion', 'proxima_comprobacion'])

@receiver(post_delete, sender=Comprobacion)
def update_equipo_comprobacion_info_on_delete(sender, instance, **kwargs):
    equipo = instance.equipo
    latest_comprobacion = Comprobacion.objects.filter(equipo=equipo).order_by('-fecha_comprobacion').first()

    if latest_comprobacion:
        equipo.fecha_ultima_comprobacion = latest_comprobacion.fecha_comprobacion
    else:
        equipo.fecha_ultima_comprobacion = None
    
    if equipo.estado != 'De Baja':
        equipo.calcular_proxima_comprobacion() # Recalcular antes de guardar
    else:
        equipo.proxima_comprobacion = None

    equipo.save(update_fields=['fecha_ultima_comprobacion', 'proxima_comprobacion'])
