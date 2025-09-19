# Diagnóstico específico para logos de empresa
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import default_storage
from .models import Empresa
from .templatetags.file_tags import secure_file_url, empresa_logo_url
import logging

logger = logging.getLogger('core')

@staff_member_required
def logo_diagnostics(request, empresa_id):
    """
    Diagnóstico específico para el logo de una empresa
    """
    empresa = get_object_or_404(Empresa, id=empresa_id)

    diagnostics = {
        'empresa_info': {
            'id': empresa.id,
            'nombre': empresa.nombre,
            'has_logo_field': hasattr(empresa, 'logo_empresa'),
            'logo_field_value': str(empresa.logo_empresa) if empresa.logo_empresa else None,
            'logo_field_name': str(empresa.logo_empresa.name) if empresa.logo_empresa else None,
            'logo_field_url_attr': getattr(empresa.logo_empresa, 'url', None) if empresa.logo_empresa else None,
        }
    }

    # Test del template tag empresa_logo_url
    try:
        logo_url_template_tag = empresa_logo_url(empresa)
        diagnostics['template_tag_result'] = {
            'status': 'success',
            'url': logo_url_template_tag,
            'url_length': len(logo_url_template_tag) if logo_url_template_tag else 0
        }
    except Exception as e:
        diagnostics['template_tag_result'] = {
            'status': 'error',
            'message': str(e)
        }

    # Test directo de secure_file_url
    if empresa.logo_empresa:
        try:
            direct_url = secure_file_url(empresa.logo_empresa)
            diagnostics['direct_secure_url'] = {
                'status': 'success',
                'url': direct_url,
                'url_length': len(direct_url) if direct_url else 0
            }
        except Exception as e:
            diagnostics['direct_secure_url'] = {
                'status': 'error',
                'message': str(e)
            }

        # Test de existencia del archivo en storage
        try:
            file_exists = default_storage.exists(empresa.logo_empresa.name)
            file_size = default_storage.size(empresa.logo_empresa.name) if file_exists else 0

            diagnostics['storage_info'] = {
                'file_exists': file_exists,
                'file_size': file_size,
                'file_path': empresa.logo_empresa.name,
                'storage_class': default_storage.__class__.__name__
            }
        except Exception as e:
            diagnostics['storage_info'] = {
                'error': str(e)
            }

    # Verificar si el archivo está en S3
    if empresa.logo_empresa:
        try:
            import boto3
            import os

            s3_client = boto3.client(
                's3',
                aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                region_name=os.environ.get('AWS_S3_REGION_NAME', 'us-east-2')
            )

            bucket_name = os.environ.get('AWS_STORAGE_BUCKET_NAME')

            # Probar diferentes rutas posibles
            possible_keys = [
                empresa.logo_empresa.name,
                f"media/{empresa.logo_empresa.name}",
                f"empresas_logos/{empresa.logo_empresa.name.split('/')[-1]}"
            ]

            s3_results = {}
            for key in possible_keys:
                try:
                    response = s3_client.head_object(Bucket=bucket_name, Key=key)
                    s3_results[key] = {
                        'exists': True,
                        'size': response.get('ContentLength', 0),
                        'last_modified': str(response.get('LastModified', ''))
                    }
                except:
                    s3_results[key] = {'exists': False}

            diagnostics['s3_check'] = s3_results

        except Exception as e:
            diagnostics['s3_check'] = {'error': str(e)}

    return JsonResponse(diagnostics, json_dumps_params={'indent': 2})

@staff_member_required
def test_logo_upload(request):
    """
    Página para probar subida de logos
    """
    if request.method == 'POST' and request.FILES.get('logo_file') and request.POST.get('empresa_id'):
        try:
            empresa_id = request.POST.get('empresa_id')
            empresa = get_object_or_404(Empresa, id=empresa_id)

            # Guardar el logo
            logo_file = request.FILES['logo_file']
            empresa.logo_empresa = logo_file
            empresa.save()

            # Obtener URL generada
            logo_url = empresa_logo_url(empresa)

            return JsonResponse({
                'status': 'success',
                'message': f'Logo subido exitosamente para {empresa.nombre}',
                'logo_url': logo_url,
                'empresa_id': empresa.id
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })

    # Obtener lista de empresas
    empresas = Empresa.objects.all()

    return render(request, 'core/test_logo_upload.html', {
        'empresas': empresas
    })