#!/usr/bin/env python
"""
Script de testing automatizado para usuario CERTI.
Simula tests manuales y mide rendimiento.
"""
import os
import sys
import django
import time
from datetime import datetime

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from core.models import CustomUser, Empresa

print("=" * 70)
print("TESTING AUTOMATIZADO - USUARIO CERTI")
print("Dia 13: Validacion con Usuario Real")
print("=" * 70)

# Obtener usuario certi
try:
    usuario = CustomUser.objects.get(username='CERTI')
    print(f"\n[OK] Usuario encontrado: {usuario.username}")
    print(f"     Empresa: {usuario.empresa.nombre}")
    print(f"     Rol: {usuario.rol_usuario}")
except CustomUser.DoesNotExist:
    print("\n[ERROR] Usuario CERTI no encontrado")
    sys.exit(1)

# Crear cliente de testing
client = Client()

# Login
print("\n" + "=" * 70)
print("TEST 1: LOGIN Y AUTENTICACION")
print("=" * 70)

# Nota: Necesitamos la password real. Vamos a simular login con force_login
client.force_login(usuario)
print("[OK] Login simulado exitoso (force_login)")

# Test Dashboard - Primera carga
print("\n" + "=" * 70)
print("TEST 2: DASHBOARD - PRIMERA CARGA (SIN CACHE)")
print("=" * 70)

start_time = time.time()
response = client.get(reverse('core:dashboard'))
elapsed_first = time.time() - start_time

print(f"\nStatus code: {response.status_code}")
print(f"Tiempo de carga: {elapsed_first:.3f}s")

if response.status_code == 200:
    print("[OK] Dashboard cargado correctamente")
    if elapsed_first < 1.0:
        print(f"[EXCELENTE] Tiempo < 1s (Meta alcanzada!)")
    elif elapsed_first < 2.0:
        print(f"[BUENO] Tiempo < 2s (Aceptable)")
    else:
        print(f"[ATENCION] Tiempo > 2s (Revisar optimizaciones)")

    # Verificar contexto
    if 'total_equipos' in response.context:
        print(f"\nEstadisticas:")
        print(f"  Total equipos: {response.context.get('total_equipos', 'N/A')}")
        print(f"  Activos: {response.context.get('equipos_activos', 'N/A')}")
        print(f"  En calibracion: {response.context.get('equipos_en_calibracion', 'N/A')}")
else:
    print(f"[ERROR] Dashboard retorno status {response.status_code}")

# Test Dashboard - Segunda carga (con cache)
print("\n" + "=" * 70)
print("TEST 3: DASHBOARD - SEGUNDA CARGA (CON CACHE)")
print("=" * 70)

start_time = time.time()
response = client.get(reverse('core:dashboard'))
elapsed_cached = time.time() - start_time

print(f"\nStatus code: {response.status_code}")
print(f"Tiempo de carga: {elapsed_cached:.3f}s ({elapsed_cached*1000:.1f}ms)")

if elapsed_cached < 0.1:  # <100ms
    print(f"[EXCELENTE] Cache funcionando perfectamente!")
elif elapsed_cached < 0.5:  # <500ms
    print(f"[BUENO] Cache ayudando, pero puede mejorar")
else:
    print(f"[ATENCION] Cache no parece estar funcionando")

mejora_percentage = ((elapsed_first - elapsed_cached) / elapsed_first) * 100
print(f"\nMejora con cache: {mejora_percentage:.1f}%")

# Test Lista de Equipos
print("\n" + "=" * 70)
print("TEST 4: LISTA DE EQUIPOS")
print("=" * 70)

start_time = time.time()
response = client.get(reverse('core:home'))
elapsed_list = time.time() - start_time

print(f"\nStatus code: {response.status_code}")
print(f"Tiempo de carga: {elapsed_list:.3f}s")

if response.status_code == 200:
    print("[OK] Lista de equipos cargada")
    if elapsed_list < 0.5:
        print(f"[EXCELENTE] Tiempo < 500ms")
    elif elapsed_list < 1.0:
        print(f"[BUENO] Tiempo < 1s")
    else:
        print(f"[ATENCION] Tiempo > 1s")
else:
    print(f"[ERROR] Lista retorno status {response.status_code}")

# Test Panel de Decisiones (solo para GERENCIA)
print("\n" + "=" * 70)
print("TEST 5: PANEL DE DECISIONES (ROL GERENCIA)")
print("=" * 70)

if usuario.rol_usuario == 'GERENCIA':
    start_time = time.time()
    response = client.get(reverse('core:panel_decisiones'))
    elapsed_panel = time.time() - start_time

    print(f"\nStatus code: {response.status_code}")
    print(f"Tiempo de carga: {elapsed_panel:.3f}s")

    if response.status_code == 200:
        print("[OK] Panel de decisiones accesible para GERENCIA")
    else:
        print(f"[ERROR] Panel retorno status {response.status_code}")
else:
    print(f"[SKIP] Usuario no es GERENCIA, saltando test")

# Test Informes
print("\n" + "=" * 70)
print("TEST 6: SISTEMA DE INFORMES")
print("=" * 70)

start_time = time.time()
response = client.get(reverse('core:informes'))
elapsed_informes = time.time() - start_time

print(f"\nStatus code: {response.status_code}")
print(f"Tiempo de carga: {elapsed_informes:.3f}s")

if response.status_code == 200:
    print("[OK] Informes cargados correctamente")
else:
    print(f"[ERROR] Informes retorno status {response.status_code}")

# Resumen de rendimiento
print("\n" + "=" * 70)
print("RESUMEN DE RENDIMIENTO")
print("=" * 70)

resultados = [
    ("Dashboard (1ra carga)", elapsed_first, 1.0),
    ("Dashboard (cache)", elapsed_cached, 0.05),
    ("Lista equipos", elapsed_list, 0.5),
]

if usuario.rol_usuario == 'GERENCIA':
    resultados.append(("Panel decisiones", elapsed_panel, 2.0))

resultados.append(("Informes", elapsed_informes, 1.5))

print(f"\n{'Endpoint':<25} {'Tiempo':<12} {'Meta':<10} {'Estado'}")
print("-" * 70)

aprobados = 0
total = len(resultados)

for nombre, tiempo, meta in resultados:
    estado = "[OK]" if tiempo < meta else "[LENTO]"
    if tiempo < meta:
        aprobados += 1
    print(f"{nombre:<25} {tiempo:>6.3f}s      <{meta}s       {estado}")

print("-" * 70)
print(f"\nTests aprobados: {aprobados}/{total} ({aprobados/total*100:.1f}%)")

# Calificacion final
if aprobados == total:
    calificacion = "EXCELENTE"
    puntos = 10
elif aprobados >= total * 0.8:
    calificacion = "BUENO"
    puntos = 8
elif aprobados >= total * 0.6:
    calificacion = "ACEPTABLE"
    puntos = 6
else:
    calificacion = "NECESITA MEJORAS"
    puntos = 4

print(f"\nCalificacion de rendimiento: {calificacion} ({puntos}/10)")

# Guardar resultados
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"test_results_certi_{timestamp}.txt"

with open(output_file, 'w') as f:
    f.write("RESULTADOS TESTING AUTOMATIZADO - USUARIO CERTI\n")
    f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("=" * 70 + "\n\n")

    f.write("RENDIMIENTO:\n")
    for nombre, tiempo, meta in resultados:
        estado = "OK" if tiempo < meta else "LENTO"
        f.write(f"  {nombre}: {tiempo:.3f}s (meta: <{meta}s) [{estado}]\n")

    f.write(f"\nAprobados: {aprobados}/{total}\n")
    f.write(f"Calificacion: {calificacion} ({puntos}/10)\n")

print(f"\n[OK] Resultados guardados en: {output_file}")

print("\n" + "=" * 70)
print("TESTING COMPLETADO")
print("=" * 70)
print("\nPasos siguientes:")
print("1. Revisar resultados guardados")
print("2. Completar testing manual con usuario real")
print("3. Probar dark mode y keyboard shortcuts manualmente")
print("4. Probar responsive design en diferentes dispositivos")
print("\n" + "=" * 70)
