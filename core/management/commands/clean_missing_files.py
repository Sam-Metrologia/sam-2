# core/management/commands/clean_missing_files.py

from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from core.models import Equipo, Empresa, BajaEquipo, Calibracion, Mantenimiento, Comprobacion
from django.db import models
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Limpia referencias a archivos que no existen en el storage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué se limpiaría, sin hacer cambios',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY RUN - No se harán cambios'))

        models_to_check = [
            (Equipo, ['imagen_equipo', 'manual_pdf', 'archivo_compra_pdf', 'ficha_tecnica_pdf', 'otros_documentos_pdf']),
            (Empresa, ['logo_empresa']),
            (BajaEquipo, ['documento_baja']),
            (Calibracion, ['documento_calibracion', 'confirmacion_metrologica_pdf', 'intervalos_calibracion_pdf']),
            (Mantenimiento, ['documento_mantenimiento']),
            (Comprobacion, ['documento_comprobacion']),
        ]

        total_cleaned = 0

        for model_class, file_fields in models_to_check:
            self.stdout.write(f'\nVerificando {model_class.__name__}...')

            for field_name in file_fields:
                # Obtener objetos que tienen archivo en este campo
                field_lookup = f'{field_name}__isnull'
                objects_with_files = model_class.objects.exclude(**{field_lookup: True}).exclude(**{field_name: ''})

                for obj in objects_with_files:
                    file_field = getattr(obj, field_name)
                    if file_field and file_field.name:
                        try:
                            # Verificar si el archivo existe en el storage
                            if not default_storage.exists(file_field.name):
                                self.stdout.write(
                                    self.style.WARNING(
                                        f'Archivo faltante: {model_class.__name__}#{obj.pk}.{field_name} -> {file_field.name}'
                                    )
                                )

                                if not dry_run:
                                    # Limpiar la referencia al archivo
                                    setattr(obj, field_name, None)
                                    obj.save(update_fields=[field_name])
                                    total_cleaned += 1

                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(
                                    f'Error verificando {file_field.name}: {str(e)}'
                                )
                            )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'DRY RUN completado. {total_cleaned} referencias se limpiarían.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Limpieza completada. {total_cleaned} referencias fueron limpiadas.')
            )