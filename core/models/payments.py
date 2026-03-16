# core/models/payments.py
# Modelos: TerminosYCondiciones, AceptacionTerminos, TransaccionPago, LinkPago

from django.db import models
from django.conf import settings
from django.utils import timezone
import logging
from .empresa import Empresa

logger = logging.getLogger('core')


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


class TransaccionPago(models.Model):
    """
    Registra cada intento de pago realizado por una empresa.
    Soporta PSE y tarjeta a través de la pasarela Wompi.
    La referencia_pago es única y se usa como identificador contra Wompi.
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('error', 'Error'),
    ]
    METODO_CHOICES = [
        ('PSE', 'PSE'),
        ('tarjeta', 'Tarjeta de Crédito/Débito'),
        ('efectivo', 'Efectivo'),
    ]
    PLAN_CHOICES = [
        # Estándar (200 equipos) — backward compat con transacciones existentes
        ('MENSUAL', 'Plan Estándar Mensual'),
        ('ANUAL', 'Plan Estándar Anual'),
        # Básico (50 equipos)
        ('BASICO_MENSUAL', 'Plan Básico Mensual'),
        ('BASICO_ANUAL', 'Plan Básico Anual'),
        # Profesional (500 equipos)
        ('PRO_MENSUAL', 'Plan Profesional Mensual'),
        ('PRO_ANUAL', 'Plan Profesional Anual'),
        # Empresarial (1000 equipos)
        ('ENTERPRISE_MENSUAL', 'Plan Empresarial Mensual'),
        ('ENTERPRISE_ANUAL', 'Plan Empresarial Anual'),
        # Add-ons modulares
        ('ADDON', 'Add-ons'),
    ]

    empresa = models.ForeignKey(
        'Empresa', on_delete=models.CASCADE,
        related_name='transacciones_pago',
        verbose_name='Empresa'
    )
    referencia_pago = models.CharField(
        max_length=100, unique=True,
        verbose_name='Referencia de Pago',
        help_text='ID único de la transacción (enviado a Wompi como reference)'
    )
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default='pendiente',
        verbose_name='Estado'
    )
    monto = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name='Monto',
        help_text='Valor total incluyendo IVA, en COP'
    )
    moneda = models.CharField(max_length=3, default='COP', verbose_name='Moneda')
    metodo_pago = models.CharField(
        max_length=20, choices=METODO_CHOICES, blank=True,
        verbose_name='Método de Pago'
    )
    plan_seleccionado = models.CharField(
        max_length=20, choices=PLAN_CHOICES, blank=True,
        verbose_name='Plan Seleccionado',
        help_text="Vacío solo para transacciones de tipo add-on cuando se usa el campo datos_addon"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última Actualización')
    datos_respuesta = models.JSONField(
        null=True, blank=True,
        verbose_name='Datos de Respuesta',
        help_text='Respuesta completa de Wompi (para auditoría)'
    )
    datos_addon = models.JSONField(
        null=True, blank=True,
        verbose_name='Detalle de Add-ons',
        help_text='Cantidades de add-ons comprados: {tecnicos, admins, gerentes, bloques_equipos, bloques_storage}'
    )
    ip_cliente = models.GenericIPAddressField(
        null=True, blank=True,
        verbose_name='IP del Cliente'
    )

    class Meta:
        verbose_name = 'Transacción de Pago'
        verbose_name_plural = 'Transacciones de Pago'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.empresa.nombre} | {self.referencia_pago} | {self.estado}"

    @property
    def monto_en_centavos(self):
        """Retorna el monto en centavos (requerido por Wompi)."""
        return int(self.monto * 100)

    def esta_aprobada(self):
        return self.estado == 'aprobado'


class LinkPago(models.Model):
    """
    Link de pago único que permite a contabilidad pagar sin iniciar sesión.
    Generado por admin/gerente desde el modal de renovación del dashboard.
    Expira en 7 días si no se usa.
    """
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('expirado', 'Expirado'),
    ]

    empresa = models.ForeignKey(
        'Empresa', on_delete=models.CASCADE,
        related_name='links_pago', verbose_name="Empresa"
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    plan_seleccionado = models.CharField(max_length=40, blank=True, null=True,
        verbose_name="Plan seleccionado")
    addons = models.JSONField(default=dict, blank=True,
        verbose_name="Add-ons",
        help_text="{tecnicos, admins, gerentes, bloques_equipos, bloques_storage}")
    monto_total = models.DecimalField(max_digits=12, decimal_places=2,
        verbose_name="Monto total (IVA incl.)")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField()
    transaccion = models.OneToOneField(
        'TransaccionPago', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='link_pago'
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='links_pago_creados'
    )

    class Meta:
        verbose_name = "Link de Pago"
        verbose_name_plural = "Links de Pago"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"LinkPago {self.token[:8]}… — {self.empresa.nombre}"

    def esta_vigente(self):
        from django.utils import timezone
        return self.estado == 'pendiente' and self.fecha_expiracion > timezone.now()
