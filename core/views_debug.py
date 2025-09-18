# Vistas de diagnóstico temporal para debugging de archivos S3
import os
import boto3
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.core.files.storage import default_storage
import logging

logger = logging.getLogger('core')

@staff_member_required
def s3_diagnostics(request):
    """
    Vista de diagnóstico para verificar configuración S3 y subida de archivos
    """
    diagnostics = {}

    # 1. Verificar variables de entorno
    diagnostics['aws_vars'] = {
        'AWS_ACCESS_KEY_ID': bool(os.environ.get('AWS_ACCESS_KEY_ID')),
        'AWS_SECRET_ACCESS_KEY': bool(os.environ.get('AWS_SECRET_ACCESS_KEY')),
        'AWS_STORAGE_BUCKET_NAME': os.environ.get('AWS_STORAGE_BUCKET_NAME'),
        'AWS_S3_REGION_NAME': os.environ.get('AWS_S3_REGION_NAME'),
    }

    # 2. Verificar configuración de storage
    diagnostics['storage_info'] = {
        'storage_class': default_storage.__class__.__name__,
        'is_s3': 'S3' in default_storage.__class__.__name__,
        'has_bucket': hasattr(default_storage, 'bucket_name'),
        'bucket_name': getattr(default_storage, 'bucket_name', None),
    }

    # 3. Test de conexión S3
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_S3_REGION_NAME', 'us-east-2')
        )

        bucket_name = os.environ.get('AWS_STORAGE_BUCKET_NAME')
        response = s3_client.head_bucket(Bucket=bucket_name)
        diagnostics['s3_connection'] = {
            'status': 'success',
            'bucket_accessible': True,
            'message': f'Bucket {bucket_name} accesible'
        }

        # Listar algunos objetos del bucket
        try:
            objects = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
            diagnostics['s3_objects'] = {
                'count': objects.get('KeyCount', 0),
                'files': [obj['Key'] for obj in objects.get('Contents', [])]
            }
        except Exception as e:
            diagnostics['s3_objects'] = {'error': str(e)}

    except Exception as e:
        diagnostics['s3_connection'] = {
            'status': 'error',
            'message': str(e)
        }

    # 4. Test de subida de archivo
    if request.method == 'POST':
        try:
            # Crear un archivo de prueba
            from django.core.files.base import ContentFile
            test_content = ContentFile(b"Test file for S3 diagnostics")
            test_filename = "diagnostics/test_file.txt"

            # Intentar guardar con default_storage
            saved_path = default_storage.save(test_filename, test_content)
            file_url = default_storage.url(saved_path)

            diagnostics['upload_test'] = {
                'status': 'success',
                'saved_path': saved_path,
                'file_url': file_url,
                'file_exists': default_storage.exists(saved_path)
            }

            # Intentar eliminar el archivo de prueba
            try:
                default_storage.delete(saved_path)
                diagnostics['cleanup'] = 'success'
            except:
                diagnostics['cleanup'] = 'failed'

        except Exception as e:
            diagnostics['upload_test'] = {
                'status': 'error',
                'message': str(e)
            }

    return JsonResponse(diagnostics, indent=2)

@staff_member_required
def file_upload_test(request):
    """
    Vista para probar subida de archivos manualmente
    """
    if request.method == 'POST' and request.FILES.get('test_file'):
        try:
            uploaded_file = request.FILES['test_file']

            # Guardar archivo
            file_path = f"test_uploads/{uploaded_file.name}"
            saved_path = default_storage.save(file_path, uploaded_file)

            # Obtener URL
            file_url = default_storage.url(saved_path)

            return JsonResponse({
                'status': 'success',
                'original_name': uploaded_file.name,
                'saved_path': saved_path,
                'file_url': file_url,
                'file_size': uploaded_file.size,
                'content_type': uploaded_file.content_type,
                'storage_class': default_storage.__class__.__name__
            })

        except Exception as e:
            logger.error(f"Error en test de subida: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })

    # Mostrar formulario de prueba
    return render(request, 'core/file_upload_test.html')