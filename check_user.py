#!/usr/bin/env python
"""Script para verificar usuario certi y empresa demo."""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from core.models import CustomUser, Empresa

print("=" * 60)
print("VERIFICACION DE USUARIO CERTI")
print("=" * 60)

# Buscar empresa demo
try:
    empresa_demo = Empresa.objects.filter(nombre__icontains='demo').first()
    if empresa_demo:
        print(f"\n[OK] Empresa encontrada:")
        print(f"   ID: {empresa_demo.id}")
        print(f"   Nombre: {empresa_demo.nombre}")
        print(f"   NIT: {empresa_demo.nit}")
        print(f"   Limite equipos: {empresa_demo.limite_equipos_empresa}")
        print(f"   Equipos actuales: {empresa_demo.equipos.count()}")
    else:
        print("\n[ERROR] No se encontro empresa 'demo'")
        print("\nEmpresas disponibles:")
        for emp in Empresa.objects.all()[:5]:
            print(f"   - {emp.nombre} (ID: {emp.id})")
except Exception as e:
    print(f"\n[ERROR] Error buscando empresa: {e}")

# Buscar usuario certi
try:
    usuario_certi = CustomUser.objects.filter(username__icontains='certi').first()
    if usuario_certi:
        print(f"\n[OK] Usuario encontrado:")
        print(f"   ID: {usuario_certi.id}")
        print(f"   Username: {usuario_certi.username}")
        print(f"   Email: {usuario_certi.email}")
        print(f"   Empresa: {usuario_certi.empresa.nombre if usuario_certi.empresa else 'Sin empresa'}")
        print(f"   Rol: {usuario_certi.rol_usuario}")
        print(f"   Activo: {usuario_certi.is_active}")
        print(f"   Superuser: {usuario_certi.is_superuser}")
    else:
        print("\n[ERROR] No se encontro usuario 'certi'")
        print("\nUsuarios disponibles:")
        for user in CustomUser.objects.all()[:10]:
            print(f"   - {user.username} ({user.empresa.nombre if user.empresa else 'Sin empresa'})")
except Exception as e:
    print(f"\n[ERROR] Error buscando usuario: {e}")

# Si ambos existen, mostrar estadisticas
if empresa_demo and usuario_certi:
    print("\n" + "=" * 60)
    print("ESTADISTICAS EMPRESA DEMO")
    print("=" * 60)

    from core.models import Equipo, Calibracion, Mantenimiento

    equipos = Equipo.objects.filter(empresa=empresa_demo)
    print(f"\nEquipos: {equipos.count()}")

    if equipos.exists():
        print(f"   - Activos: {equipos.filter(estado='Activo').count()}")
        print(f"   - En calibracion: {equipos.filter(estado='En Calibración').count()}")

        calibraciones = Calibracion.objects.filter(equipo__empresa=empresa_demo)
        print(f"\nCalibraciones: {calibraciones.count()}")

        mantenimientos = Mantenimiento.objects.filter(equipo__empresa=empresa_demo)
        print(f"Mantenimientos: {mantenimientos.count()}")

print("\n" + "=" * 60)
