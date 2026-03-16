# core/models/system.py
# Modelos: EmailConfiguration, SystemScheduleConfig, MetricasEficienciaMetrologica,
#           MaintenanceTask, CommandLog, SystemHealthCheck

from django.db import models
from django.utils import timezone
import logging
from .empresa import Empresa
from .users import CustomUser

logger = logging.getLogger('core')


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
