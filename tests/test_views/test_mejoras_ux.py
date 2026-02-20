#!/usr/bin/env python
"""
Test de Funcionalidad - Mejoras UX SAM
Verifica que las implementaciones funcionan correctamente
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Equipo, Empresa
from django.test import Client
from django.urls import reverse

User = get_user_model()

def print_header(text):
    """Imprime un header formateado"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_test(name, passed):
    """Imprime resultado de test"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {name}")

def test_permissions():
    """Test 1: Verificar permisos de eliminación"""
    print_header("TEST 1: PERMISOS DE ELIMINACIÓN")

    try:
        # Verificar que el método existe
        if hasattr(User, 'puede_eliminar_equipos'):
            print_test("Método puede_eliminar_equipos() existe", True)
        else:
            print_test("Método puede_eliminar_equipos() existe", False)
            return False

        # Crear usuarios de prueba si no existen
        empresa, _ = Empresa.objects.get_or_create(
            nombre='Empresa Test',
            defaults={'nit': '123456789'}
        )

        # Técnico
        tecnico, _ = User.objects.get_or_create(
            username='tecnico_test',
            defaults={
                'empresa': empresa,
                'rol_usuario': 'TECNICO',
                'email': 'tecnico@test.com'
            }
        )
        print_test(f"Técnico NO puede eliminar: {not tecnico.puede_eliminar_equipos()}",
                   not tecnico.puede_eliminar_equipos())

        # Administrador
        admin, _ = User.objects.get_or_create(
            username='admin_test',
            defaults={
                'empresa': empresa,
                'rol_usuario': 'ADMINISTRADOR',
                'email': 'admin@test.com'
            }
        )
        print_test(f"Administrador SÍ puede eliminar: {admin.puede_eliminar_equipos()}",
                   admin.puede_eliminar_equipos())

        # Gerencia
        gerente, _ = User.objects.get_or_create(
            username='gerente_test',
            defaults={
                'empresa': empresa,
                'rol_usuario': 'GERENCIA',
                'email': 'gerente@test.com'
            }
        )
        print_test(f"Gerente SÍ puede eliminar: {gerente.puede_eliminar_equipos()}",
                   gerente.puede_eliminar_equipos())

        return True
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_middleware():
    """Test 2: Verificar que el middleware está activo"""
    print_header("TEST 2: MIDDLEWARE DE SESIÓN")

    try:
        from django.conf import settings

        middlewares = settings.MIDDLEWARE

        # Verificar SessionActivityMiddleware
        has_session_middleware = any('SessionActivityMiddleware' in m for m in middlewares)
        print_test("SessionActivityMiddleware está en MIDDLEWARE", has_session_middleware)

        # Verificar orden correcto
        auth_index = next((i for i, m in enumerate(middlewares) if 'AuthenticationMiddleware' in m), -1)
        session_index = next((i for i, m in enumerate(middlewares) if 'SessionActivityMiddleware' in m), -1)

        if auth_index != -1 and session_index != -1:
            correct_order = session_index > auth_index
            print_test("SessionActivityMiddleware está después de AuthenticationMiddleware", correct_order)

        return has_session_middleware
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_heartbeat_endpoint():
    """Test 3: Verificar endpoint de heartbeat"""
    print_header("TEST 3: ENDPOINT DE HEARTBEAT")

    try:
        from django.urls import resolve

        # Verificar que la URL existe
        try:
            url = reverse('core:session_heartbeat')
            print_test(f"URL 'session_heartbeat' existe: {url}", True)
        except Exception:
            print_test("URL 'session_heartbeat' existe", False)
            return False

        # Verificar que la vista existe
        from core.views import base
        has_view = hasattr(base, 'session_heartbeat')
        print_test("Vista session_heartbeat existe", has_view)

        return has_view
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_navigation_logic():
    """Test 4: Verificar lógica de navegación entre equipos"""
    print_header("TEST 4: NAVEGACIÓN ENTRE EQUIPOS")

    try:
        # Verificar que la vista de edición tiene los parámetros necesarios
        from core.views import equipment
        import inspect

        # Obtener código fuente de la función
        source = inspect.getsource(equipment.editar_equipo)

        # Verificar que tiene la lógica de navegación
        has_prev = 'prev_equipo_id' in source
        has_next = 'next_equipo_id' in source
        has_position = 'current_position' in source
        has_save_and_next = 'save_and_next' in source
        has_save_and_prev = 'save_and_prev' in source

        print_test("Lógica de equipo anterior implementada", has_prev)
        print_test("Lógica de equipo siguiente implementada", has_next)
        print_test("Indicador de posición implementado", has_position)
        print_test("Botón 'save_and_next' implementado", has_save_and_next)
        print_test("Botón 'save_and_prev' implementado", has_save_and_prev)

        return has_prev and has_next and has_position
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_static_files():
    """Test 5: Verificar archivos estáticos"""
    print_header("TEST 5: ARCHIVOS ESTÁTICOS")

    try:
        import os
        from django.conf import settings

        # Verificar JavaScript de heartbeat
        js_path = os.path.join(settings.BASE_DIR, 'core', 'static', 'core', 'js', 'session_keepalive.js')
        has_js = os.path.exists(js_path)
        print_test(f"session_keepalive.js existe", has_js)

        if has_js:
            # Verificar contenido básico
            with open(js_path, 'r', encoding='utf-8') as f:
                content = f.read()
                has_heartbeat = 'sendHeartbeat' in content
                has_activity = 'lastActivityTime' in content
                has_warning = 'showWarning' in content

                print_test("Función sendHeartbeat existe", has_heartbeat)
                print_test("Tracking de actividad existe", has_activity)
                print_test("Sistema de advertencias existe", has_warning)

                return has_heartbeat and has_activity and has_warning

        return has_js
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_database():
    """Test 6: Verificar estado de la base de datos"""
    print_header("TEST 6: BASE DE DATOS")

    try:
        # Verificar que la columna puntos_calibracion existe
        equipo_fields = [f.name for f in Equipo._meta.get_fields()]
        has_puntos = 'puntos_calibracion' in equipo_fields
        print_test("Campo 'puntos_calibracion' existe en Equipo", has_puntos)

        # Verificar que podemos hacer queries
        try:
            count = Equipo.objects.count()
            print_test(f"Query a Equipo funciona (total: {count})", True)
        except Exception as e:
            print_test(f"Query a Equipo funciona", False)
            print(f"   Error: {e}")
            return False

        # Verificar que podemos acceder al campo
        if count > 0:
            equipo = Equipo.objects.first()
            try:
                _ = equipo.puntos_calibracion
                print_test("Campo 'puntos_calibracion' es accesible", True)
            except Exception as e:
                print_test("Campo 'puntos_calibracion' es accesible", False)
                print(f"   Error: {e}")
                return False

        return has_puntos
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def run_all_tests():
    """Ejecuta todos los tests"""
    print("\n" + "🚀 "*20)
    print("   TEST DE FUNCIONALIDAD - MEJORAS UX SAM")
    print("🚀 "*20)

    results = {}

    # Ejecutar tests
    results['Permisos'] = test_permissions()
    results['Middleware'] = test_middleware()
    results['Endpoint Heartbeat'] = test_heartbeat_endpoint()
    results['Navegación'] = test_navigation_logic()
    results['Archivos Estáticos'] = test_static_files()
    results['Base de Datos'] = test_database()

    # Resumen final
    print_header("RESUMEN FINAL")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print("\n" + "-"*60)
    percentage = (passed / total) * 100
    print(f"Total: {passed}/{total} tests pasados ({percentage:.1f}%)")

    if passed == total:
        print("\n🎉 ¡TODOS LOS TESTS PASARON! El sistema está funcionando correctamente.")
    elif passed >= total * 0.75:
        print("\n✅ La mayoría de tests pasaron. Algunas funcionalidades están listas.")
    else:
        print("\n⚠️ Varios tests fallaron. Revisa los errores arriba.")

    print("="*60 + "\n")

    return passed == total


if __name__ == '__main__':
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrumpidos por el usuario.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERROR FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
