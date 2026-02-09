"""
Script para Backup Automatico de PostgreSQL a almacenamiento S3-compatible (Cloudflare R2 / AWS S3)
Cumple con Clausula 5.2 del contrato: "Copias de seguridad automaticas diarias"

Uso:
1. Programar en cron diario (Render Cron Jobs o GitHub Actions)
2. Retiene backups por 6 meses
3. Comprime antes de subir

Dependencias:
pip install boto3 python-dotenv

Variables de entorno requeridas:
- DATABASE_URL (Render lo proporciona automaticamente)
- AWS_ACCESS_KEY_ID (o R2 Access Key ID)
- AWS_SECRET_ACCESS_KEY (o R2 Secret Access Key)
- AWS_BACKUP_BUCKET (bucket/nombre del bucket en R2)
- AWS_S3_ENDPOINT_URL (endpoint de R2, ej: https://<account_id>.r2.cloudflarestorage.com)
- AWS_S3_REGION_NAME (opcional, default: auto)
"""

import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
import gzip
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseBackupManager:
    """Gestor de backups de PostgreSQL con retencion de 6 meses"""

    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL')
        self.s3_bucket = os.environ.get('AWS_BACKUP_BUCKET', 'sam-metrologia-backups1')
        self.endpoint_url = os.environ.get('AWS_S3_ENDPOINT_URL', '').strip()
        self.is_r2 = 'r2.cloudflarestorage.com' in self.endpoint_url
        self.retention_days = 180  # 6 meses

        # Configurar cliente boto3 compatible con R2 y AWS S3
        client_kwargs = {
            'aws_access_key_id': os.environ.get('AWS_ACCESS_KEY_ID'),
            'aws_secret_access_key': os.environ.get('AWS_SECRET_ACCESS_KEY'),
        }

        if self.endpoint_url:
            client_kwargs['endpoint_url'] = self.endpoint_url
            # R2 requiere region 'auto', AWS usa la region configurada
            client_kwargs['region_name'] = 'auto' if self.is_r2 else os.environ.get('AWS_S3_REGION_NAME', 'us-east-2')
        else:
            client_kwargs['region_name'] = os.environ.get('AWS_S3_REGION_NAME', 'us-east-2')

        self.s3_client = boto3.client('s3', **client_kwargs)

        provider = "Cloudflare R2" if self.is_r2 else "AWS S3"
        logger.info(f"Backup Manager inicializado - Proveedor: {provider}, Bucket: {self.s3_bucket}")

    def create_backup(self):
        """Crea backup de PostgreSQL usando pg_dump"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'sam_backup_{timestamp}.sql'
        compressed_filename = f'{backup_filename}.gz'

        try:
            logger.info(f"Iniciando backup: {backup_filename}")

            # Ejecutar pg_dump con path explicito (usar version 17 si esta disponible)
            pg_dump_cmd = 'pg_dump'
            if subprocess.run(['which', 'pg_dump-17'], capture_output=True).returncode == 0:
                pg_dump_cmd = 'pg_dump-17'
            elif subprocess.run(['test', '-f', '/usr/lib/postgresql/17/bin/pg_dump'], shell=True, capture_output=True).returncode == 0:
                pg_dump_cmd = '/usr/lib/postgresql/17/bin/pg_dump'

            dump_command = f'{pg_dump_cmd} {self.database_url} > {backup_filename}'
            logger.info(f"Usando: {pg_dump_cmd}")
            subprocess.run(dump_command, shell=True, check=True)

            # Comprimir
            with open(backup_filename, 'rb') as f_in:
                with gzip.open(compressed_filename, 'wb') as f_out:
                    f_out.writelines(f_in)

            file_size_mb = os.path.getsize(compressed_filename) / (1024 * 1024)
            logger.info(f"Backup comprimido: {compressed_filename} ({file_size_mb:.2f} MB)")

            # Subir a R2/S3
            self.upload_to_storage(compressed_filename, timestamp)

            # Limpiar archivos locales
            os.remove(backup_filename)
            os.remove(compressed_filename)

            # Limpiar backups antiguos
            self.cleanup_old_backups()

            provider = "R2" if self.is_r2 else "S3"
            logger.info(f"Backup completado exitosamente en {provider}")
            return True

        except Exception as e:
            logger.error(f"Error al crear backup: {e}")
            # Limpiar archivos temporales en caso de error
            for f in [backup_filename, compressed_filename]:
                if os.path.exists(f):
                    os.remove(f)
            return False

    def upload_to_storage(self, filename, timestamp):
        """Sube backup a R2/S3 con metadatos"""
        s3_key = f'backups/database/{datetime.now().year}/{datetime.now().month:02d}/{filename}'

        extra_args = {
            'Metadata': {
                'backup-date': timestamp,
                'retention-days': str(self.retention_days),
                'app': 'sam-metrologia'
            }
        }

        # AWS S3 soporta estos parametros, R2 no
        if not self.is_r2:
            extra_args['ServerSideEncryption'] = 'AES256'
            extra_args['StorageClass'] = 'STANDARD_IA'

        try:
            self.s3_client.upload_file(
                filename,
                self.s3_bucket,
                s3_key,
                ExtraArgs=extra_args
            )
            provider = "R2" if self.is_r2 else "S3"
            logger.info(f"Subido a {provider}: {self.s3_bucket}/{s3_key}")
        except ClientError as e:
            logger.error(f"Error al subir backup: {e}")
            raise

    def cleanup_old_backups(self):
        """Elimina backups con mas de 6 meses (retencion del contrato)"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)

        try:
            # Listar todos los backups (paginar para buckets grandes)
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.s3_bucket,
                Prefix='backups/database/'
            )

            deleted_count = 0
            for page in pages:
                if 'Contents' not in page:
                    continue

                for obj in page['Contents']:
                    if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                        self.s3_client.delete_object(
                            Bucket=self.s3_bucket,
                            Key=obj['Key']
                        )
                        deleted_count += 1
                        logger.info(f"Eliminado backup antiguo: {obj['Key']}")

            logger.info(f"Limpieza completada: {deleted_count} backups eliminados")

        except ClientError as e:
            logger.error(f"Error al limpiar backups antiguos: {e}")

    def list_backups(self):
        """Lista todos los backups disponibles"""
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.s3_bucket,
                Prefix='backups/database/'
            )

            backups = []
            for page in pages:
                if 'Contents' not in page:
                    continue
                for obj in page['Contents']:
                    backups.append({
                        'key': obj['Key'],
                        'size_mb': obj['Size'] / (1024 * 1024),
                        'date': obj['LastModified'],
                    })

            backups.sort(key=lambda x: x['date'], reverse=True)

            logger.info(f"Backups encontrados: {len(backups)}")
            for b in backups[:10]:
                logger.info(f"  {b['key']} ({b['size_mb']:.2f} MB) - {b['date']}")

            return backups

        except ClientError as e:
            logger.error(f"Error al listar backups: {e}")
            return []

    def restore_backup(self, backup_key):
        """Restaura un backup desde R2/S3 (uso manual)"""
        temp_file = 'temp_restore.sql.gz'
        restored_file = 'temp_restore.sql'

        try:
            logger.info(f"Descargando backup: {backup_key}")
            self.s3_client.download_file(self.s3_bucket, backup_key, temp_file)

            # Descomprimir
            with gzip.open(temp_file, 'rb') as f_in:
                with open(restored_file, 'wb') as f_out:
                    f_out.writelines(f_in)

            logger.info("Backup descargado y descomprimido")
            logger.info(f"Para restaurar, ejecute: psql $DATABASE_URL < {restored_file}")

        except Exception as e:
            logger.error(f"Error al restaurar backup: {e}")


def main():
    """Ejecuta backup automatico"""
    manager = DatabaseBackupManager()
    success = manager.create_backup()

    if success:
        exit(0)
    else:
        exit(1)


if __name__ == '__main__':
    main()
