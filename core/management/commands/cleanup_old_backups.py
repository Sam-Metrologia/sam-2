# core/management/commands/cleanup_old_backups.py
# Comando para limpiar backups antiguos de S3 (mayores a 6 meses)

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger('core')


class Command(BaseCommand):
    help = 'Limpia backups de S3 que tengan más de 6 meses de antigüedad'

    def add_arguments(self, parser):
        parser.add_argument(
            '--retention-months',
            type=int,
            default=6,
            help='Número de meses de retención de backups (por defecto 6)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular eliminación sin borrar realmente'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar información detallada'
        )

    def handle(self, *args, **options):
        retention_months = options['retention_months']
        dry_run = options['dry_run']
        verbose = options['verbose']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('MODO SIMULACIÓN - No se eliminarán archivos realmente')
            )

        # Verificar si AWS está configurado
        if not self._check_aws_config():
            self.stdout.write(
                self.style.ERROR('AWS S3 no está configurado. Verificar variables de entorno.')
            )
            return

        self.stdout.write(f'Buscando backups con más de {retention_months} meses...')

        # Calcular fecha límite
        cutoff_date = timezone.now() - timedelta(days=retention_months * 30)

        try:
            deleted_count, total_size_mb = self._cleanup_s3_backups(
                cutoff_date, dry_run, verbose
            )

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'\n[SIMULACIÓN] Se eliminarían {deleted_count} archivos '
                        f'({total_size_mb:.2f} MB)'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✅ Limpieza completada: {deleted_count} archivos eliminados '
                        f'({total_size_mb:.2f} MB liberados)'
                    )
                )

        except Exception as e:
            logger.error(f'Error limpiando backups antiguos: {e}')
            self.stdout.write(
                self.style.ERROR(f'Error al limpiar backups: {e}')
            )

    def _check_aws_config(self):
        """Verifica que AWS S3 esté configurado."""
        return all([
            settings.AWS_ACCESS_KEY_ID,
            settings.AWS_SECRET_ACCESS_KEY,
            settings.AWS_STORAGE_BUCKET_NAME
        ])

    def _cleanup_s3_backups(self, cutoff_date, dry_run=False, verbose=False):
        """
        Elimina backups de S3 anteriores a cutoff_date.

        Returns:
            (deleted_count, total_size_mb): Tupla con número de archivos y tamaño total
        """
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            raise ImportError(
                'boto3 no está instalado. Ejecutar: pip install boto3'
            )

        # Conectar a S3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-2')
        )

        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        backup_prefix = 'backups/'

        deleted_count = 0
        total_size = 0

        try:
            # Listar objetos en el bucket con prefijo 'backups/'
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket_name, Prefix=backup_prefix)

            for page in pages:
                if 'Contents' not in page:
                    continue

                for obj in page['Contents']:
                    file_key = obj['Key']
                    file_size = obj['Size']
                    last_modified = obj['LastModified']

                    # Verificar si el archivo es más antiguo que cutoff_date
                    if last_modified < cutoff_date.replace(tzinfo=last_modified.tzinfo):
                        deleted_count += 1
                        total_size += file_size

                        if verbose:
                            age_days = (timezone.now() - last_modified).days
                            size_mb = file_size / (1024 * 1024)
                            self.stdout.write(
                                f'  {"[SIMULAR]" if dry_run else "[ELIMINAR]"} {file_key} '
                                f'({size_mb:.2f} MB, {age_days} días)'
                            )

                        # Eliminar archivo (si no es dry-run)
                        if not dry_run:
                            s3_client.delete_object(Bucket=bucket_name, Key=file_key)
                            logger.info(f'Backup eliminado de S3: {file_key}')

            total_size_mb = total_size / (1024 * 1024)
            return deleted_count, total_size_mb

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                raise Exception(f'Bucket S3 no existe: {bucket_name}')
            elif error_code == 'AccessDenied':
                raise Exception(
                    'Acceso denegado a S3. Verificar permisos del usuario IAM.'
                )
            else:
                raise Exception(f'Error de S3: {e}')
