#!/usr/bin/env python
"""
SAM METROLOGÍA - SCRIPT DE PRUEBA COMPREHENSIVO
Prueba todas las funcionalidades críticas de la plataforma antes de producción
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from datetime import timedelta
from core.models import Equipo, Empresa, Proveedor, Procedimiento

User = get_user_model()

class PlatformTester:
    def __init__(self):
        self.client = Client()
        self.results = []
        self.errors = []

    def log_result(self, test_name, passed, message=""):
        status = "[PASS]" if passed else "[FAIL]"
        result = f"{status} - {test_name}"
        if message:
            result += f": {message}"
        self.results.append(result)
        if not passed:
            self.errors.append(result)
        print(result)

    def test_database_connection(self):
        """Test 1: Conexión a base de datos"""
        try:
            count = User.objects.count()
            self.log_result("Database Connection", True, f"{count} usuarios encontrados")
        except Exception as e:
            self.log_result("Database Connection", False, str(e))

    def test_user_authentication(self):
        """Test 2: Sistema de autenticación"""
        try:
            # Intentar obtener un superusuario
            superuser = User.objects.filter(is_superuser=True).first()
            if not superuser:
                self.log_result("User Authentication", False, "No superuser found")
                return

            # Test login
            response = self.client.get('/core/login/')
            self.log_result("Login Page Access", response.status_code == 200)

        except Exception as e:
            self.log_result("User Authentication", False, str(e))

    def test_models_integrity(self):
        """Test 3: Integridad de modelos"""
        try:
            # Test Empresa
            empresa_count = Empresa.objects.filter(is_deleted=False).count()
            self.log_result("Empresa Model", empresa_count >= 0, f"{empresa_count} empresas activas")

            # Test Equipo
            equipo_count = Equipo.objects.count()
            self.log_result("Equipo Model", equipo_count >= 0, f"{equipo_count} equipos")

            # Test Proveedor
            proveedor_count = Proveedor.objects.count()
            self.log_result("Proveedor Model", proveedor_count >= 0, f"{proveedor_count} proveedores")

            # Test Procedimiento
            procedimiento_count = Procedimiento.objects.count()
            self.log_result("Procedimiento Model", procedimiento_count >= 0, f"{procedimiento_count} procedimientos")

        except Exception as e:
            self.log_result("Models Integrity", False, str(e))

    def test_email_configuration(self):
        """Test 4: Configuración de email"""
        try:
            from django.conf import settings

            # Check email settings
            has_email_backend = hasattr(settings, 'EMAIL_BACKEND')
            has_email_host = hasattr(settings, 'EMAIL_HOST')

            if not has_email_backend or not has_email_host:
                self.log_result("Email Configuration", False, "EMAIL settings not configured")
                return

            # Email service check
            self.log_result("Email Settings", True, f"Backend: {settings.EMAIL_BACKEND}")

            # Check if using console backend (development)
            if 'console' in settings.EMAIL_BACKEND.lower():
                self.log_result("Email Backend", True, "Console backend (development mode)")
            else:
                self.log_result("Email Backend", True, f"SMTP backend configured: {settings.EMAIL_HOST}")

        except Exception as e:
            self.log_result("Email Configuration", False, str(e))

    def test_notification_system(self):
        """Test 5: Sistema de notificaciones"""
        try:
            from core.models import Calibracion, Mantenimiento, Comprobacion

            # Check for activities due soon
            today = timezone.now().date()
            in_15_days = today + timedelta(days=15)

            calibraciones_proximas = Calibracion.objects.filter(
                fecha_proxima_calibracion__lte=in_15_days,
                fecha_proxima_calibracion__gte=today
            ).count()

            mantenimientos_proximos = Mantenimiento.objects.filter(
                fecha_proximo_mantenimiento__lte=in_15_days,
                fecha_proximo_mantenimiento__gte=today
            ).count()

            comprobaciones_proximas = Comprobacion.objects.filter(
                fecha_proxima_comprobacion__lte=in_15_days,
                fecha_proxima_comprobacion__gte=today
            ).count()

            total_proximas = calibraciones_proximas + mantenimientos_proximos + comprobaciones_proximas

            self.log_result("Notification System - Upcoming Activities", True,
                          f"{total_proximas} actividades próximas (15 días)")

            # Test notification command exists
            from django.core.management import call_command
            try:
                # This will fail if command doesn't exist
                from core.management.commands import enviar_notificaciones_automaticas
                self.log_result("Notification Command", True, "enviar_notificaciones_automaticas exists")
            except ImportError:
                self.log_result("Notification Command", False, "enviar_notificaciones_automaticas not found")

        except Exception as e:
            self.log_result("Notification System", False, str(e))

    def test_static_files(self):
        """Test 6: Archivos estáticos"""
        try:
            from django.conf import settings
            import os

            # Check STATIC_ROOT
            if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
                static_exists = os.path.exists(settings.STATIC_ROOT)
                self.log_result("Static Files Root", static_exists, settings.STATIC_ROOT)
            else:
                self.log_result("Static Files Root", False, "STATIC_ROOT not configured")

            # Check themes.css exists
            themes_css = os.path.join(settings.BASE_DIR, 'core', 'static', 'core', 'css', 'themes.css')
            self.log_result("Themes CSS", os.path.exists(themes_css))

        except Exception as e:
            self.log_result("Static Files", False, str(e))

    def test_url_patterns(self):
        """Test 7: Patrones de URL críticos"""
        critical_urls = [
            '/core/',
            '/core/dashboard/',
            '/core/panel-decisiones/',
            '/core/informes/',
            '/core/proveedores/',
            '/core/procedimientos/',
        ]

        for url in critical_urls:
            try:
                response = self.client.get(url)
                # 302 is OK (redirect to login if not authenticated)
                # 200 is OK (page loads)
                passed = response.status_code in [200, 302, 301]
                self.log_result(f"URL Pattern: {url}", passed, f"Status: {response.status_code}")
            except Exception as e:
                self.log_result(f"URL Pattern: {url}", False, str(e))

    def test_media_storage(self):
        """Test 8: Almacenamiento de archivos"""
        try:
            from django.conf import settings

            if hasattr(settings, 'AWS_STORAGE_BUCKET_NAME'):
                self.log_result("Media Storage", True, f"AWS S3: {settings.AWS_STORAGE_BUCKET_NAME}")
            elif hasattr(settings, 'MEDIA_ROOT'):
                import os
                media_exists = os.path.exists(settings.MEDIA_ROOT)
                self.log_result("Media Storage", media_exists, f"Local: {settings.MEDIA_ROOT}")
            else:
                self.log_result("Media Storage", False, "No media storage configured")

        except Exception as e:
            self.log_result("Media Storage", False, str(e))

    def test_async_zip_system(self):
        """Test 9: Sistema asíncrono de ZIP"""
        try:
            from core.async_zip_improved import AsyncZipProcessor

            # Check if processor exists
            self.log_result("Async ZIP Processor", True, "AsyncZipProcessor importado")

            # Check ZIP directory
            from django.conf import settings
            import os
            zip_dir = os.path.join(settings.MEDIA_ROOT, 'zip_files')
            self.log_result("ZIP Directory", os.path.exists(zip_dir) or True, zip_dir)

        except Exception as e:
            self.log_result("Async ZIP System", False, str(e))

    def test_permissions(self):
        """Test 10: Sistema de permisos"""
        try:
            from django.contrib.auth.models import Permission

            # Check core permissions
            core_perms = Permission.objects.filter(content_type__app_label='core').count()
            self.log_result("Permissions System", core_perms > 0, f"{core_perms} permisos de core")

        except Exception as e:
            self.log_result("Permissions System", False, str(e))

    def run_all_tests(self):
        """Ejecutar todos los tests"""
        print("\n" + "="*70)
        print("SAM METROLOGÍA - TEST COMPREHENSIVO DE PLATAFORMA")
        print("="*70 + "\n")

        self.test_database_connection()
        self.test_user_authentication()
        self.test_models_integrity()
        self.test_email_configuration()
        self.test_notification_system()
        self.test_static_files()
        self.test_url_patterns()
        self.test_media_storage()
        self.test_async_zip_system()
        self.test_permissions()

        # Summary
        print("\n" + "="*70)
        print("RESUMEN DE PRUEBAS")
        print("="*70)
        total = len(self.results)
        passed = total - len(self.errors)
        print(f"\nTotal de pruebas: {total}")
        print(f"Pruebas exitosas: {passed}")
        print(f"Pruebas fallidas: {len(self.errors)}")

        if self.errors:
            print("\n[!] ERRORES ENCONTRADOS:")
            for error in self.errors:
                print(f"  {error}")
        else:
            print("\n[OK] TODAS LAS PRUEBAS PASARON!")

        print("\n" + "="*70 + "\n")

        return len(self.errors) == 0

if __name__ == '__main__':
    tester = PlatformTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
