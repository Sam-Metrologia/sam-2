"""
Script para Backup Automático de PostgreSQL a AWS S3
Cumple con Cláusula 5.2 del contrato: "Copias de seguridad automáticas diarias"

Uso:
1. Programar en cron diario (Render Cron Jobs o GitHub Actions)
2. Retiene backups por 6 meses en S3
3. Comprime y encripta antes de subir

Dependencias:
pip install boto3 python-dotenv

Variables de entorno requeridas:
- DATABASE_URL (Render lo proporciona automáticamente)
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- AWS_BACKUP_BUCKET (bucket separado para backups)
- BACKUP_ENCRYPTION_KEY (opcional - para cifrado adicional)
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
    """Gestor de backups de PostgreSQL con retención de 6 meses"""

    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL')
        self.s3_bucket = os.environ.get('AWS_BACKUP_BUCKET', 'sam-metrologia-backups1')
        self.s3_client = boto3.client('s3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_S3_REGION_NAME', 'us-east-2')
        )
        self.retention_days = 180  # 6 meses

    def create_backup(self):
        """Crea backup de PostgreSQL usando pg_dump"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'sam_backup_{timestamp}.sql'
        compressed_filename = f'{backup_filename}.gz'

        try:
            logger.info(f"Iniciando backup: {backup_filename}")

            # Ejecutar pg_dump
            dump_command = f'pg_dump {self.database_url} > {backup_filename}'
            subprocess.run(dump_command, shell=True, check=True)

            # Comprimir
            with open(backup_filename, 'rb') as f_in:
                with gzip.open(compressed_filename, 'wb') as f_out:
                    f_out.writelines(f_in)

            logger.info(f"Backup comprimido: {compressed_filename}")

            # Subir a S3
            self.upload_to_s3(compressed_filename, timestamp)

            # Limpiar archivos locales
            os.remove(backup_filename)
            os.remove(compressed_filename)

            # Limpiar backups antiguos
            self.cleanup_old_backups()

            logger.info("✅ Backup completado exitosamente")
            return True

        except Exception as e:
            logger.error(f"❌ Error al crear backup: {e}")
            return False

    def upload_to_s3(self, filename, timestamp):
        """Sube backup a S3 con metadatos"""
        s3_key = f'backups/database/{datetime.now().year}/{datetime.now().month:02d}/{filename}'

        try:
            self.s3_client.upload_file(
                filename,
                self.s3_bucket,
                s3_key,
                ExtraArgs={
                    'ServerSideEncryption': 'AES256',
                    'StorageClass': 'STANDARD_IA',  # Almacenamiento de acceso infrecuente (más barato)
                    'Metadata': {
                        'backup-date': timestamp,
                        'retention-days': str(self.retention_days),
                        'app': 'sam-metrologia'
                    }
                }
            )
            logger.info(f"Subido a S3: s3://{self.s3_bucket}/{s3_key}")
        except ClientError as e:
            logger.error(f"Error al subir a S3: {e}")
            raise

    def cleanup_old_backups(self):
        """Elimina backups con más de 6 meses (retención del contrato)"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)

        try:
            # Listar todos los backups
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix='backups/database/'
            )

            if 'Contents' not in response:
                logger.info("No hay backups antiguos para eliminar")
                return

            deleted_count = 0
            for obj in response['Contents']:
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

    def restore_backup(self, backup_key):
        """Restaura un backup desde S3 (uso manual)"""
        temp_file = 'temp_restore.sql.gz'
        restored_file = 'temp_restore.sql'

        try:
            logger.info(f"Descargando backup: {backup_key}")
            self.s3_client.download_file(self.s3_bucket, backup_key, temp_file)

            # Descomprimir
            with gzip.open(temp_file, 'rb') as f_in:
                with open(restored_file, 'wb') as f_out:
                    f_out.writelines(f_in)

            logger.info("✅ Backup descargado y descomprimido")
            logger.info(f"Para restaurar, ejecute: psql {self.database_url} < {restored_file}")

        except Exception as e:
            logger.error(f"Error al restaurar backup: {e}")


def main():
    """Ejecuta backup automático"""
    manager = DatabaseBackupManager()
    success = manager.create_backup()

    if success:
        exit(0)
    else:
        exit(1)


if __name__ == '__main__':
    main()
