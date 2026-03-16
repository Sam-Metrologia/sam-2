# core/models/users.py
# Modelos: CustomUser, OnboardingProgress

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from .empresa import Empresa


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
    def puede_eliminar_equipos(self):
        """
        Verifica si el usuario puede eliminar equipos.
        TÉCNICO: NO
        ADMINISTRADOR: SÍ
        GERENTE: SÍ
        SUPERUSER: SÍ
        """
        if self.is_superuser:
            return True
        return self.rol_usuario in ['ADMINISTRADOR', 'GERENCIA']

    @property
    def has_export_permission(self):
        """
        Verifica si el usuario tiene permiso para exportar informes.
        Usa el nuevo sistema de roles.
        """
        return self.puede_descargar_informes()


class OnboardingProgress(models.Model):
    """Progreso del onboarding para usuarios de empresas trial."""
    usuario = models.OneToOneField(
        'CustomUser', on_delete=models.CASCADE,
        related_name='onboarding_progress'
    )
    # Tour guiado (Shepherd.js)
    tour_completado = models.BooleanField(default=False)
    # Pasos del checklist
    paso_crear_equipo = models.BooleanField(default=False)
    paso_registrar_calibracion = models.BooleanField(default=False)
    paso_generar_reporte = models.BooleanField(default=False)
    # Timestamps
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_completado = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Progreso de Onboarding'
        verbose_name_plural = 'Progresos de Onboarding'

    def __str__(self):
        pasos = self.pasos_completados
        return f"Onboarding {self.usuario.username}: {pasos}/3"

    @property
    def pasos_completados(self):
        return sum([
            self.paso_crear_equipo,
            self.paso_registrar_calibracion,
            self.paso_generar_reporte,
        ])

    @property
    def total_pasos(self):
        return 3

    @property
    def porcentaje(self):
        return int((self.pasos_completados / self.total_pasos) * 100)

    @property
    def completado(self):
        return self.pasos_completados == self.total_pasos

    def marcar_paso(self, nombre_paso):
        """Marca un paso como completado si existe y no estaba marcado."""
        campo = f'paso_{nombre_paso}'
        if hasattr(self, campo) and not getattr(self, campo):
            setattr(self, campo, True)
            if self.completado and not self.fecha_completado:
                self.fecha_completado = timezone.now()
            self.save(update_fields=[campo, 'fecha_completado'])
            return True
        return False
