"""
Script para limpiar solicitudes ZIP pendientes/huérfanas
Ejecutar con: python manage.py shell < limpiar_cola_zip.py
"""
from core.models import ZipRequest
from django.utils import timezone

print("=" * 60)
print("🧹 LIMPIEZA DE COLA ZIP")
print("=" * 60)

# Mostrar estado actual
total = ZipRequest.objects.count()
pendientes = ZipRequest.objects.filter(status='pending').count()
en_cola = ZipRequest.objects.filter(status='queued').count()
procesando = ZipRequest.objects.filter(status='processing').count()
completadas = ZipRequest.objects.filter(status='completed').count()
fallidas = ZipRequest.objects.filter(status='failed').count()

print(f"\n📊 ESTADO ACTUAL:")
print(f"  Total: {total}")
print(f"  Pendientes: {pendientes}")
print(f"  En cola: {en_cola}")
print(f"  Procesando: {procesando}")
print(f"  Completadas: {completadas}")
print(f"  Fallidas: {fallidas}")

# Listar solicitudes pendientes
print(f"\n📦 SOLICITUDES PENDIENTES:")
for req in ZipRequest.objects.filter(status__in=['pending', 'queued', 'processing']).order_by('created_at'):
    print(f"  ID: {req.id} | Empresa: {req.empresa.nombre} | Usuario: {req.user.username} | Parte: {req.parte_numero}/{req.total_partes} | Creada: {req.created_at}")

# Opción 1: Eliminar TODAS las solicitudes pendientes/en cola
print(f"\n🗑️  OPCIÓN 1: Eliminar todas las pendientes/en cola ({pendientes + en_cola + procesando})")
confirmar = input("¿Desea eliminar TODAS las solicitudes pendientes/en cola/procesando? (si/no): ")
if confirmar.lower() == 'si':
    ZipRequest.objects.filter(status__in=['pending', 'queued', 'processing']).delete()
    print("✅ Solicitudes pendientes eliminadas")
else:
    print("❌ Operación cancelada")

# Opción 2: Marcar como fallidas
print(f"\n⚠️  OPCIÓN 2: Marcar pendientes como fallidas (mantener historial)")
confirmar2 = input("¿Desea marcar todas las pendientes como fallidas? (si/no): ")
if confirmar2.lower() == 'si':
    actualizadas = ZipRequest.objects.filter(status__in=['pending', 'queued', 'processing']).update(
        status='failed',
        error_message='Solicitud huérfana - procesador no corriendo',
        completed_at=timezone.now()
    )
    print(f"✅ {actualizadas} solicitudes marcadas como fallidas")
else:
    print("❌ Operación cancelada")

# Estado final
print(f"\n📊 ESTADO FINAL:")
pendientes_final = ZipRequest.objects.filter(status='pending').count()
print(f"  Pendientes: {pendientes_final}")
print(f"  Total: {ZipRequest.objects.count()}")

print("\n" + "=" * 60)
print("✅ LIMPIEZA COMPLETADA")
print("=" * 60)
