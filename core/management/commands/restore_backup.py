# core/management/commands/restore_backup.py
# Sistema de restauración de backups

from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from core.models import Empresa, Equipo, Calibracion, Mantenimiento, Comprobacion, CustomUser
import json
import os
import zipfile
import tempfile
from datetime import datetime
import logging

logger = logging.getLogger('core')

class Command(BaseCommand):
    help = 'Restaura backups de empresas desde archivos JSON o ZIP'

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_file',
            type=str,
            help='Ruta del archivo de backup (JSON o ZIP)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular restauración sin hacer cambios reales'
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Sobrescribir empresa existente si ya existe'
        )
        parser.add_argument(
            '--restore-files',
            action='store_true',
            help='Restaurar también archivos adjuntos (solo para backups ZIP)'
        )
        parser.add_argument(
            '--new-name',
            type=str,
            help='Nuevo nombre para la empresa restaurada (opcional)'
        )

    def handle(self, *args, **options):
        backup_file = options['backup_file']
        dry_run = options['dry_run']
        overwrite = options['overwrite']
        restore_files = options['restore_files']
        new_name = options['new_name']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('MODO SIMULACION - No se haran cambios reales')
            )

        try:
            # Verificar que el archivo existe
            if not os.path.exists(backup_file):
                self.stdout.write(
                    self.style.ERROR(f'ERROR: Archivo no encontrado: {backup_file}')
                )
                return

            # Determinar tipo de archivo
            if backup_file.endswith('.zip'):
                backup_data = self.load_zip_backup(backup_file)
                can_restore_files = True
            elif backup_file.endswith('.json'):
                backup_data = self.load_json_backup(backup_file)
                can_restore_files = False
            else:
                self.stdout.write(
                    self.style.ERROR('ERROR: Tipo de archivo no soportado. Use .json o .zip')
                )
                return

            if not backup_data:
                self.stdout.write(
                    self.style.ERROR('ERROR: No se pudo cargar el backup')
                )
                return

            # Mostrar información del backup
            metadata = backup_data.get('metadata', {})
            empresa_original = metadata.get('empresa_nombre', 'Desconocida')
            fecha_backup = metadata.get('backup_date', 'Desconocida')

            self.stdout.write(f'INFORMACION DEL BACKUP:')
            self.stdout.write(f'   Empresa: {empresa_original}')
            self.stdout.write(f'   Fecha: {fecha_backup}')
            self.stdout.write(f'   Equipos: {len(backup_data.get("equipos", []))}')
            self.stdout.write(f'   Usuarios: {len(backup_data.get("usuarios", []))}')
            self.stdout.write(f'   Calibraciones: {len(backup_data.get("calibraciones", []))}')
            self.stdout.write(f'   Mantenimientos: {len(backup_data.get("mantenimientos", []))}')
            self.stdout.write(f'   Comprobaciones: {len(backup_data.get("comprobaciones", []))}')

            # Verificar si la empresa ya existe
            empresa_data = backup_data['empresa']['fields']
            empresa_nombre = new_name or empresa_data['nombre']

            existing_empresa = Empresa.objects.filter(nombre=empresa_nombre).first()
            if existing_empresa and not overwrite:
                self.stdout.write(
                    self.style.ERROR(f'ERROR: La empresa "{empresa_nombre}" ya existe. Use --overwrite para reemplazarla.')
                )
                return

            if not dry_run:
                # Realizar restauración
                self.stdout.write(f'[INICIANDO] Restauración de {empresa_nombre}...')

                with transaction.atomic():
                    restored_empresa = self.restore_empresa(
                        backup_data, empresa_nombre, overwrite, restore_files, can_restore_files, backup_file
                    )

                self.stdout.write(
                    self.style.SUCCESS(f'EXITO: Empresa "{restored_empresa.nombre}" restaurada exitosamente')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('SIMULACION: Simulación completada. Use sin --dry-run para restaurar realmente.')
                )

        except Exception as e:
            logger.error(f'Error in restore command: {e}')
            self.stdout.write(
                self.style.ERROR(f'ERROR: Error durante la restauración: {e}')
            )

    def load_json_backup(self, json_file):
        """Carga backup desde archivo JSON."""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f'Error loading JSON backup: {e}')
            return None

    def load_zip_backup(self, zip_file):
        """Carga backup desde archivo ZIP."""
        try:
            with zipfile.ZipFile(zip_file, 'r') as zipf:
                # Leer data.json del ZIP
                data_json = zipf.read('data.json').decode('utf-8')
                return json.loads(data_json)
        except Exception as e:
            logger.error(f'Error loading ZIP backup: {e}')
            return None

    def restore_empresa(self, backup_data, empresa_nombre, overwrite, restore_files, can_restore_files, backup_file):
        """Restaura una empresa completa desde backup."""

        # 1. Crear/actualizar empresa
        empresa_data = backup_data['empresa']['fields']
        empresa_data['nombre'] = empresa_nombre

        if overwrite:
            empresa, created = Empresa.objects.update_or_create(
                nombre=empresa_nombre,
                defaults=empresa_data
            )
            if not created:
                # Limpiar datos existentes
                empresa.equipos.all().delete()
                CustomUser.objects.filter(empresa=empresa).delete()
                self.stdout.write(f'   [LIMPIEZA] Datos existentes eliminados')
        else:
            empresa = Empresa.objects.create(**empresa_data)

        action = "creada" if not overwrite else "actualizada"
        self.stdout.write(f'   [EMPRESA] Empresa {action}')

        # 2. Restaurar usuarios
        for usuario_data in backup_data.get('usuarios', []):
            usuario_fields = usuario_data['fields']
            usuario_fields['empresa'] = empresa

            # Eliminar campos que pueden causar conflictos
            usuario_fields.pop('user_permissions', None)
            usuario_fields.pop('groups', None)

            CustomUser.objects.create(**usuario_fields)

        self.stdout.write(f'   [USUARIOS] {len(backup_data.get("usuarios", []))} usuarios restaurados')

        # 3. Restaurar equipos
        equipos_map = {}  # Para mapear IDs antiguos con nuevos
        for equipo_data in backup_data.get('equipos', []):
            equipo_fields = equipo_data['fields']
            equipo_fields['empresa'] = empresa
            old_id = equipo_data['pk']

            equipo = Equipo.objects.create(**equipo_fields)
            equipos_map[old_id] = equipo

        self.stdout.write(f'   [EQUIPOS] {len(backup_data.get("equipos", []))} equipos restaurados')

        # 4. Restaurar calibraciones
        for cal_data in backup_data.get('calibraciones', []):
            cal_fields = cal_data['fields']
            old_equipo_id = cal_fields.pop('equipo')

            if old_equipo_id in equipos_map:
                cal_fields['equipo'] = equipos_map[old_equipo_id]
                Calibracion.objects.create(**cal_fields)

        self.stdout.write(f'   [CALIBRACIONES] {len(backup_data.get("calibraciones", []))} calibraciones restauradas')

        # 5. Restaurar mantenimientos
        for mant_data in backup_data.get('mantenimientos', []):
            mant_fields = mant_data['fields']
            old_equipo_id = mant_fields.pop('equipo')

            if old_equipo_id in equipos_map:
                mant_fields['equipo'] = equipos_map[old_equipo_id]
                Mantenimiento.objects.create(**mant_fields)

        self.stdout.write(f'   [MANTENIMIENTOS] {len(backup_data.get("mantenimientos", []))} mantenimientos restaurados')

        # 6. Restaurar comprobaciones
        for comp_data in backup_data.get('comprobaciones', []):
            comp_fields = comp_data['fields']
            old_equipo_id = comp_fields.pop('equipo')

            if old_equipo_id in equipos_map:
                comp_fields['equipo'] = equipos_map[old_equipo_id]
                Comprobacion.objects.create(**comp_fields)

        self.stdout.write(f'   [COMPROBACIONES] {len(backup_data.get("comprobaciones", []))} comprobaciones restauradas')

        # 7. Restaurar archivos (solo para ZIP)
        if restore_files and can_restore_files:
            files_restored = self.restore_files_from_zip(backup_file, empresa, equipos_map)
            self.stdout.write(f'   [ARCHIVOS] {files_restored} archivos restaurados')

        return empresa

    def restore_files_from_zip(self, zip_file, empresa, equipos_map):
        """Restaura archivos desde backup ZIP."""
        files_restored = 0

        try:
            with zipfile.ZipFile(zip_file, 'r') as zipf:
                # Buscar archivos en el ZIP
                for file_info in zipf.filelist:
                    if file_info.filename.startswith('files/'):
                        try:
                            file_content = zipf.read(file_info.filename)

                            # Determinar destino del archivo
                            # files/empresa/logo_... -> Logo empresa
                            # files/equipos/CODIGO/field/archivo -> Archivo equipo

                            if 'empresa/logo_' in file_info.filename:
                                # Restaurar logo empresa
                                filename = os.path.basename(file_info.filename)
                                empresa.logo_empresa.save(filename, ContentFile(file_content))
                                files_restored += 1

                            elif 'equipos/' in file_info.filename:
                                # Restaurar archivo de equipo
                                parts = file_info.filename.split('/')
                                if len(parts) >= 4:
                                    codigo_interno = parts[2]
                                    field_name = parts[3]
                                    filename = os.path.basename(file_info.filename)

                                    # Buscar equipo por código interno
                                    equipo = empresa.equipos.filter(codigo_interno=codigo_interno).first()
                                    if equipo and hasattr(equipo, field_name):
                                        field = getattr(equipo, field_name)
                                        if hasattr(field, 'save'):
                                            field.save(filename, ContentFile(file_content))
                                            files_restored += 1

                        except Exception as e:
                            logger.warning(f'Error restoring file {file_info.filename}: {e}')
                            continue

        except Exception as e:
            logger.error(f'Error restoring files: {e}')

        return files_restored