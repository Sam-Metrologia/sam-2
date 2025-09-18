#!/usr/bin/env python
"""
Script de configuración para SAM Metrología
Ejecutar después de aplicar las migraciones para configurar el entorno
"""

import os
import sys
import django
from django.core.management import execute_from_command_line
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()


class Command(BaseCommand):
    help = 'Configura el entorno de SAM Metrología después de la instalación'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-cache',
            action='store_true',
            help='Omitir configuración de cache',
        )
        parser.add_argument(
            '--skip-indexes',
            action='store_true', 
            help='Omitir verificación de índices',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Configurando SAM Metrología...')
        )

        # 1. Crear tabla de cache si se usa DatabaseCache
        if not options['skip_cache']:
            self.setup_cache()

        # 2. Verificar índices críticos
        if not options['skip_indexes']:
            self.verify_indexes()

        # 3. Crear directorios necesarios
        self.create_directories()

        # 4. Verificar configuración de archivos
        self.verify_file_config()

        # 5. Crear superusuario si no existe
        self.setup_superuser()

        self.stdout.write(
            self.style.SUCCESS('✅ Configuración completada exitosamente!')
        )

    def setup_cache(self):
        """Configurar cache de base de datos si es necesario"""
        self.stdout.write('📦 Configurando cache...')
        
        try:
            # Verificar si se usa cache de base de datos
            cache_backend = settings.CACHES['default']['BACKEND']
            
            if 'DatabaseCache' in cache_backend:
                self.stdout.write('   Creando tabla de cache...')
                execute_from_command_line([
                    'manage.py', 'createcachetable', 
                    settings.CACHES['default']['LOCATION']
                ])
                self.stdout.write('   ✓ Tabla de cache creada')
            
            # Probar conexión de cache
            cache.set('test_key', 'test_value', 30)
            if cache.get('test_key') == 'test_value':
                cache.delete('test_key')
                self.stdout.write('   ✓ Cache funcionando correctamente')
            else:
                self.stdout.write(
                    self.style.WARNING('   ⚠ Cache no está funcionando correctamente')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'   ❌ Error configurando cache: {str(e)}')
            )

    def verify_indexes(self):
        """Verificar que los índices críticos existen"""
        self.stdout.write('🔍 Verificando índices de base de datos...')
        
        try:
            from django.db import connection
            
            critical_indexes = [
                'idx_equipo_empresa_estado',
                'idx_equipo_proxima_calibracion', 
                'idx_calibracion_fecha',
                'idx_mantenimiento_fecha',
                'idx_comprobacion_fecha'
            ]
            
            with connection.cursor() as cursor:
                # Para PostgreSQL
                if 'postgresql' in settings.DATABASES['default']['ENGINE']:
                    cursor.execute("""
                        SELECT indexname FROM pg_indexes 
                        WHERE tablename LIKE 'core_%'
                    """)
                # Para SQLite
                elif 'sqlite' in settings.DATABASES['default']['ENGINE']:
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='index' AND name LIKE 'idx_%'
                    """)
                else:
                    self.stdout.write('   ⚠ Tipo de base de datos no soportado para verificación de índices')
                    return
                
                existing_indexes = [row[0] for row in cursor.fetchall()]
                
                for index in critical_indexes:
                    if index in existing_indexes:
                        self.stdout.write(f'   ✓ {index}')
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'   ⚠ Índice faltante: {index}')
                        )
                        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'   ❌ Error verificando índices: {str(e)}')
            )

    def create_directories(self):
        """Crear directorios necesarios"""
        self.stdout.write('📁 Creando directorios...')
        
        directories = [
            settings.BASE_DIR / 'logs',
            settings.BASE_DIR / 'media',
            settings.BASE_DIR / 'staticfiles',
        ]
        
        # Solo crear directorio media si no se usa S3
        if not hasattr(settings, 'AWS_STORAGE_BUCKET_NAME') or not settings.AWS_STORAGE_BUCKET_NAME:
            directories.append(settings.BASE_DIR / 'media' / 'pdfs')
            directories.append(settings.BASE_DIR / 'media' / 'imagenes_equipos')
            directories.append(settings.BASE_DIR / 'media' / 'empresas_logos')
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                self.stdout.write(f'   ✓ {directory}')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'   ❌ Error creando {directory}: {str(e)}')
                )

    def verify_file_config(self):
        """Verificar configuración de archivos"""
        self.stdout.write('📄 Verificando configuración de archivos...')
        
        # Verificar configuración S3 si está habilitada
        if hasattr(settings, 'AWS_STORAGE_BUCKET_NAME') and settings.AWS_STORAGE_BUCKET_NAME:
            required_aws_settings = [
                'AWS_ACCESS_KEY_ID',
                'AWS_SECRET_ACCESS_KEY', 
                'AWS_STORAGE_BUCKET_NAME',
                'AWS_S3_REGION_NAME'
            ]
            
            missing_settings = []
            for setting in required_aws_settings:
                if not hasattr(settings, setting) or not getattr(settings, setting):
                    missing_settings.append(setting)
            
            if missing_settings:
                self.stdout.write(
                    self.style.ERROR(f'   ❌ Configuración S3 incompleta: {missing_settings}')
                )
            else:
                self.stdout.write('   ✓ Configuración S3 completa')
        else:
            self.stdout.write('   ✓ Usando almacenamiento local')
        
        # Verificar límites de archivos
        limits = getattr(settings, 'SAM_CONFIG', {})
        max_size = limits.get('MAX_FILE_SIZE_MB', 10)
        self.stdout.write(f'   ✓ Límite máximo de archivos: {max_size}MB')

    def setup_superuser(self):
        """Crear superusuario inicial si no existe"""
        self.stdout.write('👤 Verificando superusuario...')
        
        try:
            from core.models import CustomUser
            
            if not CustomUser.objects.filter(is_superuser=True).exists():
                self.stdout.write(
                    self.style.WARNING('   ⚠ No hay superusuarios. Creando usuario admin por defecto...')
                )
                
                # Crear superusuario por defecto
                admin_user = CustomUser.objects.create_superuser(
                    username='admin',
                    email='admin@sammetrologia.com',
                    password='admin123',  # Cambiar en producción
                    first_name='Administrador',
                    last_name='Sistema'
                )
                
                self.stdout.write(
                    self.style.SUCCESS('   ✓ Usuario admin creado (username: admin, password: admin123)')
                )
                self.stdout.write(
                    self.style.WARNING('   ⚠ IMPORTANTE: Cambiar contraseña en producción')
                )
            else:
                superusers_count = CustomUser.objects.filter(is_superuser=True).count()
                self.stdout.write(f'   ✓ {superusers_count} superusuario(s) encontrado(s)')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'   ❌ Error configurando superusuario: {str(e)}')
            )


def main():
    """Función principal para ejecutar desde línea de comandos"""
    if __name__ == '__main__':
        # Ejecutar como comando de Django
        execute_from_command_line(['manage.py', 'setup_sam'] + sys.argv[1:])


# Script ejecutable independiente
if __name__ == '__main__':
    print("🚀 Configurando SAM Metrología...")
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists('manage.py'):
        print("❌ Error: Este script debe ejecutarse desde el directorio raíz del proyecto Django")
        sys.exit(1)
    
    # Ejecutar migraciones primero
    print("📦 Aplicando migraciones...")
    os.system('python manage.py migrate')
    
    # Ejecutar recolección de archivos estáticos
    print("📦 Recolectando archivos estáticos...")
    os.system('python manage.py collectstatic --noinput')
    
    # Ejecutar nuestro comando personalizado
    main()