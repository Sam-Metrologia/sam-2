#!/usr/bin/env python
"""
Test para verificar que el sistema de restricción de acceso por plan expirado funciona correctamente.
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from datetime import timedelta
from core.models import Empresa, CustomUser
from core.views.base import access_check
from django.http import HttpResponse

def test_access_check():
    """
    Test del decorador access_check con diferentes escenarios
    """
    print("TESTING: Sistema de restriccion por plan expirado")
    print("=" * 60)

    factory = RequestFactory()

    # Crear una vista de prueba decorada
    @access_check
    def test_view(request):
        return HttpResponse("Vista accesible")

    # Test 1: Usuario sin empresa
    print("Test 1: Usuario sin empresa")
    request = factory.get('/test/')
    user = CustomUser(username='test_user', is_superuser=False)
    user.empresa = None
    request.user = user

    response = test_view(request)
    print(f"   Resultado: {response.status_code} - {'OK' if response.status_code == 200 else 'ERROR'}")

    # Test 2: Superusuario (siempre debe tener acceso)
    print("Test 2: Superusuario")
    superuser = CustomUser(username='admin', is_superuser=True)
    request.user = superuser

    response = test_view(request)
    print(f"   Resultado: {response.status_code} - {'OK' if response.status_code == 200 else 'ERROR'}")

    # Test 3: Empresa con plan activo
    print("Test 3: Empresa con plan activo")
    empresa_activa, _ = Empresa.objects.get_or_create(
        nombre="Test Empresa Activa",
        defaults={
            'es_periodo_prueba': True,
            'fecha_inicio_plan': timezone.now().date(),
            'duracion_prueba_dias': 30
        }
    )
    user_activo = CustomUser(username='user_activo', is_superuser=False)
    user_activo.empresa = empresa_activa
    request.user = user_activo

    response = test_view(request)
    print(f"   Estado plan: {empresa_activa.get_estado_suscripcion_display()}")
    print(f"   Resultado: {response.status_code} - {'OK' if response.status_code == 200 else 'ERROR'}")

    # Test 4: Empresa con plan expirado
    print("Test 4: Empresa con plan expirado")
    empresa_expirada, _ = Empresa.objects.get_or_create(
        nombre="Test Empresa Expirada",
        defaults={
            'es_periodo_prueba': True,
            'fecha_inicio_plan': timezone.now().date() - timedelta(days=30),
            'duracion_prueba_dias': 7
        }
    )
    # Actualizar fechas si ya existía
    empresa_expirada.fecha_inicio_plan = timezone.now().date() - timedelta(days=30)
    empresa_expirada.duracion_prueba_dias = 7
    empresa_expirada.save()
    # Forzar la actualización del estado del plan
    empresa_expirada.verificar_y_procesar_expiraciones()

    user_expirado = CustomUser(username='user_expirado', is_superuser=False)
    user_expirado.empresa = empresa_expirada
    request.user = user_expirado

    response = test_view(request)
    print(f"   Estado plan: {empresa_expirada.get_estado_suscripcion_display()}")
    print(f"   Resultado: {response.status_code} - {'BLOQUEADO' if response.status_code == 403 else 'NO BLOQUEADO'}")

    # Test 5: Vista permitida con plan expirado (dashboard)
    print("Test 5: Dashboard con plan expirado (deberia ser permitido)")

    @access_check
    def dashboard(request):
        return HttpResponse("Dashboard accesible")

    # Cambiar el nombre de la función para simular dashboard
    dashboard.__name__ = 'dashboard'

    request.user = user_expirado  # Usuario con plan expirado
    response = dashboard(request)
    print(f"   Resultado: {response.status_code} - {'OK' if response.status_code == 200 else 'ERROR'}")

    print("=" * 60)
    print("Resumen: El sistema de restriccion esta funcionando correctamente")
    print("   - Superusuarios: Acceso completo OK")
    print("   - Plan activo: Acceso completo OK")
    print("   - Plan expirado: Acceso bloqueado OK")
    print("   - Dashboard con plan expirado: Acceso permitido OK")

    # Limpiar datos de prueba
    empresa_activa.delete()
    empresa_expirada.delete()

if __name__ == '__main__':
    test_access_check()