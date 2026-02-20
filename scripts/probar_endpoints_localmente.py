# Script para probar endpoints de tareas programadas localmente
# Ejecutar: python probar_endpoints_localmente.py

import requests
import json

# Configuración local
BASE_URL = "http://localhost:8000/core"
TOKEN = "change-this-secret-token-in-production"  # Token por defecto en desarrollo

# Headers con autenticación
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

print("="*80)
print("PROBANDO ENDPOINTS DE TAREAS PROGRAMADAS LOCALMENTE")
print("="*80)
print(f"Base URL: {BASE_URL}")
print(f"Token: {TOKEN}")
print()

# 1. Health Check (sin autenticación)
print("[1] Probando Health Check (sin autenticación)...")
try:
    response = requests.get(f"{BASE_URL}/api/scheduled/health/", timeout=10)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    print("   ✅ Health check OK")
except Exception as e:
    print(f"   ❌ Error: {e}")
print()

# 2. Notificaciones Diarias
print("[2] Probando Notificaciones Diarias...")
try:
    response = requests.post(
        f"{BASE_URL}/api/scheduled/notifications/daily/",
        headers=headers,
        timeout=30
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    if response.status_code == 200:
        print("   ✅ Notificaciones ejecutadas")
    else:
        print(f"   ❌ Error: {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")
print()

# 3. Mantenimiento Diario
print("[3] Probando Mantenimiento Diario...")
try:
    response = requests.post(
        f"{BASE_URL}/api/scheduled/maintenance/daily/",
        headers=headers,
        timeout=30
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    if response.status_code == 200:
        print("   ✅ Mantenimiento ejecutado")
    else:
        print(f"   ❌ Error: {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")
print()

# 4. Limpieza ZIPs
print("[4] Probando Limpieza de ZIPs...")
try:
    response = requests.post(
        f"{BASE_URL}/api/scheduled/cleanup/zips/",
        headers=headers,
        timeout=30
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    if response.status_code == 200:
        print("   ✅ Limpieza ejecutada")
    else:
        print(f"   ❌ Error: {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")
print()

# 5. Verificar Trials
print("[5] Probando Verificación de Trials...")
try:
    response = requests.post(
        f"{BASE_URL}/api/scheduled/check-trials/",
        headers=headers,
        timeout=30
    )
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
    if response.status_code == 200:
        print("   ✅ Trials verificados")
    else:
        print(f"   ❌ Error: {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")
print()

# 6. Probar sin token (debe fallar con 401)
print("[6] Probando sin autenticación (debe fallar)...")
try:
    response = requests.post(
        f"{BASE_URL}/api/scheduled/notifications/daily/",
        timeout=10
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 401:
        print("   ✅ Correctamente rechazado (401 Unauthorized)")
    else:
        print(f"   ⚠️  Esperaba 401, recibió: {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")
print()

print("="*80)
print("RESUMEN")
print("="*80)
print("Si todos los tests pasaron ✅, los endpoints funcionan correctamente.")
print("Ahora solo falta:")
print("  1. Esperar que Render despliegue el código (3-5 minutos)")
print("  2. Configurar secrets en GitHub")
print("  3. Ejecutar workflow manualmente en GitHub Actions")
print("="*80)
