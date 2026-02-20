#!/usr/bin/env python
"""
Script de verificación del sistema de préstamos

Verifica que:
- Los modelos estén creados correctamente
- Los usuarios tengan empresa asignada
- Los permisos estén configurados
- Haya equipos disponibles para prestar
"""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from core.models import PrestamoEquipo, AgrupacionPrestamo, Equipo, Empresa

User = get_user_model()

def verificar_sistema():
    print("=" * 70)
    print("VERIFICACION DEL SISTEMA DE PRESTAMOS")
    print("=" * 70)
    print()

    # 1. Verificar modelos
    print("1. MODELOS:")
    print("-" * 70)
    try:
        total_prestamos = PrestamoEquipo.objects.count()
        total_agrupaciones = AgrupacionPrestamo.objects.count()
        print(f"   [OK] PrestamoEquipo: {total_prestamos} registros")
        print(f"   [OK] AgrupacionPrestamo: {total_agrupaciones} registros")
    except Exception as e:
        print(f"   [ERROR] No se pueden acceder a los modelos: {e}")
        return
    print()

    # 2. Verificar usuarios y empresas
    print("2. USUARIOS Y EMPRESAS:")
    print("-" * 70)
    usuarios = User.objects.filter(is_active=True)
    usuarios_sin_empresa = []
    usuarios_con_empresa = []

    for usuario in usuarios:
        if usuario.empresa:
            usuarios_con_empresa.append(usuario)
            print(f"   [OK] {usuario.username:15} -> {usuario.empresa.nombre}")
        else:
            usuarios_sin_empresa.append(usuario)
            print(f"   [ADVERTENCIA] {usuario.username:15} -> SIN EMPRESA")

    if usuarios_sin_empresa:
        print()
        print(f"   ACCION REQUERIDA: {len(usuarios_sin_empresa)} usuario(s) sin empresa")
        print("   Estos usuarios NO podran crear prestamos.")
    print()

    # 3. Verificar permisos
    print("3. PERMISOS:")
    print("-" * 70)
    permisos_prestamo = Permission.objects.filter(
        codename__in=['can_view_prestamo', 'can_add_prestamo',
                      'can_change_prestamo', 'can_delete_prestamo']
    )

    if permisos_prestamo.count() == 0:
        print("   [ERROR] No se encontraron permisos de prestamos!")
        return

    print(f"   [OK] Encontrados {permisos_prestamo.count()} permisos principales")

    # Verificar cuántos usuarios tienen permisos
    usuarios_con_permisos = 0
    for usuario in usuarios_con_empresa:
        if usuario.has_perm('core.can_view_prestamo'):
            usuarios_con_permisos += 1

    print(f"   [OK] {usuarios_con_permisos} usuario(s) con permiso can_view_prestamo")

    if usuarios_con_permisos == 0:
        print("   [ADVERTENCIA] Ningun usuario tiene permisos de prestamos")
        print("   Ejecuta: python asignar_permisos_prestamos.py")
    print()

    # 4. Verificar equipos disponibles
    print("4. EQUIPOS DISPONIBLES:")
    print("-" * 70)
    empresas = Empresa.objects.all()

    for empresa in empresas:
        equipos_totales = Equipo.objects.filter(empresa=empresa).count()

        # Equipos disponibles para préstamo
        equipos_disponibles = Equipo.objects.filter(
            empresa=empresa,
            estado__in=['Activo', 'En Mantenimiento', 'En Calibración', 'En Comprobación']
        ).exclude(
            prestamos__estado_prestamo='ACTIVO',
            prestamos__fecha_devolucion_real__isnull=True
        ).count()

        prestamos_activos = PrestamoEquipo.objects.filter(
            empresa=empresa,
            estado_prestamo='ACTIVO'
        ).count()

        print(f"   Empresa: {empresa.nombre}")
        print(f"      Total equipos: {equipos_totales}")
        print(f"      Disponibles: {equipos_disponibles}")
        print(f"      En prestamo: {prestamos_activos}")
        print()

    # 5. Resumen
    print("=" * 70)
    print("RESUMEN:")
    print("=" * 70)

    problemas = []

    if usuarios_sin_empresa:
        problemas.append(f"- {len(usuarios_sin_empresa)} usuario(s) sin empresa")

    if usuarios_con_permisos == 0:
        problemas.append("- Ningun usuario tiene permisos de prestamos")

    if problemas:
        print("[ADVERTENCIAS ENCONTRADAS]")
        for problema in problemas:
            print(f"  {problema}")
        print()
        print("ACCIONES SUGERIDAS:")
        if usuarios_sin_empresa:
            print("  1. Asignar empresa a los usuarios sin empresa")
            print("     -> Admin Django -> Usuarios -> Editar usuario -> Empresa")
        if usuarios_con_permisos == 0:
            print("  2. Asignar permisos ejecutando:")
            print("     -> python asignar_permisos_prestamos.py")
    else:
        print("[SISTEMA CONFIGURADO CORRECTAMENTE]")
        print()
        print("El sistema de prestamos esta listo para usar!")
        print("Accede a: http://localhost:8000 -> Menu -> Prestamos")

    print()
    print("=" * 70)

if __name__ == '__main__':
    try:
        verificar_sistema()
    except Exception as e:
        print(f"\n[ERROR] Error al verificar el sistema: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
