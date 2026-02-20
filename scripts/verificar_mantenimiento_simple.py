# Verificación simple del sistema de mantenimiento

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from core.models import MaintenanceTask, CommandLog, SystemHealthCheck
from core.admin_services import ScheduleManager
from django.utils import timezone

print("="*80)
print("VERIFICACION DEL SISTEMA DE MANTENIMIENTO")
print("="*80)
print()

# 1. Verificar modelos existen
print("[1] VERIFICANDO MODELOS...")
try:
    count_tasks = MaintenanceTask.objects.count()
    count_logs = CommandLog.objects.count()
    count_health = SystemHealthCheck.objects.count()

    print(f"   [OK] MaintenanceTask: {count_tasks} tareas registradas")
    print(f"   [OK] CommandLog: {count_logs} logs")
    print(f"   [OK] SystemHealthCheck: {count_health} health checks")
except Exception as e:
    print(f"   [X] ERROR: {e}")
    print("   Ejecutar: python manage.py migrate")
    exit(1)

print()

# 2. Verificar configuración de tareas programadas
print("[2] VERIFICANDO CONFIGURACION DE TAREAS PROGRAMADAS...")
try:
    config = ScheduleManager.get_schedule_config()

    print(f"\n   a) Mantenimiento Diario:")
    print(f"      - Habilitado: {config['maintenance_daily']['enabled']}")
    print(f"      - Hora: {config['maintenance_daily']['time']}")
    print(f"      - Tareas: {', '.join(config['maintenance_daily']['tasks'])}")

    print(f"\n   b) Notificaciones Diarias:")
    print(f"      - Habilitado: {config['notifications_daily']['enabled']}")
    print(f"      - Hora: {config['notifications_daily']['time']}")
    print(f"      - Tipos: {', '.join(config['notifications_daily']['types'])}")

    print(f"\n   c) Mantenimiento Semanal:")
    print(f"      - Habilitado: {config['maintenance_weekly']['enabled']}")
    print(f"      - Dia: {config['maintenance_weekly']['day_of_week']}")
    print(f"      - Hora: {config['maintenance_weekly']['time']}")

    print(f"\n   d) Notificaciones Semanales:")
    print(f"      - Habilitado: {config['notifications_weekly']['enabled']}")
    print(f"      - Dia: {config['notifications_weekly']['day_of_week']}")

    print(f"\n   e) Backup Mensual:")
    print(f"      - Habilitado: {config['backup_monthly']['enabled']}")
    print(f"      - Dia del mes: {config['backup_monthly']['day_of_month']}")

except Exception as e:
    print(f"   [X] ERROR al leer configuracion: {e}")

print()

# 3. Verificar ejecuciones recientes
print("[3] VERIFICANDO EJECUCIONES RECIENTES...")
try:
    # Tareas de los últimos 7 días
    recent_tasks = MaintenanceTask.objects.filter(
        created_at__gte=timezone.now() - timezone.timedelta(days=7)
    ).order_by('-created_at')[:10]

    if recent_tasks.exists():
        print(f"   [OK] Encontradas {recent_tasks.count()} tareas recientes (ultimos 7 dias)")
        print("\n   Ultimas 5 tareas:")
        for task in recent_tasks[:5]:
            status_symbol = "[OK]" if task.status == "completed" else "[!]"
            print(f"      {status_symbol} {task.get_task_type_display()}")
            print(f"         - Estado: {task.status}")
            print(f"         - Creada: {task.created_at.strftime('%Y-%m-%d %H:%M')}")
            if task.completed_at:
                print(f"         - Completada: {task.completed_at.strftime('%Y-%m-%d %H:%M')}")
            print()
    else:
        print("   [!] NO hay tareas ejecutadas en los ultimos 7 dias")
        print("   Esto podria significar:")
        print("      a) Las tareas programadas no se estan ejecutando automaticamente")
        print("      b) No se han ejecutado tareas manualmente")

except Exception as e:
    print(f"   [X] ERROR: {e}")

print()

# 4. Verificar health checks recientes
print("[4] VERIFICANDO HEALTH CHECKS...")
try:
    recent_health = SystemHealthCheck.objects.order_by('-checked_at')[:5]

    if recent_health.exists():
        print(f"   [OK] Encontrados {recent_health.count()} health checks recientes")
        latest = recent_health.first()
        print(f"\n   Ultimo health check:")
        print(f"      - Fecha: {latest.checked_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"      - Estado: {latest.status}")
        if latest.response_time_ms:
            print(f"      - Tiempo de respuesta: {latest.response_time_ms:.2f}ms")
    else:
        print("   [!] NO hay health checks registrados")

except Exception as e:
    print(f"   [X] ERROR: {e}")

print()

# 5. Verificar comandos de limpieza
print("[5] VERIFICANDO COMANDOS DE LIMPIEZA...")
try:
    # Verificar si hay archivos ZIP antiguos
    from pathlib import Path
    media_root = Path("media")
    if media_root.exists():
        zip_files = list(media_root.rglob("*.zip"))
        print(f"   [i] Archivos ZIP encontrados: {len(zip_files)}")
        if len(zip_files) > 50:
            print("   [!] Hay muchos archivos ZIP. Considerar ejecutar limpieza:")
            print("       python manage.py cleanup_zip_files --older-than-hours 6")
    else:
        print("   [i] Directorio media/ no encontrado")

except Exception as e:
    print(f"   [X] ERROR: {e}")

print()
print("="*80)
print("RESUMEN")
print("="*80)
print()
print("Para verificar si las tareas programadas se ejecutan automaticamente:")
print("  1. Verificar que las tareas esten habilitadas en la configuracion")
print("  2. Configurar un cron job o tarea programada de Windows:")
print("     - Ejecutar diariamente: python manage.py run_scheduled_tasks")
print("  3. Verificar logs de ejecucion en la interfaz web de mantenimiento")
print()
print("Para ejecutar tareas manualmente:")
print("  - Mantenimiento: python manage.py maintenance --all")
print("  - Notificaciones: python manage.py send_notifications --type consolidated")
print("  - Limpieza cache: python manage.py run_maintenance_task <task_id>")
print()
print("="*80)
