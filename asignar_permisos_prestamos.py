#!/usr/bin/env python
"""
Script para asignar permisos de préstamos a usuarios o grupos

Uso:
    python asignar_permisos_prestamos.py

Este script asigna todos los permisos relacionados con préstamos
a todos los usuarios activos del sistema (excepto superusuarios que ya los tienen).
"""

import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from core.models import PrestamoEquipo, AgrupacionPrestamo

User = get_user_model()

def asignar_permisos_prestamos():
    """Asigna permisos de préstamos a todos los usuarios activos"""

    print("=" * 60)
    print("ASIGNANDO PERMISOS DEL SISTEMA DE PRÉSTAMOS")
    print("=" * 60)
    print()

    # Obtener todos los permisos de préstamos
    content_type_prestamo = ContentType.objects.get_for_model(PrestamoEquipo)
    content_type_agrupacion = ContentType.objects.get_for_model(AgrupacionPrestamo)

    permisos_prestamo = Permission.objects.filter(content_type=content_type_prestamo)
    permisos_agrupacion = Permission.objects.filter(content_type=content_type_agrupacion)

    print(f"[OK] Encontrados {permisos_prestamo.count()} permisos de PrestamoEquipo")
    print(f"[OK] Encontrados {permisos_agrupacion.count()} permisos de AgrupacionPrestamo")
    print()

    # Listar permisos
    print("Permisos a asignar:")
    for perm in permisos_prestamo:
        print(f"  - {perm.codename}: {perm.name}")
    for perm in permisos_agrupacion:
        print(f"  - {perm.codename}: {perm.name}")
    print()

    # Obtener usuarios activos (no superusuarios)
    usuarios = User.objects.filter(is_active=True, is_superuser=False)

    print(f"Usuarios activos encontrados: {usuarios.count()}")
    print()

    if usuarios.count() == 0:
        print("[ADVERTENCIA] No hay usuarios activos para asignar permisos.")
        print("   Los superusuarios ya tienen todos los permisos.")
        return

    # Confirmar
    respuesta = input("Deseas asignar estos permisos a TODOS los usuarios activos? (s/n): ")
    if respuesta.lower() != 's':
        print("[CANCELADO] Operacion cancelada.")
        return

    # Asignar permisos
    usuarios_actualizados = 0
    for usuario in usuarios:
        # Asignar permisos de préstamos
        usuario.user_permissions.add(*permisos_prestamo)
        usuario.user_permissions.add(*permisos_agrupacion)
        usuarios_actualizados += 1
        print(f"[OK] Permisos asignados a: {usuario.username} ({usuario.email})")

    print()
    print("=" * 60)
    print(f"[COMPLETADO] Permisos asignados a {usuarios_actualizados} usuario(s)")
    print("=" * 60)
    print()
    print("Ahora los usuarios podrán:")
    print("  1. Ver el menú 'Préstamos' en el sidebar")
    print("  2. Acceder al dashboard de préstamos")
    print("  3. Crear nuevos préstamos")
    print("  4. Ver y devolver préstamos")
    print()
    print("NOTA: Recarga la página web para ver los cambios")
    print()

if __name__ == '__main__':
    try:
        asignar_permisos_prestamos()
    except KeyboardInterrupt:
        print("\n[CANCELADO] Operacion cancelada por el usuario.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
