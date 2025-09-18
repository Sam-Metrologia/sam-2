# proyecto_c/storages.py
# Configuración personalizada de almacenamiento para AWS S3

from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings
import logging

logger = logging.getLogger('core')

class S3MediaStorage(S3Boto3Storage):
    """
    Storage personalizado para archivos media en S3
    """
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    location = settings.AWS_LOCATION if hasattr(settings, 'AWS_LOCATION') else 'media'
    default_acl = 'private'  # Archivos privados por defecto
    file_overwrite = False
    custom_domain = False  # Usar URLs firmadas en lugar del dominio personalizado

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info(f"S3MediaStorage initialized with bucket: {self.bucket_name}, location: {self.location}")

    def url(self, name, parameters=None, expire=3600, http_method=None):
        """
        Genera URLs firmadas para acceso seguro a archivos privados
        """
        try:
            # Para archivos privados, generar URL firmada
            url = self.connection.meta.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': name},
                ExpiresIn=expire
            )
            logger.debug(f"Generated presigned URL for {name}: {url[:50]}...")
            return url
        except Exception as e:
            logger.error(f"Error generating presigned URL for {name}: {str(e)}")
            # Fallback al método padre
            return super().url(name, parameters, expire, http_method)


class S3StaticStorage(S3Boto3Storage):
    """
    Storage personalizado para archivos estáticos en S3
    """
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    location = settings.AWS_STATIC_LOCATION if hasattr(settings, 'AWS_STATIC_LOCATION') else 'static'
    default_acl = 'public-read'  # Archivos estáticos públicos
    file_overwrite = True
    querystring_auth = False
    custom_domain = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None)