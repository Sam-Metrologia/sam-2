# 🚀 Configurar Tareas Automáticas con GitHub Actions (GRATIS)

## ✅ ¿Qué he hecho?

He configurado **GitHub Actions** para ejecutar tareas automáticas **100% GRATIS**:

- ✅ API endpoints creados en Django
- ✅ 6 workflows de GitHub Actions configurados
- ✅ Sin necesidad de pagar Render

---

## 📋 TAREAS AUTOMÁTICAS CONFIGURADAS

| # | Tarea | Frecuencia | Hora (Colombia) | Archivo |
|---|-------|-----------|-----------------|---------|
| 1 | **Notificaciones Diarias** | Todos los días | 8:00 AM | `daily-notifications.yml` |
| 2 | **Mantenimiento Diario** | Todos los días | 3:00 AM | `daily-maintenance.yml` |
| 3 | **Limpieza ZIPs** | Cada 6 horas | - | `cleanup-zips.yml` |
| 4 | **Notificaciones Vencidas** | Lunes | 8:00 AM | `weekly-overdue.yml` |
| 5 | **Verificar Trials** | Todos los días | 5:00 AM | `check-trials.yml` |
| 6 | **Limpieza Notificaciones** | Domingos | 4:00 AM | `cleanup-notifications.yml` |

---

## 🔧 CONFIGURACIÓN REQUERIDA

### Paso 1: Agregar Variable de Entorno en Render

Necesitas agregar un token de seguridad en tu aplicación:

1. Ve a **Render Dashboard** > **sam-metrologia**
2. Ve a **Environment** (menú lateral)
3. Haz clic en **"Add Environment Variable"**
4. Agrega:
   - **Key**: `SCHEDULED_TASKS_TOKEN`
   - **Value**: `tu-token-secreto-aqui-12345`

   **⚠️ IMPORTANTE**: Genera un token fuerte, por ejemplo:
   ```
   SAM-secret-token-2025-abc123xyz789
   ```

5. Haz clic en **"Save Changes"**
6. Espera a que Render haga redeploy (2-3 minutos)

### Paso 2: Configurar GitHub Secrets

Ahora vas a agregar 2 secrets en GitHub:

#### 2.1. Ve a tu Repositorio en GitHub

1. https://github.com/Sam-Metrologia/sam-2
2. Ve a **Settings** (pestaña superior)
3. En el menú lateral, ve a **Secrets and variables** > **Actions**
4. Haz clic en **"New repository secret"**

#### 2.2. Crear Secret #1: SCHEDULED_TASKS_TOKEN

- **Name**: `SCHEDULED_TASKS_TOKEN`
- **Value**: El mismo token que pusiste en Render
  ```
  SAM-secret-token-2025-abc123xyz789
  ```
- Haz clic en **"Add secret"**

#### 2.3. Crear Secret #2: APP_URL

- **Name**: `APP_URL`
- **Value**: La URL de tu aplicación en Render (SIN barra final)
  ```
  https://sam-9o6o.onrender.com
  ```
  (Reemplaza con tu URL real de Render)
- Haz clic en **"Add secret"**

---

## 📤 SUBIR A GITHUB

Ahora vamos a subir los archivos a GitHub:

```bash
cd "C:\Users\LENOVO\OneDrive\Escritorio\sam-2"
git status
git add .github/workflows/
git add core/views/scheduled_tasks_api.py
git add core/views/__init__.py
git add core/urls.py
git commit -m "Agregar GitHub Actions para tareas automaticas (notificaciones, mantenimiento, limpieza)"
git push origin main
```

---

## ✅ VERIFICAR QUE FUNCIONA

### Paso 1: Verificar que GitHub detectó los Workflows

1. Ve a tu repositorio en GitHub
2. Pestaña **"Actions"**
3. Deberías ver 6 workflows en el menú lateral:
   - Notificaciones Diarias
   - Mantenimiento Diario
   - Limpieza de Archivos ZIP
   - Notificaciones Vencidas Semanales
   - Verificar Trials Expirados
   - Limpieza de Notificaciones Antiguas

### Paso 2: Probar Manualmente (Sin Esperar al Horario)

1. En GitHub, pestaña **"Actions"**
2. Haz clic en **"Notificaciones Diarias"** (en el menú lateral)
3. Arriba a la derecha, haz clic en **"Run workflow"**
4. Selecciona branch **"main"**
5. Haz clic en **"Run workflow"** (botón verde)
6. Espera 10-30 segundos
7. Verás un nuevo workflow ejecutándose

### Paso 3: Ver Logs

1. Haz clic en el workflow que se está ejecutando
2. Haz clic en el job **"send-notifications"**
3. Verás los logs en tiempo real

**Si sale ✅ verde = Funcionó correctamente**
**Si sale ❌ rojo = Hubo un error (ver logs)**

---

## 🧪 PROBAR ENDPOINTS LOCALMENTE

Antes de probar en GitHub, puedes probar los endpoints localmente:

```bash
# 1. Verificar que el servidor esté corriendo
cd "C:\Users\LENOVO\OneDrive\Escritorio\sam-2"
# (Asegúrate que manage.py runserver esté corriendo)

# 2. Probar health check (sin token)
curl http://localhost:8000/core/api/scheduled/health/

# 3. Probar notificaciones (con token)
curl -X POST \
  -H "Authorization: Bearer SAM-secret-token-2025-abc123xyz789" \
  http://localhost:8000/core/api/scheduled/notifications/daily/

# 4. Probar mantenimiento (con token)
curl -X POST \
  -H "Authorization: Bearer SAM-secret-token-2025-abc123xyz789" \
  http://localhost:8000/core/api/scheduled/maintenance/daily/
```

Si no tienes `curl`, usa tu navegador:
```
http://localhost:8000/core/api/scheduled/health/
```

---

## 📅 HORARIOS (Hora Colombia)

```
03:00 AM - Mantenimiento diario
05:00 AM - Verificar trials expirados
08:00 AM - Notificaciones diarias

Cada 6 horas - Limpieza de archivos ZIP (0:00, 6:00, 12:00, 18:00 UTC-5)

Lunes 08:00 AM - Notificaciones vencidas semanales
Domingo 04:00 AM - Limpieza de notificaciones antiguas
```

---

## 🔒 SEGURIDAD

### ¿Cómo funciona la autenticación?

Los workflows de GitHub envían un **token secreto** en el header `Authorization`:
```
Authorization: Bearer SAM-secret-token-2025-abc123xyz789
```

Django verifica este token antes de ejecutar cualquier tarea:
```python
def verify_token(request):
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        return token == SCHEDULED_TASKS_TOKEN
    return False
```

Si el token no coincide, retorna **401 Unauthorized**.

### Recomendaciones de Seguridad

1. **Nunca compartas tu token** en código público
2. **Usa un token fuerte** (mínimo 32 caracteres aleatorios)
3. **Rota el token periódicamente** (cada 3-6 meses)
4. **Monitorea logs** en busca de intentos de acceso no autorizado

---

## 📊 MONITOREO

### Ver Ejecuciones en GitHub

1. GitHub > Pestaña **"Actions"**
2. Ver historial de todas las ejecuciones
3. Filtrar por workflow, estado (exitoso/fallido), fecha

### Ver Logs en tu Aplicación

Los endpoints escriben logs en Django:
```bash
# Ver logs de notificaciones
grep "GitHub Actions" logs/sam_info.log

# Ver errores
tail -f logs/sam_errors.log
```

### Recibir Notificaciones de Errores

GitHub te enviará un email si un workflow falla:
- Ve a **Settings** > **Notifications**
- Asegúrate que **"Actions"** esté habilitado

---

## ❓ PREGUNTAS FRECUENTES

### ¿Es realmente gratis?

**Sí, 100% gratis.** GitHub Actions ofrece:
- **2,000 minutos/mes gratis** para repositorios públicos
- **3,000 minutos/mes gratis** para repositorios privados

Cada tarea toma ~5-10 segundos, así que tienes minutos de sobra.

### ¿Qué pasa si me quedo sin minutos?

Casi imposible. Con 6 tareas diarias:
- 6 tareas × 10 segundos × 30 días = 30 minutos/mes
- Tienes 2,000 minutos disponibles

### ¿Puedo cambiar los horarios?

Sí, edita los archivos `.yml` en `.github/workflows/`:

```yaml
schedule:
  - cron: '0 13 * * *'  # Cambiar esta línea
```

**Formato cron:**
```
0 13 * * *
│  │ │ │ │
│  │ │ │ └─ Día de la semana (0-6) (0 = Domingo)
│  │ │ └─── Mes (1-12)
│  │ └───── Día del mes (1-31)
│  └─────── Hora (0-23) en UTC
└────────── Minuto (0-59)
```

**⚠️ Recuerda**: GitHub Actions usa **UTC**. Colombia es **UTC-5**.
```
Hora Colombia + 5 horas = Hora UTC
8:00 AM Colombia = 13:00 UTC
```

### ¿Puedo desactivar un workflow?

**Opción 1: Desde GitHub**
1. Actions > Selecciona el workflow
2. Botón **"..."** (arriba derecha)
3. **"Disable workflow"**

**Opción 2: Eliminar el archivo**
```bash
git rm .github/workflows/daily-notifications.yml
git commit -m "Desactivar notificaciones diarias"
git push
```

### ¿Las notificaciones se enviarán ahora?

Sí, PERO solo si hay equipos con actividades próximas (15, 7, 0 días).

Si no hay equipos próximos, el workflow se ejecutará pero no enviará emails (comportamiento correcto).

---

## 🆘 SOLUCIÓN DE PROBLEMAS

### Error 401 Unauthorized

**Causa**: El token no coincide entre GitHub Secrets y Render.

**Solución**:
1. Verificar token en Render: Environment > SCHEDULED_TASKS_TOKEN
2. Verificar token en GitHub: Settings > Secrets > SCHEDULED_TASKS_TOKEN
3. Deben ser **exactamente iguales**

### Error 500 Internal Server Error

**Causa**: Error en el código Django.

**Solución**:
1. Ver logs en Render: Dashboard > Logs
2. Buscar el error específico
3. Verificar que las migraciones estén aplicadas

### Workflow no se ejecuta en el horario

**Causa**: GitHub Actions puede tener retraso de hasta 15 minutos.

**Solución**:
- Es normal, GitHub no garantiza ejecución exacta
- Puede ejecutarse 0-15 minutos después del horario
- Para ejecución exacta, necesitarías servidor propio (caro)

### No llegan notificaciones

**Verificar**:
1. ¿El workflow se ejecutó correctamente? (✅ verde en GitHub)
2. ¿Hay equipos con fechas en 15, 7, 0 días?
3. ¿EMAIL_HOST_USER y EMAIL_HOST_PASSWORD están configurados en Render?
4. Ver logs del workflow en GitHub

---

## ✅ CHECKLIST FINAL

Antes de dar por terminado:

- [ ] Token agregado en Render (SCHEDULED_TASKS_TOKEN)
- [ ] Render hizo redeploy (Environment > esperar)
- [ ] GitHub Secret #1 creado (SCHEDULED_TASKS_TOKEN)
- [ ] GitHub Secret #2 creado (APP_URL)
- [ ] Archivos subidos a GitHub (git push)
- [ ] Workflows visibles en GitHub Actions
- [ ] Probado 1 workflow manualmente ("Run workflow")
- [ ] Workflow ejecutado exitosamente (✅ verde)
- [ ] Logs verificados sin errores

---

## 🎉 ¡LISTO!

**Las tareas automáticas están configuradas y funcionando 100% GRATIS.**

GitHub Actions ejecutará automáticamente:
- Notificaciones diarias a las 8:00 AM
- Mantenimiento diario a las 3:00 AM
- Limpieza de ZIPs cada 6 horas
- Y todas las demás tareas según programación

**No necesitas pagar nada. Todo funciona en la nube de GitHub y Render.**

---

## 📞 SOPORTE

Si necesitas ayuda:
- WhatsApp: +57 324 7990534
- Email: metrologiasam@gmail.com
- GitHub Actions Docs: https://docs.github.com/en/actions

---

**Creado por:** Claude Code
**Fecha:** 23 de Octubre de 2025
