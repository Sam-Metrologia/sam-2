# 🚀 Activar Tareas Automáticas en Render

## ✅ YA HICE:
Agregué 6 Cron Jobs al archivo `render.yaml`

---

## 📋 TAREAS AUTOMÁTICAS CONFIGURADAS

| # | Tarea | Frecuencia | Hora (Colombia) | Qué hace |
|---|-------|-----------|-----------------|----------|
| 1 | **Notificaciones Diarias** | Todos los días | 8:00 AM | Envía recordatorios de calibraciones, mantenimientos y comprobaciones próximas |
| 2 | **Mantenimiento Diario** | Todos los días | 3:00 AM | Limpia cache, optimiza base de datos |
| 3 | **Limpieza ZIPs** | Cada 6 horas | - | Elimina archivos ZIP temporales antiguos (>6 horas) |
| 4 | **Notificaciones Vencidas** | Lunes | 8:00 AM | Recordatorio semanal de actividades vencidas |
| 5 | **Verificar Trials** | Todos los días | 5:00 AM | Verifica empresas con periodo de prueba expirado |
| 6 | **Limpieza Notificaciones** | Domingos | 4:00 AM | Limpia notificaciones antiguas (>30 días) |

---

## 🔄 PASOS PARA ACTIVAR

### Paso 1: Subir a GitHub

```bash
cd "C:\Users\LENOVO\OneDrive\Escritorio\sam-2"
git status
git add render.yaml
git commit -m "Agregar Cron Jobs para tareas automáticas (notificaciones, mantenimiento, limpieza)"
git push origin main
```

### Paso 2: Esperar Deploy Automático

1. Render detectará el cambio en `render.yaml` automáticamente
2. Iniciará un nuevo deploy
3. Creará los 6 Cron Jobs automáticamente

⏱️ **Tiempo estimado:** 3-5 minutos

### Paso 3: Verificar en Render Dashboard

1. Ve a: https://dashboard.render.com
2. Selecciona tu aplicación: **sam-metrologia**
3. En el menú lateral, busca la sección **"Cron Jobs"**
4. Deberías ver los 6 cron jobs creados:
   - ✅ notificaciones-diarias
   - ✅ mantenimiento-diario
   - ✅ limpieza-zips
   - ✅ notificaciones-vencidas-semanales
   - ✅ verificar-trials
   - ✅ limpieza-notificaciones

### Paso 4: Probar Manualmente (Opcional)

Para probar que funcionan SIN esperar al horario:

1. En Render Dashboard, ve a "Cron Jobs"
2. Haz clic en **notificaciones-diarias**
3. Clic en botón **"Trigger Job Manually"** o **"Run Now"**
4. Espera unos segundos
5. Ve a la pestaña **"Logs"** para ver el resultado

---

## 📊 MONITOREAR EJECUCIONES

### Ver Logs de un Cron Job

1. Dashboard Render > Cron Jobs
2. Clic en el cron job que quieres ver
3. Pestaña **"Logs"**
4. Verás cada ejecución con fecha, hora y resultado

### Ver Última Ejecución

En cada Cron Job verás:
- **Last Run**: Cuándo se ejecutó por última vez
- **Status**: succeeded / failed
- **Duration**: Cuánto tardó
- **Next Run**: Cuándo se ejecutará la próxima vez

### Alertas de Errores

Si un cron job falla:
- Render te enviará un email de notificación
- Verás el estado "failed" en el dashboard
- Los logs mostrarán el error

---

## ⚠️ IMPORTANTE: NOTIFICACIONES

**¿Por qué no llegan notificaciones?**

Las notificaciones SOLO se envían cuando hay equipos con actividades próximas:
- Vencen en **15 días**
- Vencen en **7 días**
- Vencen **HOY** (0 días)
- Ya están **vencidas**

**Problema actual:**
- Empresa "prueba": Próxima calibración en 335 días (2026-09-23)
- Empresas test: Sin fechas configuradas

**Solución:**
Para probar notificaciones, crea equipos con fechas en 7 días desde hoy:
- Hoy: 2025-10-23
- Crear equipo con próxima calibración: 2025-10-30 (en 7 días)
- Al día siguiente recibirás notificación automáticamente a las 8:00 AM

---

## 🧪 PROBAR NOTIFICACIONES AHORA (Sin Esperar)

### Opción 1: Ejecutar Manualmente desde Render

1. Render Dashboard > Cron Jobs
2. Clic en "notificaciones-diarias"
3. Clic "Trigger Job Manually"
4. Ver logs

Si no llegan emails:
- Verificar configuración EMAIL_HOST_USER y EMAIL_HOST_PASSWORD en Render
- Verificar que haya equipos con fechas próximas (15, 7, 0 días)

### Opción 2: Forzar Envío (Ignorar Fechas)

Desde tu computadora local:
```bash
cd "C:\Users\LENOVO\OneDrive\Escritorio\sam-2"
python manage.py send_notifications --type consolidated
```

Este comando enviará notificaciones SIN importar las fechas (para testing).

---

## 🔧 COMANDOS ÚTILES

### Ver Estado de Cron Jobs desde API

```bash
# Obtener info de tu aplicación
curl https://api.render.com/v1/services \
  -H "Authorization: Bearer TU_API_KEY"
```

### Probar Comandos Localmente

```bash
cd "C:\Users\LENOVO\OneDrive\Escritorio\sam-2"

# Notificaciones
python manage.py send_notifications --type consolidated

# Mantenimiento
python manage.py run_scheduled_tasks --force

# Limpieza ZIPs
python manage.py cleanup_zip_files --older-than-hours 6

# Verificar trials
python manage.py check_trial_expiration

# Limpieza notificaciones
python manage.py cleanup_notifications --days 30
```

---

## 📅 HORARIOS (Hora Colombia)

```
03:00 AM - Mantenimiento diario
05:00 AM - Verificar trials expirados
08:00 AM - Notificaciones diarias

Cada 6 horas - Limpieza de archivos ZIP

Lunes 08:00 AM - Notificaciones vencidas semanales
Domingo 04:00 AM - Limpieza de notificaciones antiguas
```

---

## ❓ PREGUNTAS FRECUENTES

### ¿Los cron jobs consumen del plan Free de Render?

No, los cron jobs en el plan Free son **completamente gratis**.

### ¿Cuántos cron jobs puedo tener?

- **Free:** Hasta 10 cron jobs
- **Starter ($7/mes):** Ilimitados

### ¿Qué pasa si falla un cron job?

- Render intentará ejecutarlo nuevamente
- Te enviará un email de notificación
- Verás el error en los logs

### ¿Puedo cambiar los horarios?

Sí, edita el archivo `render.yaml`:

```yaml
schedule: "0 13 * * *"  # Hora en formato cron
```

**Formato:**
```
0 13 * * *
│  │ │ │ │
│  │ │ │ └─ Día de la semana (0-6) (0 = Domingo)
│  │ │ └─── Mes (1-12)
│  │ └───── Día del mes (1-31)
│  └─────── Hora (0-23) en UTC
└────────── Minuto (0-59)
```

**Ejemplos:**
```yaml
"0 8 * * *"     # Diario a las 8:00 UTC
"0 */6 * * *"   # Cada 6 horas
"0 9 * * 1"     # Lunes a las 9:00 UTC
"0 10 1 * *"    # Día 1 de cada mes a las 10:00 UTC
```

**⚠️ Recuerda:** Render usa **UTC**. Colombia es **UTC-5**.
```
Hora Colombia + 5 horas = Hora UTC
8:00 AM Colombia = 13:00 UTC
```

### ¿Cómo desactivo un cron job?

**Opción 1: Eliminar del render.yaml**
- Elimina el bloque del cron job
- Haz commit y push
- Render lo eliminará automáticamente

**Opción 2: Suspender desde Dashboard**
- Render Dashboard > Cron Jobs
- Clic en el job
- Botón "Suspend" o "Disable"

---

## ✅ CHECKLIST

Después de subir a GitHub:

- [ ] Subido render.yaml a GitHub (`git push`)
- [ ] Esperado 3-5 minutos para deploy
- [ ] Verificado que aparecen 6 cron jobs en Render Dashboard
- [ ] Probado manualmente un cron job ("Trigger Manually")
- [ ] Verificado logs sin errores
- [ ] Esperado 24 horas y verificado que se ejecutan automáticamente
- [ ] Confirmado que llegan notificaciones (si hay equipos con fechas próximas)

---

## 🆘 SOLUCIÓN DE PROBLEMAS

### No aparecen los cron jobs en Render

1. Verificar que `render.yaml` está en la raíz del repositorio
2. Verificar sintaxis YAML (espaciado correcto)
3. Forzar nuevo deploy: Dashboard > Manual Deploy

### Cron job falla con "Command not found"

- Verificar que el comando existe: `python manage.py send_notifications --help`
- Verificar que `manage.py` tiene permisos de ejecución

### No llegan notificaciones

1. Verificar EMAIL_HOST_USER y EMAIL_HOST_PASSWORD en Render
2. Verificar que hay equipos con fechas en 15, 7 o 0 días
3. Ver logs del cron job para errores
4. Probar manualmente: `python manage.py send_notifications --type consolidated`

### Error de base de datos en cron job

- Verificar que DATABASE_URL está configurado en envVars del cron job
- Verificar migraciones aplicadas: `python manage.py migrate`

---

## 📞 SOPORTE

Si necesitas ayuda:
- WhatsApp: +57 324 7990534
- Email: metrologiasam@gmail.com
- Render Support: https://render.com/docs/cronjobs

---

**¿Listo para activar?** Ejecuta el Paso 1 (subir a GitHub) 🚀
