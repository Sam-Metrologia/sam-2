# 🔧 CORRECCIÓN: Email y Staticfiles en Producción

**Fecha:** 15 de Octubre de 2025
**Problemas identificados:**
1. ❌ Correos de error no se envían a `metrologiasam@gmail.com`
2. ❌ Error: `Missing staticfiles manifest entry for 'core/css/themes.css'`

---

## 📧 PROBLEMA 1: Correos de Error No se Envían

### ✅ Diagnóstico

El sistema **SÍ está configurado correctamente** para enviar correos en `settings.py`:

```python
# settings.py líneas 228-236
'mail_admins': {
    'level': 'ERROR',
    'filters': ['require_debug_false'],  # ⚠️ Solo funciona cuando DEBUG=False
    'class': 'django.utils.log.AdminEmailHandler',
    'formatter': 'verbose',
    'include_html': True,
}

# settings.py líneas 489-491
ADMINS = [
    ('Admin SAM', os.environ.get('ADMIN_EMAIL', 'metrologiasam@gmail.com')),
]
```

**El problema:** Las variables de entorno de email NO están configuradas en Render.

---

### 🛠️ SOLUCIÓN: Configurar Variables de Entorno en Render

#### Paso 1: Acceder a Render Dashboard

1. Ve a: https://dashboard.render.com/
2. Selecciona tu servicio: **sam-metrologia** (o el nombre que tenga)
3. Click en **"Environment"** en el menú lateral

#### Paso 2: Agregar Variables de Email

Añade las siguientes variables de entorno:

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `EMAIL_HOST_USER` | `metrologiasam@gmail.com` | Tu correo de Gmail |
| `EMAIL_HOST_PASSWORD` | `tu_app_password` | **Contraseña de aplicación** (NO la contraseña normal) |
| `EMAIL_HOST` | `smtp.gmail.com` | (Opcional, ya está por defecto) |
| `EMAIL_PORT` | `587` | (Opcional, ya está por defecto) |
| `ADMIN_EMAIL` | `metrologiasam@gmail.com` | Correo donde llegan las notificaciones |

#### Paso 3: Generar Contraseña de Aplicación de Gmail

**⚠️ IMPORTANTE:** NO uses tu contraseña normal de Gmail. Debes generar una "Contraseña de aplicación":

1. **Ir a tu Cuenta de Google:**
   - Ve a: https://myaccount.google.com/
   - Selecciona **"Seguridad"** en el menú lateral

2. **Habilitar Verificación en 2 Pasos** (si no está habilitada):
   - En la sección **"Cómo inicias sesión en Google"**
   - Click en **"Verificación en 2 pasos"**
   - Sigue los pasos para habilitarla

3. **Generar Contraseña de Aplicación:**
   - Una vez habilitada la verificación en 2 pasos
   - Ve a: https://myaccount.google.com/apppasswords
   - O busca **"Contraseñas de aplicaciones"** en la búsqueda
   - Selecciona **"Correo"** y **"Otro (nombre personalizado)"**
   - Escribe: `SAM Metrología Render`
   - Click en **"Generar"**
   - **Copia la contraseña generada** (16 caracteres, sin espacios)

4. **Usar la Contraseña en Render:**
   - Vuelve a Render Dashboard
   - En `EMAIL_HOST_PASSWORD`, pega la contraseña generada
   - Click en **"Save Changes"**

#### Paso 4: Reiniciar el Servicio

1. En Render Dashboard, click en **"Manual Deploy"**
2. Selecciona **"Deploy latest commit"**
3. Espera a que el deploy complete (5-10 minutos)

---

### 🧪 Verificar que Funciona

Para probar que los correos funcionan, puedes:

1. **Forzar un error en producción** (opcional, no recomendado)
2. **Revisar logs de Django:**
   ```
   En Render Dashboard → Logs
   Buscar líneas con: "django.core.mail"
   ```

Si está configurado correctamente, verás en los logs:
```
INFO Sending email to Admin SAM <metrologiasam@gmail.com>
```

---

## 🎨 PROBLEMA 2: Error de Staticfiles `themes.css`

### ✅ Diagnóstico

El error ocurre porque:
- WhiteNoise usa `CompressedStaticFilesStorage` que crea un manifest
- El archivo `themes.css` es nuevo (agregado recientemente)
- El manifest en producción no incluye este archivo

**Error exacto:**
```
ValueError: Missing staticfiles manifest entry for 'core/css/themes.css'
```

---

### 🛠️ SOLUCIÓN: Forzar Rebuild en Render

#### Opción 1: Deploy Manual (RECOMENDADO)

Ya hicimos un commit con `themes.css`, así que:

1. Ve a Render Dashboard
2. Tu servicio debería estar **desplegándose automáticamente**
3. Si no, click en **"Manual Deploy"** → **"Clear build cache & deploy"**
4. Esto forzará a:
   - Descargar el código nuevo
   - Ejecutar `build.sh` → `collectstatic`
   - Crear nuevo manifest con `themes.css`

#### Opción 2: Verificar que build.sh se Ejecuta Correctamente

El archivo `build.sh` **YA está correctamente configurado**:

```bash
#!/bin/bash

echo "Iniciando build..."

# Ejecutar migraciones de base de datos
echo "Aplicando migraciones..."
python manage.py migrate --noinput

# Recoger archivos estáticos ✅
echo "Recolectando archivos estaticos..."
python manage.py collectstatic --noinput

# Crear tabla de cache
echo "Verificando tabla de cache..."
python manage.py createcachetable sam_cache_table --noinput || true

echo "Build completado!"
```

---

### 🔍 Verificar que themes.css se Recolectó

Una vez que el deploy complete, verifica en los logs de Render que `collectstatic` se ejecutó:

```
Recolectando archivos estaticos...
XXX static files copied to '/opt/render/project/src/staticfiles'
```

El número `XXX` debe ser mayor que antes (porque ahora incluye `themes.css`).

---

## 📋 CHECKLIST DE VERIFICACIÓN POST-DEPLOY

### Email:
- [ ] Variables `EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD` configuradas en Render
- [ ] Contraseña de aplicación de Gmail generada y usada
- [ ] Servicio reiniciado después de agregar variables
- [ ] Verificar logs para confirmar que no hay errores de SMTP

### Staticfiles:
- [ ] Deploy completado en Render con commit más reciente
- [ ] Logs muestran "Recolectando archivos estaticos..."
- [ ] Número de archivos estáticos aumentó
- [ ] Error de `themes.css` desapareció en logs
- [ ] Modo oscuro funciona correctamente en producción

---

## 🔄 MONITOREO DE ERRORES

### Cómo Monitorear Logs en Render

1. **Acceder a Logs:**
   - Render Dashboard → Tu servicio → **"Logs"**

2. **Filtrar por Errores:**
   - Buscar: `ERROR` o `ValueError` o `Exception`

3. **Ver Correos Enviados:**
   - Buscar: `django.core.mail` o `Sending email`

---

## 📞 TROUBLESHOOTING

### Si los correos NO llegan después de configurar:

1. **Verificar Contraseña de Aplicación:**
   - ¿Copiaste correctamente la contraseña de 16 caracteres?
   - ¿Sin espacios?

2. **Verificar Variables en Render:**
   - Ve a Environment
   - Confirma que `EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD` tienen valores

3. **Revisar Logs de Render:**
   - Buscar errores tipo: `SMTPAuthenticationError`
   - Buscar: `django.core.mail`

4. **Probar Manualmente (Shell de Django):**
   ```python
   # En tu local (con las mismas variables de entorno)
   python manage.py shell

   from django.core.mail import send_mail
   send_mail(
       'Test Email',
       'This is a test',
       'metrologiasam@gmail.com',
       ['metrologiasam@gmail.com'],
       fail_silently=False,
   )
   ```

### Si el error de themes.css persiste:

1. **Verificar que el archivo existe:**
   ```
   Archivo: core/static/core/css/themes.css
   ```

2. **Limpiar cache de build en Render:**
   - Manual Deploy → **"Clear build cache & deploy"**

3. **Verificar STATICFILES_DIRS en settings.py:**
   ```python
   STATICFILES_DIRS = [
       BASE_DIR / 'core/static',  # ✅ Debe incluir core/static
   ]
   ```

---

## ✅ RESUMEN DE ACCIONES

**Para Correos:**
1. Generar contraseña de aplicación en Gmail
2. Configurar `EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD` en Render
3. Reiniciar servicio

**Para Staticfiles:**
1. Ya se hizo commit con `themes.css`
2. Deploy automático en Render recolectará el archivo
3. Verificar en logs que `collectstatic` se ejecutó

---

**🎯 Tiempo Estimado Total:** 10-15 minutos

**📅 Última Actualización:** 15 de Octubre de 2025
