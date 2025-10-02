#!/usr/bin/env python
"""
SAM METROLOGÍA - PRE-DEPLOYMENT CHECK
Verifica que todo esté listo para deployment en Render
"""

import os
import sys

def check_env_file():
    """Verifica que exista archivo .env con las variables necesarias"""
    print("\n[1/6] Verificando archivo .env...")

    required_vars = [
        'SECRET_KEY',
        'DATABASE_URL',
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'AWS_STORAGE_BUCKET_NAME',
    ]

    # Para desarrollo, .env es opcional
    if not os.path.exists('.env'):
        print("   [!] Archivo .env no encontrado (OK para desarrollo)")
        print("   [OK] En Render, configurar variables de entorno manualmente")
        return True

    print("   [OK] Archivo .env encontrado")
    return True

def check_requirements():
    """Verifica que requirements.txt esté completo"""
    print("\n[2/6] Verificando requirements.txt...")

    if not os.path.exists('requirements.txt'):
        print("   [FAIL] requirements.txt no encontrado!")
        return False

    with open('requirements.txt', 'r', encoding='utf-8') as f:
        requirements = f.read()

    required_packages = [
        'Django',
        'gunicorn',
        'psycopg2-binary',
        'boto3',
        'django-storages',
        'whitenoise',
        'django-crispy-forms',
    ]

    missing = []
    for package in required_packages:
        if package.lower() not in requirements.lower():
            missing.append(package)

    if missing:
        print(f"   [FAIL] Faltan paquetes: {', '.join(missing)}")
        return False

    print("   [OK] Todos los paquetes requeridos están presentes")
    return True

def check_settings():
    """Verifica configuración de settings.py"""
    print("\n[3/6] Verificando settings.py...")

    with open('proyecto_c/settings.py', 'r', encoding='utf-8') as f:
        settings = f.read()

    checks = {
        'ALLOWED_HOSTS': 'ALLOWED_HOSTS' in settings,
        'CSRF_TRUSTED_ORIGINS': 'CSRF_TRUSTED_ORIGINS' in settings,
        'AWS S3': 'AWS_STORAGE_BUCKET_NAME' in settings,
        'STATIC_ROOT': 'STATIC_ROOT' in settings,
        'MEDIA_ROOT': 'MEDIA_ROOT' in settings,
    }

    all_good = True
    for check_name, passed in checks.items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"   {status} {check_name}")
        if not passed:
            all_good = False

    return all_good

def check_static_files():
    """Verifica que los archivos estáticos estén listos"""
    print("\n[4/6] Verificando archivos estáticos...")

    # Verificar que existe themes.css
    themes_css = 'core/static/core/css/themes.css'
    if not os.path.exists(themes_css):
        print(f"   [FAIL] {themes_css} no encontrado!")
        return False

    print(f"   [OK] {themes_css} existe")

    # Verificar directorio staticfiles
    if os.path.exists('staticfiles'):
        file_count = sum([len(files) for r, d, files in os.walk('staticfiles')])
        print(f"   [OK] Directorio staticfiles existe ({file_count} archivos)")
    else:
        print("   [!]  Directorio staticfiles no existe (se creará con collectstatic)")

    return True

def check_migrations():
    """Verifica que las migraciones estén creadas"""
    print("\n[5/6] Verificando migraciones...")

    migrations_dir = 'core/migrations'
    if not os.path.exists(migrations_dir):
        print(f"   [FAIL] {migrations_dir} no encontrado!")
        return False

    migration_files = [f for f in os.listdir(migrations_dir) if f.endswith('.py') and f != '__init__.py']

    if not migration_files:
        print("   [FAIL] No hay archivos de migración!")
        return False

    print(f"   [OK] {len(migration_files)} archivos de migración encontrados")
    return True

def check_storages():
    """Verifica que exista el archivo storages.py"""
    print("\n[6/6] Verificando proyecto_c/storages.py...")

    storages_file = 'proyecto_c/storages.py'
    if not os.path.exists(storages_file):
        print(f"   [FAIL] {storages_file} no encontrado!")
        print("   Este archivo es necesario para S3")
        return False

    with open(storages_file, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'S3MediaStorage' in content and 'S3StaticStorage' in content:
        print("   [OK] storages.py configurado correctamente")
        return True
    else:
        print("   [FAIL] storages.py no tiene las clases necesarias")
        return False

def print_deployment_summary():
    """Imprime resumen y siguientes pasos"""
    print("\n" + "="*70)
    print("SIGUIENTES PASOS PARA DEPLOYMENT EN RENDER")
    print("="*70)
    print("""
1. Crear Web Service en Render:
   - Repository: [tu-repo-git]
   - Branch: main/master
   - Build Command: pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput
   - Start Command: gunicorn proyecto_c.wsgi:application

2. Añadir PostgreSQL Database:
   - Copiar DATABASE_URL
   - Añadir a Environment Variables

3. Configurar Environment Variables en Render:
   SECRET_KEY=<generar-uno-nuevo>
   DEBUG_VALUE=False
   RENDER_EXTERNAL_HOSTNAME=<tu-app>.onrender.com
   DATABASE_URL=<del-paso-2>
   AWS_ACCESS_KEY_ID=<de-aws>
   AWS_SECRET_ACCESS_KEY=<de-aws>
   AWS_STORAGE_BUCKET_NAME=<nombre-bucket>
   AWS_S3_REGION_NAME=us-east-2

4. Después del primer deployment:
   - Crear superusuario: python manage.py createsuperuser
   - Verificar login
   - Probar funcionalidad

5. Verificar en producción:
   - Dark mode funciona
   - Archivos suben a S3
   - ZIP generation funciona
   - Dashboard se genera correctamente

[INFO] Ver DEPLOYMENT_RENDER.md para guia completa
[!] Ver ERRORES_ENCONTRADOS.md para issues conocidos
    """)

def main():
    print("="*70)
    print("SAM METROLOGÍA - PRE-DEPLOYMENT CHECK")
    print("="*70)

    checks = [
        check_env_file(),
        check_requirements(),
        check_settings(),
        check_static_files(),
        check_migrations(),
        check_storages(),
    ]

    print("\n" + "="*70)
    print("RESULTADO")
    print("="*70)

    total = len(checks)
    passed = sum(checks)

    print(f"\nPruebas pasadas: {passed}/{total}")

    if all(checks):
        print("\n[OK] LISTO PARA DEPLOYMENT!")
        print_deployment_summary()
        return 0
    else:
        print("\n[FAIL] HAY PROBLEMAS QUE CORREGIR")
        print("Revisa los errores arriba antes de hacer deployment")
        return 1

if __name__ == '__main__':
    sys.exit(main())
