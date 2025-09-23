# core/management/commands/backup_data.py
# Sistema de backup completo de datos

from django.core.management.base import BaseCommand
from django.core import serializers
from django.conf import settings
from django.utils import timezone
from django.core.files.storage import default_storage
from core.models import Empresa, Equipo, Calibracion, Mantenimiento, Comprobacion, CustomUser
import json
import os
import zipfile
import tempfile
from datetime import datetime
import logging

logger = logging.getLogger('core')

class Command(BaseCommand):
    help = 'Crea backups completos de datos de empresas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='ID específico de empresa para backup (por defecto: todas)'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'zip', 'both'],
            default='both',
            help='Formato de backup'
        )
        parser.add_argument(
            '--include-files',
            action='store_true',
            help='Incluir archivos adjuntos en el backup'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='backups',
            help='Directorio de salida para backups'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar información detallada'
        )

    def handle(self, *args, **options):
        empresa_id = options.get('empresa_id')
        backup_format = options['format']
        include_files = options['include_files']
        output_dir = options['output_dir']
        verbose = options['verbose']

        # Crear directorio de backup
        backup_path = os.path.join(settings.BASE_DIR, output_dir)
        os.makedirs(backup_path, exist_ok=True)

        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')

        try:
            if empresa_id:
                # Backup de empresa específica
                empresa = Empresa.objects.get(id=empresa_id)
                self.backup_empresa(empresa, backup_path, timestamp, backup_format, include_files, verbose)
            else:
                # Backup de todas las empresas
                empresas = Empresa.objects.all()
                self.stdout.write(f'📦 Iniciando backup de {empresas.count()} empresas...')

                for empresa in empresas:
                    self.backup_empresa(empresa, backup_path, timestamp, backup_format, include_files, verbose)

            self.stdout.write(
                self.style.SUCCESS(f'✅ Backup completado en: {backup_path}')
            )

        except Exception as e:
            logger.error(f'Error in backup command: {e}')
            self.stdout.write(
                self.style.ERROR(f'❌ Error durante backup: {e}')
            )

    def backup_empresa(self, empresa, backup_path, timestamp, backup_format, include_files, verbose):
        """Crea backup completo de una empresa."""
        if verbose:
            self.stdout.write(f'   📊 Procesando: {empresa.nombre}')

        try:
            # Preparar datos para serialización
            backup_data = self.gather_empresa_data(empresa, verbose)

            # Crear nombre de archivo
            safe_name = "".join(c for c in empresa.nombre if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_name = safe_name.replace(' ', '_')

            if backup_format in ['json', 'both']:
                json_filename = f'backup_{safe_name}_{timestamp}.json'
                json_path = os.path.join(backup_path, json_filename)
                self.create_json_backup(backup_data, json_path, verbose)

            if backup_format in ['zip', 'both']:
                zip_filename = f'backup_{safe_name}_{timestamp}.zip'
                zip_path = os.path.join(backup_path, zip_filename)
                self.create_zip_backup(empresa, backup_data, zip_path, include_files, verbose)

            if verbose:
                self.stdout.write(f'   ✅ Backup completado para: {empresa.nombre}')

        except Exception as e:
            logger.error(f'Error backing up empresa {empresa.nombre}: {e}')
            self.stdout.write(
                self.style.ERROR(f'   ❌ Error en backup de {empresa.nombre}: {e}')
            )

    def gather_empresa_data(self, empresa, verbose=False):
        """Recopila todos los datos de una empresa."""
        data = {
            'metadata': {
                'empresa_id': empresa.id,
                'empresa_nombre': empresa.nombre,
                'backup_date': timezone.now().isoformat(),
                'version': '1.0'
            },
            'empresa': {},
            'usuarios': [],
            'equipos': [],
            'calibraciones': [],
            'mantenimientos': [],
            'comprobaciones': []
        }

        try:
            # Datos de la empresa
            empresa_data = serializers.serialize('json', [empresa])
            data['empresa'] = json.loads(empresa_data)[0]

            # Usuarios de la empresa
            usuarios = CustomUser.objects.filter(empresa=empresa)
            if usuarios.exists():
                usuarios_data = serializers.serialize('json', usuarios)
                data['usuarios'] = json.loads(usuarios_data)

            # Equipos de la empresa
            equipos = empresa.equipos.all()
            if equipos.exists():
                equipos_data = serializers.serialize('json', equipos)
                data['equipos'] = json.loads(equipos_data)

                # Actividades de cada equipo
                for equipo in equipos:
                    # Calibraciones
                    calibraciones = equipo.calibraciones.all()
                    if calibraciones.exists():
                        cal_data = serializers.serialize('json', calibraciones)
                        data['calibraciones'].extend(json.loads(cal_data))

                    # Mantenimientos
                    mantenimientos = equipo.mantenimientos.all()
                    if mantenimientos.exists():
                        mant_data = serializers.serialize('json', mantenimientos)
                        data['mantenimientos'].extend(json.loads(mant_data))

                    # Comprobaciones
                    comprobaciones = equipo.comprobaciones.all()
                    if comprobaciones.exists():
                        comp_data = serializers.serialize('json', comprobaciones)
                        data['comprobaciones'].extend(json.loads(comp_data))

            if verbose:
                self.stdout.write(
                    f'     - Equipos: {len(data["equipos"])}, '
                    f'Calibraciones: {len(data["calibraciones"])}, '
                    f'Mantenimientos: {len(data["mantenimientos"])}, '
                    f'Comprobaciones: {len(data["comprobaciones"])}'
                )

            return data

        except Exception as e:
            logger.error(f'Error gathering data for {empresa.nombre}: {e}')
            raise

    def create_json_backup(self, backup_data, json_path, verbose=False):
        """Crea backup en formato JSON."""
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)

            if verbose:
                self.stdout.write(f'     ✅ JSON backup: {os.path.basename(json_path)}')

        except Exception as e:
            logger.error(f'Error creating JSON backup: {e}')
            raise

    def create_zip_backup(self, empresa, backup_data, zip_path, include_files, verbose=False):
        """Crea backup completo en formato ZIP."""
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Añadir datos JSON
                json_data = json.dumps(backup_data, ensure_ascii=False, indent=2)
                zipf.writestr('data.json', json_data.encode('utf-8'))

                # Añadir archivos si se solicita
                if include_files:
                    files_added = self.add_files_to_zip(empresa, zipf, verbose)
                    if verbose and files_added > 0:
                        self.stdout.write(f'     📁 Archivos incluidos: {files_added}')

                # Añadir información del backup
                info = {
                    'empresa': empresa.nombre,
                    'fecha_backup': timezone.now().isoformat(),
                    'incluye_archivos': include_files,
                    'version': '1.0'
                }
                zipf.writestr('backup_info.json', json.dumps(info, ensure_ascii=False, indent=2))

            if verbose:
                self.stdout.write(f'     ✅ ZIP backup: {os.path.basename(zip_path)}')

        except Exception as e:
            logger.error(f'Error creating ZIP backup: {e}')
            raise

    def add_files_to_zip(self, empresa, zipf, verbose=False):
        """Añade archivos de la empresa al ZIP."""
        files_added = 0

        try:
            # Logo de empresa
            if empresa.logo_empresa and hasattr(empresa.logo_empresa, 'name'):
                if default_storage.exists(empresa.logo_empresa.name):
                    try:
                        file_content = default_storage.open(empresa.logo_empresa.name).read()
                        zipf.writestr(f'files/empresa/logo_{empresa.logo_empresa.name}', file_content)
                        files_added += 1
                    except Exception:
                        pass

            # Archivos de equipos
            for equipo in empresa.equipos.all():
                files_added += self.add_equipo_files_to_zip(equipo, zipf)

            return files_added

        except Exception as e:
            logger.error(f'Error adding files to ZIP: {e}')
            return files_added

    def add_equipo_files_to_zip(self, equipo, zipf):
        """Añade archivos de un equipo específico al ZIP."""
        files_added = 0

        try:
            # Archivos principales del equipo
            file_fields = [
                'archivo_compra_pdf', 'ficha_tecnica_pdf', 'manual_pdf',
                'otros_documentos_pdf', 'imagen_equipo'
            ]

            for field_name in file_fields:
                file_field = getattr(equipo, field_name, None)
                if file_field and hasattr(file_field, 'name'):
                    if default_storage.exists(file_field.name):
                        try:
                            file_content = default_storage.open(file_field.name).read()
                            safe_filename = os.path.basename(file_field.name)
                            zipf.writestr(
                                f'files/equipos/{equipo.codigo_interno}/{field_name}/{safe_filename}',
                                file_content
                            )
                            files_added += 1
                        except Exception:
                            pass

            # Archivos de calibraciones
            for calibracion in equipo.calibraciones.all():
                cal_fields = ['documento_calibracion', 'confirmacion_metrologica_pdf', 'intervalos_calibracion_pdf']
                for field_name in cal_fields:
                    file_field = getattr(calibracion, field_name, None)
                    if file_field and hasattr(file_field, 'name'):
                        if default_storage.exists(file_field.name):
                            try:
                                file_content = default_storage.open(file_field.name).read()
                                safe_filename = os.path.basename(file_field.name)
                                zipf.writestr(
                                    f'files/equipos/{equipo.codigo_interno}/calibraciones/{calibracion.id}/{safe_filename}',
                                    file_content
                                )
                                files_added += 1
                            except Exception:
                                pass

            # Archivos de mantenimientos
            for mantenimiento in equipo.mantenimientos.all():
                if mantenimiento.documento_mantenimiento and hasattr(mantenimiento.documento_mantenimiento, 'name'):
                    if default_storage.exists(mantenimiento.documento_mantenimiento.name):
                        try:
                            file_content = default_storage.open(mantenimiento.documento_mantenimiento.name).read()
                            safe_filename = os.path.basename(mantenimiento.documento_mantenimiento.name)
                            zipf.writestr(
                                f'files/equipos/{equipo.codigo_interno}/mantenimientos/{mantenimiento.id}/{safe_filename}',
                                file_content
                            )
                            files_added += 1
                        except Exception:
                            pass

            # Archivos de comprobaciones
            for comprobacion in equipo.comprobaciones.all():
                if comprobacion.documento_comprobacion and hasattr(comprobacion.documento_comprobacion, 'name'):
                    if default_storage.exists(comprobacion.documento_comprobacion.name):
                        try:
                            file_content = default_storage.open(comprobacion.documento_comprobacion.name).read()
                            safe_filename = os.path.basename(comprobacion.documento_comprobacion.name)
                            zipf.writestr(
                                f'files/equipos/{equipo.codigo_interno}/comprobaciones/{comprobacion.id}/{safe_filename}',
                                file_content
                            )
                            files_added += 1
                        except Exception:
                            pass

            return files_added

        except Exception as e:
            logger.error(f'Error adding equipo files to ZIP: {e}')
            return files_added