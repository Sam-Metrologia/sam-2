# 🚀 Guía de Despliegue en Render - SAM Metrología

## 📋 Pre-requisitos

✅ Código ya está en GitHub: https://github.com/Sam-Metrologia/sam-2.git
✅ Configuración de Render lista (`render.yaml`)
✅ Scripts de build y start configurados
✅ Correcciones de bugs aplicadas (commit 32de1ee)

## 🌐 Paso 1: Crear Cuenta en Render

1. Ve a https://render.com
2. Haz clic en "Get Started" o "Sign Up"
3. **Opción Recomendada**: Sign up con GitHub
   - Esto facilita la conexión con tu repositorio
   - Autoriza a Render para acceder a tus repositorios

## 📦 Paso 2: Crear Nuevo Web Service desde Blueprint

### Opción A: Deploy desde Blueprint (RECOMENDADO)

1. En el Dashboard de Render, haz clic en **"New +"**
2. Selecciona **"Blueprint"**
3. Conecta tu repositorio:
   - Busca: `Sam-Metrologia/sam-2`
   - Haz clic en **"Connect"**
4. Render detectará automáticamente el archivo `render.yaml`
5. Revisa la configuración:
   - ✅ Web Service: `sam-metrologia`
   - ✅ Worker: `sam-zip-processor`
   - ✅ Database: `sam-metrologia-db` (PostgreSQL)
   - ✅ 6 Cron Jobs configurados
6. Haz clic en **"Apply"**

### Opción B: Deploy Manual (Alternativa)

Si prefieres configurar manualmente:

1. En Dashboard, haz clic en **"New +"** → **"Web Service"**
2. Conecta el repositorio `Sam-Metrologia/sam-2`
3. Configura:
   - **Name**: `sam-metrologia`
   - **Region**: Oregon (o la más cercana)
   - **Branch**: `main`
   - **Runtime**: Python 3
   - **Build Command**: `./build.sh`
   - **Start Command**: `./start.sh`
   - **Plan**: Free (o el que prefieras)

## 🔐 Paso 3: Configurar Variables de Entorno

Render generará algunas automáticamente, pero DEBES configurar estas manualmente:

### En el Dashboard del Web Service:

1. Ve a **"Environment"** en el menú lateral
2. Añade las siguientes variables:

#### AWS S3 (Para archivos en producción) - OBLIGATORIO

```
AWS_ACCESS_KEY_ID = [Tu Access Key de AWS]
AWS_SECRET_ACCESS_KEY = [Tu Secret Key de AWS]
AWS_STORAGE_BUCKET_NAME = [Nombre de tu bucket S3]
AWS_S3_REGION_NAME = us-east-2 (o tu región)
```

#### Email (Para notificaciones) - OPCIONAL pero recomendado

```
EMAIL_HOST = smtp.gmail.com
EMAIL_PORT = 587
EMAIL_HOST_USER = [Tu email de Gmail]
EMAIL_HOST_PASSWORD = [App Password de Gmail]
ADMIN_EMAIL = metrologiasam@gmail.com
```

#### Otras configuraciones importantes

```
DEBUG_VALUE = False
PYTHON_VERSION = 3.11.9
```

### Variables que Render genera automáticamente:
- `SECRET_KEY` - Generada automáticamente
- `DATABASE_URL` - Conectada a la base de datos PostgreSQL
- `PORT` - Asignado por Render
- `RENDER_EXTERNAL_HOSTNAME` - Tu dominio de Render

## 🗄️ Paso 4: Verificar Base de Datos PostgreSQL

1. En el Dashboard, ve a **"Databases"**
2. Deberías ver `sam-metrologia-db`
3. Verifica que esté:
   - ✅ Plan: Free
   - ✅ Region: Oregon (o tu región elegida)
   - ✅ Status: Available

## ⚙️ Paso 5: Configurar Worker (Procesador ZIP)

Si usaste Blueprint, esto ya está configurado. Si no:

1. En Dashboard, haz clic en **"New +"** → **"Background Worker"**
2. Conecta el mismo repositorio
3. Configura:
   - **Name**: `sam-zip-processor`
   - **Build Command**: `./build.sh`
   - **Start Command**: `python manage.py process_zip_queue --check-interval 5 --cleanup-old`
   - Usa las MISMAS variables de entorno que el Web Service

## ⏰ Paso 6: Configurar Cron Jobs

Si usaste Blueprint, estos ya están configurados. Verifica en **"Cron Jobs"**:

1. ✅ **notificaciones-diarias** - 8:00 AM Colombia (13:00 UTC) - Diaria
2. ✅ **mantenimiento-diario** - 3:00 AM Colombia (8:00 UTC) - Diaria
3. ✅ **limpieza-zips** - Cada 6 horas
4. ✅ **notificaciones-vencidas-semanales** - Lunes 8:00 AM - Semanal
5. ✅ **verificar-trials** - 5:00 AM Colombia - Diaria
6. ✅ **limpieza-notificaciones** - Domingos 4:00 AM - Semanal

## 🚀 Paso 7: Deploy Inicial

1. Render comenzará automáticamente el primer deploy
2. Monitorea el proceso en la pestaña **"Logs"**
3. El proceso tomará aproximadamente 5-10 minutos:
   - Installing dependencies
   - Running build.sh
   - Applying migrations
   - Collecting static files
   - Starting Gunicorn server

### ✅ Verificar Deploy Exitoso:

Busca en los logs:
```
✓ Build completado!
✓ Aplicando migraciones... Done
✓ Recolectando archivos estáticos... Done
✓ Iniciando servidor Gunicorn...
[INFO] Listening at: http://0.0.0.0:10000
```

## 🌍 Paso 8: Acceder a tu Aplicación

1. Tu URL será: `https://sam-metrologia.onrender.com` (o similar)
2. Encuentra tu URL exacta en:
   - Dashboard → Tu servicio → URL en la parte superior
3. Primera visita:
   - Puede tardar 30-60 segundos (plan Free)
   - El servidor "despierta" después de inactividad

## 👤 Paso 9: Crear Superusuario

Necesitas crear un admin para acceder:

1. En el Dashboard de tu Web Service
2. Ve a **"Shell"** en el menú lateral
3. Ejecuta:
```bash
python manage.py createsuperuser
```
4. Sigue las instrucciones para crear usuario

## 🔍 Paso 10: Verificación Post-Deploy

### Verifica que todo funcione:

1. ✅ Página principal carga
2. ✅ Login funciona
3. ✅ Admin panel accesible: `https://tu-app.onrender.com/admin/`
4. ✅ Archivos estáticos cargan (CSS, JS, imágenes)
5. ✅ Base de datos conectada (crea un equipo de prueba)
6. ✅ Subida de archivos funciona (prueba subir un documento)

### Verifica Logs:

```
# Logs en tiempo real
Dashboard → Tu servicio → Logs

# Busca errores con:
[ERROR]
Traceback
500
```

## 🐛 Troubleshooting Común

### Problema 1: "Application failed to respond"
**Solución**:
- Verifica que `PORT` esté en las variables de entorno
- Asegúrate que Gunicorn use `0.0.0.0:$PORT`

### Problema 2: Archivos estáticos no cargan (CSS/JS)
**Solución**:
- Verifica variables AWS S3 configuradas
- Revisa `collectstatic` en logs de build
- Confirma permisos del bucket S3

### Problema 3: Base de datos no conecta
**Solución**:
- Verifica `DATABASE_URL` en variables de entorno
- Asegúrate que la DB esté en estado "Available"
- Revisa que `migrate` se ejecutó correctamente

### Problema 4: Error 500 en producción
**Solución**:
```bash
# En Shell de Render:
python manage.py check --deploy
```
- Revisa logs detallados
- Verifica `DEBUG_VALUE = False`
- Confirma `ALLOWED_HOSTS` incluye tu dominio Render

### Problema 5: Worker ZIP no procesa
**Solución**:
- Verifica que el Worker esté "Running"
- Revisa logs del Worker separadamente
- Confirma mismas variables de entorno que Web Service

## 📊 Monitoreo y Mantenimiento

### Logs en Producción:
```bash
# Ver logs en tiempo real:
Dashboard → Tu servicio → Logs

# Logs estructurados en:
/opt/render/project/src/logs/sam_info.log
/opt/render/project/src/logs/sam_errors.log
```

### Actualizaciones Automáticas:
- ✅ Render hace auto-deploy cuando haces push a `main`
- Monitorea cada deploy en **"Events"**

### Backup de Base de Datos:
1. Dashboard → Databases → `sam-metrologia-db`
2. Ve a **"Backups"**
3. Render hace backups automáticos (plan Free: 7 días retención)

## 💰 Costos y Planes

### Plan FREE (Actual):
- ✅ Web Service: Free
- ✅ PostgreSQL: Free (1 GB)
- ✅ Cron Jobs: Free
- ⚠️ Limitaciones:
  - App "duerme" después de 15 min inactividad
  - 750 horas/mes de runtime
  - Reinicia cada 30 días

### Upgrade Recomendado (cuando sea necesario):
- **Starter Plan** ($7/mes por servicio):
  - Sin sleep automático
  - Más RAM/CPU
  - Sin reinicios mensuales

- **Standard Plan** ($25/mes):
  - Mayor capacidad
  - Mejor para producción

## 🔒 Seguridad en Producción

### Checklist de Seguridad:
- ✅ `DEBUG_VALUE = False`
- ✅ `SECRET_KEY` único y seguro (generado por Render)
- ✅ HTTPS habilitado (automático en Render)
- ✅ `ALLOWED_HOSTS` configurado correctamente
- ✅ Variables sensibles en Environment (no en código)
- ✅ Bucket S3 con permisos correctos

## 📝 Comandos Útiles (Shell de Render)

```bash
# Ver migraciones pendientes
python manage.py showmigrations

# Ejecutar migraciones manualmente
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Verificar configuración
python manage.py check --deploy

# Limpiar archivos ZIP viejos
python manage.py cleanup_zip_files --older-than-hours 6

# Verificar health check
python manage.py health_check
```

## 🎉 ¡Deploy Completado!

Tu aplicación SAM Metrología está ahora en producción en:
**https://sam-metrologia.onrender.com** (o tu URL personalizada)

### Próximos Pasos:
1. ✅ Configura tu dominio personalizado (opcional)
2. ✅ Configura alertas de monitoreo
3. ✅ Prueba todas las funcionalidades en producción
4. ✅ Configura backup schedule
5. ✅ Documenta credenciales de admin

---

## 📞 Soporte

- **Render Docs**: https://render.com/docs
- **Render Status**: https://status.render.com
- **Community Forum**: https://community.render.com

**¡Feliz Deploy! 🚀**
