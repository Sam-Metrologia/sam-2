# Guía de Recuperación de Backups desde S3

## Descripción del Sistema de Backups

El sistema SAM Metrología crea backups automáticos mensuales de todas las empresas y los almacena en Amazon S3 para seguridad.

### ¿Qué se respalda?

- **Datos de la empresa**: Información completa de la empresa
- **Usuarios**: Todos los usuarios asociados a la empresa
- **Equipos**: Inventario completo de equipos
- **Actividades**: Calibraciones, mantenimientos y comprobaciones
- **Archivos** (opcional): Logos, certificados, documentos adjuntos

### Formatos de Backup

- **JSON**: Datos en formato texto (más ligero, solo datos)
- **ZIP**: Incluye datos JSON + archivos multimedia

---

## 🔍 Cómo Saber si los Backups se están Guardando

### Opción 1: Verificar en AWS S3 Console

1. Ir a [AWS S3 Console](https://s3.console.aws.amazon.com/)
2. Buscar el bucket configurado (nombre en variable `AWS_STORAGE_BUCKET_NAME`)
3. Navegar a la carpeta `backups/`
4. Verificar que existan archivos con formato: `backup_NombreEmpresa_YYYYMMDD_HHMMSS.zip`

### Opción 2: Usar AWS CLI

```bash
# Listar todos los backups en S3
aws s3 ls s3://tu-bucket-name/backups/

# Listar backups de una empresa específica
aws s3 ls s3://tu-bucket-name/backups/ | grep "NombreEmpresa"
```

### Opción 3: Verificar logs del sistema

```bash
# Revisar logs de backup
cat logs/sam_info.log | grep "Backup uploaded to S3"
```

---

## 📥 Proceso de Recuperación de Backups

### Paso 1: Descargar el Backup desde S3

#### Método A: AWS S3 Console (Interfaz Web)

1. Ir a [AWS S3 Console](https://s3.console.aws.amazon.com/)
2. Seleccionar el bucket de SAM
3. Navegar a `backups/`
4. Buscar el archivo de backup que necesitas:
   - Los archivos tienen formato: `backup_EmpresaNombre_20241001_143022.zip`
   - La fecha está en formato: AAAAMMDD_HHMMSS
5. Hacer clic derecho → **Download**
6. Guardar en tu servidor en una ubicación temporal, por ejemplo: `/tmp/backup_recuperacion.zip`

#### Método B: AWS CLI (Línea de Comandos)

```bash
# Instalar AWS CLI si no lo tienes
pip install awscli

# Configurar credenciales (primera vez)
aws configure
# Ingresar: AWS Access Key ID, Secret Access Key, Region (us-east-2)

# Listar backups disponibles
aws s3 ls s3://tu-bucket-name/backups/

# Descargar un backup específico
aws s3 cp s3://tu-bucket-name/backups/backup_MiEmpresa_20241001_143022.zip /tmp/backup_recuperacion.zip
```

---

### Paso 2: Restaurar el Backup

Una vez descargado el archivo, usar el comando de Django para restaurar:

#### Restaurar sin sobrescribir (crear nueva empresa)

```bash
python manage.py restore_backup /tmp/backup_recuperacion.zip --new-name "Empresa Recuperada"
```

Esto creará una **nueva empresa** con los datos del backup.

#### Restaurar sobrescribiendo empresa existente

```bash
python manage.py restore_backup /tmp/backup_recuperacion.zip --overwrite
```

⚠️ **CUIDADO**: Esto **eliminará** todos los datos actuales de la empresa y los reemplazará con el backup.

#### Restaurar incluyendo archivos (logos, documentos)

```bash
python manage.py restore_backup /tmp/backup_recuperacion.zip --restore-files
```

Esto restaurará también los archivos multimedia incluidos en el ZIP.

#### Opciones combinadas

```bash
# Sobrescribir empresa Y restaurar archivos
python manage.py restore_backup /tmp/backup_recuperacion.zip --overwrite --restore-files

# Nueva empresa CON archivos
python manage.py restore_backup /tmp/backup_recuperacion.zip --new-name "Empresa Test" --restore-files
```

---

## 📋 Parámetros del Comando restore_backup

| Parámetro | Descripción | Ejemplo |
|-----------|-------------|---------|
| `archivo` | Ruta al archivo ZIP o JSON de backup | `/tmp/backup.zip` |
| `--overwrite` | Sobrescribe empresa existente (CUIDADO) | - |
| `--new-name "Nombre"` | Crea nueva empresa con nombre diferente | `--new-name "Test"` |
| `--restore-files` | Restaura archivos multimedia del ZIP | - |

---

## 🔄 Escenarios Comunes de Recuperación

### Escenario 1: Pérdida Total de Datos (Desastre)

Si perdiste TODA la base de datos:

```bash
# 1. Descargar todos los backups de S3
aws s3 sync s3://tu-bucket-name/backups/ /tmp/backups/

# 2. Restaurar cada empresa (una por una)
for backup in /tmp/backups/*.zip; do
    python manage.py restore_backup "$backup" --restore-files
done
```

### Escenario 2: Recuperar UNA Empresa Específica

Si una empresa específica tiene datos incorrectos:

```bash
# 1. Descargar el backup más reciente de esa empresa
aws s3 cp s3://tu-bucket-name/backups/backup_MiEmpresa_20241001_143022.zip /tmp/

# 2. Restaurar sobrescribiendo
python manage.py restore_backup /tmp/backup_MiEmpresa_20241001_143022.zip --overwrite --restore-files
```

### Escenario 3: Crear Copia de Prueba

Si quieres crear una empresa de prueba con datos reales:

```bash
python manage.py restore_backup /tmp/backup_EmpresaReal.zip --new-name "Empresa de Pruebas"
```

---

## 🔧 Verificar que la Restauración Funcionó

Después de restaurar, verificar:

```bash
# Ver empresas en la base de datos
python manage.py shell
>>> from core.models import Empresa
>>> Empresa.objects.all()
>>> empresa = Empresa.objects.get(nombre="Nombre Empresa Restaurada")
>>> empresa.equipos.count()  # Verificar cantidad de equipos
>>> empresa.usuarios_empresa.count()  # Verificar usuarios
```

---

## ⚙️ Configuración de Backups Automáticos

### Variables de Entorno Requeridas

```bash
# En tu archivo .env o configuración de producción
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_STORAGE_BUCKET_NAME=nombre-tu-bucket
AWS_S3_REGION_NAME=us-east-2  # o tu región
```

### Crear Backup Manual

```bash
# Backup de UNA empresa específica
python manage.py backup_data --empresa-id 1 --format both --include-files

# Backup de TODAS las empresas
python manage.py backup_data --all --format both --include-files
```

### Programar Backups Mensuales

El sistema tiene backups automáticos programados en el panel de **Admin/Sistema → Programación**.

Para verificar/configurar:
1. Ir a Admin/Sistema → Programación
2. Verificar que "Backups Mensuales" esté **activado**
3. Los backups se ejecutarán el día 1 de cada mes a las 02:00 AM

---

## 🚨 Solución de Problemas

### Error: "No module named 'boto3'"

```bash
pip install boto3
```

### Error: "Unable to locate credentials"

```bash
# Configurar credenciales AWS
aws configure
```

### Error: "An error occurred (AccessDenied)"

Verificar que tu usuario IAM tenga permisos S3:
- `s3:ListBucket`
- `s3:GetObject`
- `s3:PutObject`

### Los backups no se suben a S3

Verificar en logs:
```bash
cat logs/sam_errors.log | grep -i "s3\|backup"
```

---

## 📞 Soporte

Si tienes problemas con la recuperación de backups:

1. Revisar logs del sistema: `logs/sam_errors.log`
2. Verificar credenciales AWS
3. Comprobar que el bucket S3 existe y es accesible
4. Contactar al administrador del sistema

---

## 📝 Notas Importantes

- ✅ Los backups se crean automáticamente cada mes
- ✅ Se guardan en S3 para seguridad fuera del servidor
- ✅ Los backups incluyen TODOS los datos de la empresa
- ⚠️ Los backups locales se eliminan después de subir a S3 (para ahorrar espacio)
- ✅ **NUEVO**: Los backups en S3 mayores a 6 meses se eliminan automáticamente
- ⚠️ El comando `--overwrite` es DESTRUCTIVO - usar con cuidado

---

## 🧹 Limpieza Automática de Backups Antiguos

El sistema ahora incluye limpieza automática de backups mayores a **6 meses** para optimizar costos de almacenamiento en S3.

### Limpieza Manual

Para ejecutar manualmente la limpieza de backups antiguos:

```bash
# Simular limpieza (ver qué se eliminaría)
python manage.py cleanup_old_backups --dry-run --verbose

# Ejecutar limpieza real
python manage.py cleanup_old_backups

# Personalizar tiempo de retención (ej: 3 meses)
python manage.py cleanup_old_backups --retention-months 3
```

### Limpieza Automática

La limpieza de backups antiguos está integrada en el sistema de mantenimiento:

```bash
# Ejecutar todas las tareas de mantenimiento (incluye limpieza de backups)
python manage.py maintenance --task all

# Solo ejecutar limpieza de backups
python manage.py maintenance --task backups
```

También disponible desde el panel de **Admin/Sistema → Mantenimiento** con la opción "Limpiar backups antiguos (>6 meses)".

---

**Última actualización**: Octubre 2025
