#!/usr/bin/env python
"""
Script de verificación del Sistema de Mantenimiento Web
Ejecutar: python verificar_sistema_mantenimiento.py
"""

import os
import sys
from pathlib import Path

# Colores para output
class Colors:
    OK = '\033[92m'
    FAIL = '\033[91m'
    WARNING = '\033[93m'
    INFO = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_ok(msg):
    print(f"{Colors.OK}✓{Colors.ENDC} {msg}")

def print_fail(msg):
    print(f"{Colors.FAIL}✗{Colors.ENDC} {msg}")

def print_warning(msg):
    print(f"{Colors.WARNING}⚠{Colors.ENDC} {msg}")

def print_info(msg):
    print(f"{Colors.INFO}ℹ{Colors.ENDC} {msg}")

def check_file_exists(file_path, description):
    """Verifica que un archivo exista"""
    if Path(file_path).exists():
        print_ok(f"{description}: {file_path}")
        return True
    else:
        print_fail(f"{description} NO ENCONTRADO: {file_path}")
        return False

def check_directory_exists(dir_path, description):
    """Verifica que un directorio exista"""
    if Path(dir_path).is_dir():
        print_ok(f"{description}: {dir_path}")
        return True
    else:
        print_fail(f"{description} NO ENCONTRADO: {dir_path}")
        return False

def check_string_in_file(file_path, search_string, description):
    """Verifica que un string exista en un archivo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if search_string in content:
                print_ok(description)
                return True
            else:
                print_fail(f"{description} - NO ENCONTRADO")
                return False
    except Exception as e:
        print_fail(f"{description} - ERROR: {e}")
        return False

def main():
    print("=" * 70)
    print(f"{Colors.BOLD}VERIFICACIÓN DEL SISTEMA DE MANTENIMIENTO WEB{Colors.ENDC}")
    print("=" * 70)
    print()

    BASE_DIR = Path(__file__).resolve().parent
    checks_passed = 0
    checks_failed = 0

    # 1. VERIFICAR MODELOS
    print(f"\n{Colors.BOLD}1. VERIFICANDO MODELOS{Colors.ENDC}")
    print("-" * 70)

    if check_string_in_file(
        BASE_DIR / 'core/models.py',
        'class MaintenanceTask',
        'Modelo MaintenanceTask'
    ):
        checks_passed += 1
    else:
        checks_failed += 1

    if check_string_in_file(
        BASE_DIR / 'core/models.py',
        'class CommandLog',
        'Modelo CommandLog'
    ):
        checks_passed += 1
    else:
        checks_failed += 1

    if check_string_in_file(
        BASE_DIR / 'core/models.py',
        'class SystemHealthCheck',
        'Modelo SystemHealthCheck'
    ):
        checks_passed += 1
    else:
        checks_failed += 1

    # 2. VERIFICAR COMANDOS
    print(f"\n{Colors.BOLD}2. VERIFICANDO COMANDOS DJANGO{Colors.ENDC}")
    print("-" * 70)

    if check_file_exists(
        BASE_DIR / 'core/management/commands/run_maintenance_task.py',
        'Comando run_maintenance_task'
    ):
        checks_passed += 1
    else:
        checks_failed += 1

    # 3. VERIFICAR VISTAS
    print(f"\n{Colors.BOLD}3. VERIFICANDO VISTAS{Colors.ENDC}")
    print("-" * 70)

    if check_file_exists(
        BASE_DIR / 'core/views/maintenance.py',
        'Archivo de vistas maintenance.py'
    ):
        checks_passed += 1
    else:
        checks_failed += 1

    views_to_check = [
        'maintenance_dashboard',
        'create_maintenance_task',
        'maintenance_task_detail',
        'task_status_api',
        'task_logs_api'
    ]

    for view in views_to_check:
        if check_string_in_file(
            BASE_DIR / 'core/views/maintenance.py',
            f'def {view}',
            f'Vista {view}'
        ):
            checks_passed += 1
        else:
            checks_failed += 1

    # 4. VERIFICAR URLS
    print(f"\n{Colors.BOLD}4. VERIFICANDO URLS{Colors.ENDC}")
    print("-" * 70)

    if check_string_in_file(
        BASE_DIR / 'core/urls.py',
        "path('maintenance/'",
        'URL maintenance/'
    ):
        checks_passed += 1
    else:
        checks_failed += 1

    if check_string_in_file(
        BASE_DIR / 'core/urls.py',
        "path('api/maintenance/task/<int:task_id>/status/'",
        'URL API task status'
    ):
        checks_passed += 1
    else:
        checks_failed += 1

    # 5. VERIFICAR TEMPLATES
    print(f"\n{Colors.BOLD}5. VERIFICANDO TEMPLATES{Colors.ENDC}")
    print("-" * 70)

    if check_directory_exists(
        BASE_DIR / 'core/templates/core/maintenance',
        'Directorio de templates'
    ):
        checks_passed += 1
    else:
        checks_failed += 1

    if check_file_exists(
        BASE_DIR / 'core/templates/core/maintenance/dashboard.html',
        'Template dashboard.html'
    ):
        checks_passed += 1
    else:
        checks_failed += 1

    if check_file_exists(
        BASE_DIR / 'core/templates/core/maintenance/task_detail.html',
        'Template task_detail.html'
    ):
        checks_passed += 1
    else:
        checks_failed += 1

    # 6. VERIFICAR MIGRACIONES
    print(f"\n{Colors.BOLD}6. VERIFICANDO MIGRACIONES{Colors.ENDC}")
    print("-" * 70)

    migration_found = False
    migrations_dir = BASE_DIR / 'core/migrations'
    for file in migrations_dir.glob('*maintenancetask*.py'):
        print_ok(f'Migración encontrada: {file.name}')
        migration_found = True
        checks_passed += 1
        break

    if not migration_found:
        print_fail('NO se encontró migración para MaintenanceTask')
        checks_failed += 1

    # 7. VERIFICAR BACKUPS
    print(f"\n{Colors.BOLD}7. VERIFICANDO SISTEMA DE BACKUPS{Colors.ENDC}")
    print("-" * 70)

    if check_file_exists(
        BASE_DIR / 'backup_database.py',
        'Script backup_database.py'
    ):
        checks_passed += 1
    else:
        checks_failed += 1

    if check_directory_exists(
        BASE_DIR / 'backups',
        'Directorio de backups'
    ):
        checks_passed += 1
        # Contar backups existentes
        backups = list((BASE_DIR / 'backups').glob('db_backup_*.sqlite3'))
        if backups:
            print_info(f'Backups encontrados: {len(backups)}')
            print_info(f'Último backup: {backups[-1].name}')
    else:
        checks_failed += 1

    # 8. VERIFICAR DOCUMENTACIÓN
    print(f"\n{Colors.BOLD}8. VERIFICANDO DOCUMENTACIÓN{Colors.ENDC}")
    print("-" * 70)

    if check_file_exists(
        BASE_DIR / 'SISTEMA_MANTENIMIENTO_WEB.md',
        'Manual de usuario'
    ):
        checks_passed += 1
    else:
        checks_failed += 1

    if check_file_exists(
        BASE_DIR / 'CHECKLIST_SISTEMA_MANTENIMIENTO.md',
        'Checklist de implementación'
    ):
        checks_passed += 1
    else:
        checks_failed += 1

    # 9. VERIFICAR BASE DE DATOS
    print(f"\n{Colors.BOLD}9. VERIFICANDO BASE DE DATOS{Colors.ENDC}")
    print("-" * 70)

    try:
        # Intentar importar Django
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
        django.setup()

        from core.models import MaintenanceTask, CommandLog, SystemHealthCheck

        print_ok('Django configurado correctamente')
        print_ok('Modelos importados correctamente')
        checks_passed += 2

        # Verificar que las tablas existen
        try:
            count_tasks = MaintenanceTask.objects.count()
            count_logs = CommandLog.objects.count()
            count_health = SystemHealthCheck.objects.count()

            print_ok(f'Tabla MaintenanceTask: {count_tasks} registros')
            print_ok(f'Tabla CommandLog: {count_logs} registros')
            print_ok(f'Tabla SystemHealthCheck: {count_health} registros')
            checks_passed += 3

        except Exception as e:
            print_fail(f'Error al consultar tablas: {e}')
            print_warning('Ejecutar: python manage.py migrate')
            checks_failed += 3

    except Exception as e:
        print_fail(f'Error al configurar Django: {e}')
        checks_failed += 5

    # RESUMEN FINAL
    print("\n" + "=" * 70)
    print(f"{Colors.BOLD}RESUMEN DE VERIFICACIÓN{Colors.ENDC}")
    print("=" * 70)

    total_checks = checks_passed + checks_failed
    percentage = (checks_passed / total_checks * 100) if total_checks > 0 else 0

    print(f"\nChecks Exitosos: {Colors.OK}{checks_passed}{Colors.ENDC}")
    print(f"Checks Fallidos: {Colors.FAIL}{checks_failed}{Colors.ENDC}")
    print(f"Total: {total_checks}")
    print(f"Porcentaje: {percentage:.1f}%")

    if checks_failed == 0:
        print(f"\n{Colors.OK}{Colors.BOLD}✓ SISTEMA COMPLETAMENTE FUNCIONAL{Colors.ENDC}")
        print(f"\n{Colors.INFO}Siguiente paso:{Colors.ENDC}")
        print("1. Iniciar servidor: python manage.py runserver")
        print("2. Abrir navegador: http://localhost:8000/core/maintenance/")
        print("3. Login como superusuario")
        print("4. Probar todas las funciones")
        return 0
    else:
        print(f"\n{Colors.WARNING}{Colors.BOLD}⚠ SISTEMA CON PROBLEMAS{Colors.ENDC}")
        print(f"\n{Colors.INFO}Acciones requeridas:{Colors.ENDC}")
        if checks_failed <= 3:
            print("- Revisar archivos faltantes")
            print("- Ejecutar: python manage.py migrate")
        else:
            print("- Revisar implementación completa")
            print("- Consultar CHECKLIST_SISTEMA_MANTENIMIENTO.md")
        return 1

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Verificación interrumpida por el usuario{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{Colors.FAIL}Error inesperado: {e}{Colors.ENDC}")
        sys.exit(1)
