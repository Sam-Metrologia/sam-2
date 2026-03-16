# Guia de Recuperacion de Backups desde Cloudflare R2

## Descripcion del Sistema de Backups

El sistema SAM Metrologia crea backups automaticos diarios de la base de datos PostgreSQL y los almacena en Cloudflare R2 (S3-compatible) para seguridad. Cumple con la Clausula 5.2 del contrato.

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

### Opcion 1: Verificar en Cloudflare Dashboard

1. Ir a [Cloudflare Dashboard](https://dash.cloudflare.com/) → R2
2. Seleccionar el bucket de backups
3. Navegar a la carpeta `backups/database/`
4. Verificar que existan archivos con formato: `sam_backup_YYYYMMDD_HHMMSS.sql.gz`

### Opcion 2: Usar el script de backup

```bash
# Listar los ultimos 10 backups
python -c "
from backup_to_s3 import DatabaseBackupManager
mgr = DatabaseBackupManager()
mgr.list_backups()
"
```

### Opcion 3: Verificar logs del sistema

```bash
# Revisar logs de backup en GitHub Actions
# Ir a: GitHub repo → Actions → "Backup Diario Automatico" → ver ultimo run
```

---

## 📥 Proceso de Recuperación de Backups

### Paso 1: Descargar el Backup desde Cloudflare R2

#### Método A: Cloudflare R2 Dashboard (Interfaz Web)

1. Ir a [Cloudflare Dashboard](https://dash.cloudflare.com/) → **R2**
2. Seleccionar el bucket de backups (nombre configurado en `AWS_BACKUP_BUCKET`)
3. Navegar a la carpeta `backups/`
4. Buscar el archivo de backup que necesitas:
   - Los archivos tienen formato: `backup_EmpresaNombre_20241001_143022.zip`
   - La fecha está en formato: AAAAMMDD_HHMMSS
5. Hacer clic en el archivo → **Download**
6. Guardar en tu servidor en una ubicación temporal, por ejemplo: `/tmp/backup_recuperacion.zip`

#### Método B: rclone (Recomendado para R2)

```bash
# Instalar rclone si no lo tienes
# Linux/macOS:
curl https://rclone.org/install.sh | sudo bash
# Windows: descargar desde https://rclone.org/downloads/

# Configurar rclone para R2 (primera vez)
rclone config
# Seleccionar: n (nueva configuración)
# Name: r2
# Type: s3
# Provider: Cloudflare
# access_key_id: <tu R2_ACCESS_KEY_ID>
# secret_access_key: <tu R2_SECRET_ACCESS_KEY>
# endpoint: https://<account_id>.r2.cloudflarestorage.com
# (el resto dejar en blanco / default)

# Listar backups disponibles
rclone ls r2:tu-bucket-name/backups/

# Descargar un backup específico
rclone copy r2:tu-bucket-name/backups/backup_MiEmpresa_20241001_143022.zip /tmp/
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
# 1. Descargar todos los backups desde R2
rclone sync r2:tu-bucket-name/backups/ /tmp/backups/

# 2. Restaurar cada empresa (una por una)
for backup in /tmp/backups/*.zip; do
    python manage.py restore_backup "$backup" --restore-files
done
```

### Escenario 2: Recuperar UNA Empresa Específica

Si una empresa específica tiene datos incorrectos:

```bash
# 1. Descargar el backup más reciente de esa empresa desde R2
rclone copy r2:tu-bucket-name/backups/backup_MiEmpresa_20241001_143022.zip /tmp/

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

## Configuracion de Backups Automaticos

### Variables de Entorno / Secrets de GitHub Requeridos

```bash
# Credenciales de Cloudflare R2
AWS_ACCESS_KEY_ID=tu_r2_access_key_id
AWS_SECRET_ACCESS_KEY=tu_r2_secret_access_key
AWS_BACKUP_BUCKET=nombre-del-bucket-en-r2
AWS_S3_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
AWS_S3_REGION_NAME=auto

# Base de datos
DATABASE_URL=postgresql://...
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

### Error: "No credentials found" en rclone

```bash
# Verificar configuración de rclone
rclone config show r2

# Reconfigurar si es necesario
rclone config reconnect r2:
```

### Error: "Access Denied" al acceder a R2

Verificar en el **Cloudflare Dashboard → R2 → Manage R2 API Tokens** que el token tenga permisos:
- **Object Read** (para listar y descargar)
- **Object Write** (para subir backups)

### Los backups no se suben a R2

Verificar en logs:
```bash
cat logs/sam_errors.log | grep -i "r2\|s3\|backup"
```

---

## 📞 Soporte

Si tienes problemas con la recuperación de backups:

1. Revisar logs del sistema: `logs/sam_errors.log`
2. Verificar credenciales R2 en variables de entorno (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_ENDPOINT_URL`)
3. Comprobar que el bucket R2 existe y es accesible desde el Cloudflare Dashboard
4. Verificar configuración de rclone: `rclone config show r2`
5. Contactar al administrador del sistema

---

## 📝 Notas Importantes

- ✅ Los backups se crean automáticamente cada mes
- ✅ Se guardan en Cloudflare R2 para seguridad fuera del servidor
- ✅ Los backups incluyen TODOS los datos de la empresa
- ⚠️ Los backups locales se eliminan después de subir a R2 (para ahorrar espacio)
- ✅ Los backups en R2 mayores a 6 meses se eliminan automáticamente
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

**Ultima actualizacion**: Marzo 2026 - Referencias AWS CLI reemplazadas por rclone para Cloudflare R2
