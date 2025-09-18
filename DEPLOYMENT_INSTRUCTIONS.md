# Instrucciones de Implementación - Mejoras de Seguridad SAM

## Resumen de Mejoras Implementadas

### ✅ 1. Validación Robusta de Archivos (`core/security.py`)
- **MIME type validation**: Verificación de firmas binarias (magic numbers)
- **Path traversal protection**: Prevención de ataques de directorio
- **Content scanning**: Detección de contenido malicioso
- **Checksum verification**: Validación de integridad con MD5

### ✅ 2. Control de Cuotas de Almacenamiento
- **Límites por empresa**: Campo `limite_almacenamiento_mb` en modelo Empresa
- **Tracking de uso**: Seguimiento automático del espacio utilizado
- **Validación preventiva**: Bloqueo de uploads que excedan la cuota
- **Dashboard de cuotas**: Información visual del uso de almacenamiento

### ✅ 3. Almacenamiento AWS S3 Mejorado
- **Storage personalizado**: `proyecto_c/storages.py` con URLs firmadas
- **Archivos privados**: Configuración de permisos por defecto
- **URLs de acceso seguro**: Generación de URLs firmadas con expiración
- **Retry logic**: Manejo robusto de errores de conexión

### ✅ 4. Optimización de Consultas de Base de Datos
- **select_related**: Reducción de consultas N+1 en relaciones FK
- **prefetch_related**: Optimización de relaciones M2M y reverse FK
- **Cache inteligente**: Sistema de cache con versionado automático
- **Queries agregadas**: Estadísticas calculadas en una sola consulta

### ✅ 5. Servicios Centralizados (`core/services_new.py`)
- **SecureFileUploadService**: Manejo unificado de archivos
- **OptimizedEquipmentService**: Lógica de negocio optimizada
- **StorageQuotaManager**: Gestión de cuotas de almacenamiento
- **CacheManager**: Cache con invalidación inteligente

## Pasos de Implementación

### 1. Instalar Dependencias Adicionales
```bash
pip install python-magic  # Para validación de MIME types
```

### 2. Ejecutar Migraciones
```bash
python manage.py migrate
```

### 3. Configurar AWS S3
Asegúrate de que las siguientes variables de entorno estén configuradas:

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_STORAGE_BUCKET_NAME=your_bucket_name
AWS_S3_REGION_NAME=us-east-2

# Opcional: Para Redis cache
REDIS_URL=redis://localhost:6379/1
```

### 4. Configurar Permisos de S3 Bucket

#### IAM Policy para la aplicación:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:PutObjectAcl"
            ],
            "Resource": "arn:aws:s3:::your-bucket-name/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": "arn:aws:s3:::your-bucket-name"
        }
    ]
}
```

#### Bucket Policy (ejemplo para acceso privado):
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DenyDirectPublicAccess",
            "Effect": "Deny",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::your-bucket-name/*",
            "Condition": {
                "StringNotEquals": {
                    "aws:PrincipalServiceName": [
                        "ec2.amazonaws.com"
                    ]
                }
            }
        }
    ]
}
```

### 5. Actualizar Configuración de Settings

En `proyecto_c/settings.py`, verificar que esté configurado:

```python
# DEFAULT_FILE_STORAGE debe apuntar al nuevo storage
DEFAULT_FILE_STORAGE = 'proyecto_c.storages.S3MediaStorage'

# Configuración de cuotas por defecto
DEFAULT_STORAGE_QUOTA = 1024 * 1024 * 1024  # 1GB
```

### 6. Configurar Límites de Almacenamiento por Empresa

#### Via Django Admin:
1. Ir a Admin → Empresas
2. Editar cada empresa
3. Configurar "Límite de Almacenamiento (MB)"

#### Via Script (crear en `core/management/commands/`):
```python
from django.core.management.base import BaseCommand
from core.models import Empresa

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Configurar límites basados en el número de equipos
        for empresa in Empresa.objects.all():
            equipos_count = empresa.equipos.count()
            # ~20 MB por equipo (estimación conservativa)
            limite_mb = max(100, equipos_count * 20)  # Mínimo 100MB
            empresa.limite_almacenamiento_mb = limite_mb
            empresa.save()
            print(f"Empresa {empresa.nombre}: {limite_mb}MB")
```

## Testing y Verificación

### 1. Test de Subida de Archivos
```bash
# Crear archivos de prueba
echo "Test PDF content" > test.pdf
echo "Test image" > test.jpg

# Probar desde la interfaz:
# - Subir archivo válido → Debe funcionar
# - Subir archivo con extensión peligrosa (.exe) → Debe fallar
# - Subir archivo muy grande → Debe fallar con mensaje de cuota
```

### 2. Test de Cuotas de Almacenamiento
```python
# En Django shell
from core.models import Empresa
from core.security import StorageQuotaManager

empresa = Empresa.objects.first()
manager = StorageQuotaManager()
info = manager.get_quota_info(empresa)
print(f"Cuota: {info['quota_mb']}MB, Uso: {info['usage_mb']}MB")
```

### 3. Test de Performance del Dashboard
```bash
# Usar Django Debug Toolbar para verificar:
# - Número de queries ejecutadas
# - Tiempo de respuesta
# - Uso de cache
```

### 4. Test de URLs de S3
```python
# En Django shell
from core.services_new import file_upload_service
from core.models import Documento

doc = Documento.objects.first()
url = file_upload_service.get_file_url(doc.archivo_s3_path)
print(f"URL: {url}")
# La URL debe ser accesible y contener signature parameters
```

## Monitoreo y Logs

### 1. Logs de Seguridad
Los eventos de seguridad se registran en:
- `logs/sam_security.log`
- `logs/sam_errors.log`

### 2. Métricas a Monitorear
- Intentos de subida de archivos maliciosos
- Empresas cerca del límite de almacenamiento
- Errores de S3 connectivity
- Performance del dashboard (tiempo de respuesta)

### 3. Alertas Recomendadas
```python
# Ejemplo de check de salud
def health_check():
    # Verificar conectividad S3
    from django.core.files.storage import default_storage
    try:
        default_storage.listdir('')
        s3_status = "OK"
    except:
        s3_status = "ERROR"

    # Verificar cache
    from django.core.cache import cache
    cache.set('health_check', 'OK', 60)
    cache_status = "OK" if cache.get('health_check') == 'OK' else "ERROR"

    return {
        's3': s3_status,
        'cache': cache_status
    }
```

## Rollback Plan

En caso de problemas, se puede hacer rollback:

### 1. Revertir a Servicios Anteriores
```python
# En views.py, cambiar:
from .services_new import file_upload_service
# Por:
from .services import FileUploadService
file_upload_service = FileUploadService()
```

### 2. Revertir Storage Backend
```python
# En settings.py:
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
```

### 3. Revertir Migraciones
```bash
python manage.py migrate core 0001  # Revertir a migración anterior
```

## Troubleshooting

### Problema: URLs de S3 no funcionan
**Solución**: Verificar permisos IAM y bucket policy

### Problema: Archivos no se suben
**Solución**: Revisar logs en `logs/sam_errors.log` para detalles específicos

### Problema: Dashboard lento
**Solución**: Verificar configuración de cache y consultas optimizadas

### Problema: Cuotas no se calculan correctamente
**Solución**: Ejecutar script de recálculo de cuotas manual

## Configuración Recomendada para Producción

```python
# En settings.py para producción
SAM_CONFIG = {
    'DEFAULT_EQUIPMENT_LIMIT': 5,
    'MAX_EQUIPMENT_LIMIT': 1000,
    'DEFAULT_STORAGE_QUOTA_MB': 1024,  # 1GB
    'MAX_FILE_SIZE_MB': 10,
    'CACHE_TIMEOUT_DASHBOARD': 300,    # 5 minutos
    'PRESIGNED_URL_EXPIRY': 3600,      # 1 hora
}

# Rate limiting para uploads
RATE_LIMIT_CONFIG = {
    'UPLOAD_FILES': {'limit': 10, 'period': 300},  # 10 uploads por 5 minutos
}
```

La implementación está lista para producción con todas las mejoras de seguridad y performance implementadas.