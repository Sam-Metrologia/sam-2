# Configurar Tareas Automáticas - SAM Metrología

## 🎯 Objetivo
Ejecutar automáticamente:
- Limpieza de cache (diaria 3:00 AM)
- Notificaciones (diaria 8:00 AM)
- Backups (mensual)
- Limpieza de archivos (diaria)

---

## 📍 ¿Dónde está tu aplicación?

### Opción A: Producción (Render.com) ⭐ RECOMENDADO
Si tu aplicación está en **Render.com**, usa **Render Cron Jobs** (lo mejor y más confiable)

### Opción B: Local / Servidor Propio (Windows)
Si está en tu computadora Windows o servidor Windows, usa **Programador de Tareas**

### Opción C: Servidor Linux (DigitalOcean, AWS, etc.)
Si está en servidor Linux, usa **crontab**

---

## ⭐ OPCIÓN A: RENDER CRON JOBS (Producción)

### ¿Qué es?
Render ejecuta comandos automáticamente según un horario que tú configures.

### Paso 1: Verificar que estás en Render
- ¿Tu aplicación está en una URL como `https://tu-app.onrender.com`?
- Sí → Continúa con esta opción
- No → Ve a Opción B (Windows) o C (Linux)

### Paso 2: Crear archivo `render.yaml`

**Ubicación:** `C:\Users\LENOVO\OneDrive\Escritorio\sam-2\render.yaml`

**Contenido:**
```yaml
services:
  # Tu aplicación web principal
  - type: web
    name: sam-metrologia
    env: python
    buildCommand: "pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput"
    startCommand: "gunicorn proyecto_c.wsgi:application"
    envVars:
      - key: PYTHON_VERSION
        value: 3.13.7
      - key: SECRET_KEY
        sync: false
      - key: DATABASE_URL
        sync: false

# ⭐ CRON JOBS (Tareas Automáticas)
cronJobs:
  # Notificaciones diarias a las 8:00 AM (hora Colombia)
  - name: notificaciones-diarias
    schedule: "0 13 * * *"  # 13:00 UTC = 8:00 AM Colombia
    command: "python manage.py send_notifications --type consolidated"
    env: python

  # Mantenimiento diario a las 3:00 AM (hora Colombia)
  - name: mantenimiento-diario
    schedule: "0 8 * * *"  # 8:00 UTC = 3:00 AM Colombia
    command: "python manage.py run_scheduled_tasks"
    env: python

  # Limpieza de archivos ZIP cada 6 horas
  - name: limpieza-zips
    schedule: "0 */6 * * *"  # Cada 6 horas
    command: "python manage.py cleanup_zip_files --older-than-hours 6"
    env: python

  # Backup mensual (día 1 de cada mes a las 2:00 AM)
  - name: backup-mensual
    schedule: "0 7 1 * *"  # 7:00 UTC día 1 = 2:00 AM Colombia
    command: "python manage.py backup_data"
    env: python

  # Limpieza de notificaciones antiguas (cada domingo)
  - name: limpieza-notificaciones
    schedule: "0 9 * * 0"  # Domingos 9:00 UTC = 4:00 AM Colombia
    command: "python manage.py cleanup_notifications --days 30"
    env: python

  # Verificación de trials expirados (diaria)
  - name: verificar-trials
    schedule: "0 10 * * *"  # 10:00 UTC = 5:00 AM Colombia
    command: "python manage.py check_trial_expiration"
    env: python
```

### Paso 3: Subir a GitHub

```bash
cd "C:\Users\LENOVO\OneDrive\Escritorio\sam-2"
git add render.yaml
git commit -m "Agregar Render Cron Jobs para tareas automáticas"
git push origin main
```

### Paso 4: Conectar en Render

1. Ve a tu dashboard de Render: https://dashboard.render.com
2. Selecciona tu aplicación "sam-metrologia"
3. Render detectará automáticamente `render.yaml`
4. Los cron jobs se crearán automáticamente
5. Puedes verlos en la pestaña "Cron Jobs"

### Paso 5: Verificar Logs

En Render Dashboard:
- Ve a "Cron Jobs"
- Haz clic en cada job
- Revisa logs de ejecución
- Verifica que se ejecuten correctamente

### 📅 Horarios Configurados

| Tarea | Frecuencia | Hora Colombia | Comando |
|-------|-----------|---------------|---------|
| **Notificaciones** | Diaria | 8:00 AM | `send_notifications` |
| **Mantenimiento** | Diaria | 3:00 AM | `run_scheduled_tasks` |
| **Limpieza ZIPs** | Cada 6 horas | - | `cleanup_zip_files` |
| **Backup** | Mensual (día 1) | 2:00 AM | `backup_data` |
| **Limpieza notif.** | Semanal (domingo) | 4:00 AM | `cleanup_notifications` |
| **Verificar trials** | Diaria | 5:00 AM | `check_trial_expiration` |

### ⚠️ IMPORTANTE: Zonas Horarias

Render usa **UTC**. Colombia está en **UTC-5**.

Para convertir:
```
Hora Colombia → Hora Render (UTC)
8:00 AM      → 13:00 (sumar 5 horas)
3:00 AM      → 8:00 (sumar 5 horas)
```

---

## 🪟 OPCIÓN B: WINDOWS TASK SCHEDULER (Local/Servidor Windows)

Si tu aplicación corre en Windows (tu computadora o servidor Windows).

### Paso 1: Crear Script Batch

**Ubicación:** `C:\Users\LENOVO\OneDrive\Escritorio\sam-2\ejecutar_tareas.bat`

**Contenido:**
```batch
@echo off
REM Script para ejecutar tareas programadas SAM

cd /d "C:\Users\LENOVO\OneDrive\Escritorio\sam-2"

REM Activar entorno virtual si existe
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Ejecutar tareas programadas
python manage.py run_scheduled_tasks >> logs\scheduled_tasks.log 2>&1

REM Limpiar archivos ZIP antiguos
python manage.py cleanup_zip_files --older-than-hours 6 >> logs\cleanup_zips.log 2>&1

echo Tareas ejecutadas: %date% %time% >> logs\task_execution.log
```

### Paso 2: Dar Permisos de Ejecución

1. Clic derecho en `ejecutar_tareas.bat`
2. Propiedades
3. Pestaña "Seguridad"
4. Verificar que tienes permisos de ejecución

### Paso 3: Abrir Programador de Tareas

1. Presiona `Win + R`
2. Escribe: `taskschd.msc`
3. Presiona Enter

### Paso 4: Crear Tarea Programada

#### Tarea 1: Ejecución Diaria de Mantenimiento

**Paso 4.1: Crear Tarea Básica**
1. En Programador de Tareas, clic derecho en "Biblioteca del Programador de tareas"
2. Selecciona "Crear tarea básica..."
3. Nombre: `SAM - Tareas Diarias`
4. Descripción: `Ejecuta notificaciones y mantenimiento diario`
5. Clic "Siguiente"

**Paso 4.2: Desencadenador**
1. Selecciona: "Diariamente"
2. Clic "Siguiente"
3. Hora: `08:00:00` (8:00 AM)
4. Repetir cada: `1 días`
5. Clic "Siguiente"

**Paso 4.3: Acción**
1. Selecciona: "Iniciar un programa"
2. Clic "Siguiente"
3. Programa o script:
   ```
   C:\Users\LENOVO\OneDrive\Escritorio\sam-2\ejecutar_tareas.bat
   ```
4. Iniciar en (opcional):
   ```
   C:\Users\LENOVO\OneDrive\Escritorio\sam-2
   ```
5. Clic "Siguiente"

**Paso 4.4: Finalizar**
1. Marcar: "Abrir el cuadro de diálogo Propiedades para esta tarea al hacer clic en Finalizar"
2. Clic "Finalizar"

**Paso 4.5: Configuración Avanzada**

En la ventana de Propiedades:

**Pestaña "General":**
- ✅ Ejecutar solo cuando el usuario haya iniciado sesión (más fácil)
- ⬜ Ejecutar aunque el usuario no esté conectado (requiere contraseña)
- ✅ Ejecutar con los privilegios más altos

**Pestaña "Desencadenadores":**
- Clic "Editar"
- Configuración avanzada:
  - ✅ Repetir la tarea cada: `6 horas`
  - Durante: `Indefinidamente`
- Clic "Aceptar"

**Pestaña "Condiciones":**
- ⬜ Iniciar la tarea solo si el equipo está conectado a la corriente alterna
- ⬜ Detener si el equipo deja de estar conectado a la corriente alterna
- ⬜ Iniciar la tarea solo si el equipo está inactivo

**Pestaña "Configuración":**
- ✅ Permitir que la tarea se ejecute a petición
- ✅ Ejecutar la tarea lo antes posible después de perder un inicio programado
- ✅ Si la tarea no se ejecuta, reintentar cada: `10 minutos`
- ✅ Intentar hasta: `3 veces`
- Si la tarea ya se está ejecutando: "No iniciar una nueva instancia"

7. Clic "Aceptar"

### Paso 5: Probar Tarea Manualmente

1. En Programador de Tareas, busca tu tarea: `SAM - Tareas Diarias`
2. Clic derecho > "Ejecutar"
3. Espera unos segundos
4. Verifica los logs en:
   ```
   C:\Users\LENOVO\OneDrive\Escritorio\sam-2\logs\scheduled_tasks.log
   ```

### Paso 6: Verificar Ejecución

**Verificar que se ejecutó:**
```bash
cd "C:\Users\LENOVO\OneDrive\Escritorio\sam-2"
type logs\task_execution.log
```

**Verificar logs de tareas:**
```bash
type logs\scheduled_tasks.log
type logs\cleanup_zips.log
```

---

## 🐧 OPCIÓN C: LINUX CRONTAB (Servidor Linux)

Si tu aplicación corre en servidor Linux (DigitalOcean, AWS, etc.)

### Paso 1: Conectarse al Servidor

```bash
ssh usuario@tu-servidor.com
```

### Paso 2: Editar Crontab

```bash
crontab -e
```

### Paso 3: Agregar Tareas

```bash
# SAM Metrología - Tareas Programadas

# Notificaciones diarias a las 8:00 AM
0 8 * * * cd /ruta/a/sam-2 && /ruta/a/venv/bin/python manage.py send_notifications --type consolidated >> /ruta/a/sam-2/logs/cron.log 2>&1

# Mantenimiento diario a las 3:00 AM
0 3 * * * cd /ruta/a/sam-2 && /ruta/a/venv/bin/python manage.py run_scheduled_tasks >> /ruta/a/sam-2/logs/cron.log 2>&1

# Limpieza de ZIPs cada 6 horas
0 */6 * * * cd /ruta/a/sam-2 && /ruta/a/venv/bin/python manage.py cleanup_zip_files --older-than-hours 6 >> /ruta/a/sam-2/logs/cron.log 2>&1

# Backup mensual (día 1 a las 2:00 AM)
0 2 1 * * cd /ruta/a/sam-2 && /ruta/a/venv/bin/python manage.py backup_data >> /ruta/a/sam-2/logs/cron.log 2>&1
```

### Paso 4: Guardar y Salir

- Presiona `Ctrl + X`
- Presiona `Y`
- Presiona `Enter`

### Paso 5: Verificar Crontab

```bash
crontab -l
```

---

## 🧪 PROBAR QUE FUNCIONA

### Prueba 1: Ejecutar Manualmente

```bash
cd "C:\Users\LENOVO\OneDrive\Escritorio\sam-2"
python manage.py run_scheduled_tasks --force
```

**Deberías ver:**
```
🚀 Forzando ejecución de todas las tareas habilitadas...
✅ Tareas ejecutadas: 4
   - maintenance_daily_forced
   - notifications_daily_forced
   - maintenance_weekly_forced
   - notifications_weekly_forced
```

### Prueba 2: Verificar Notificaciones

```bash
python manage.py send_notifications --type consolidated --dry-run
```

**Deberías ver:**
```
Enviando recordatorios consolidados...
   [SIMULADO] Recordatorios consolidados
```

### Prueba 3: Verificar Logs

```bash
# Windows
type logs\sam_info.log

# Linux
tail -f logs/sam_info.log
```

---

## 📊 MONITOREO

### Ver Estado de Tareas (Windows)

1. Abrir Programador de Tareas (`taskschd.msc`)
2. Buscar: `SAM - Tareas Diarias`
3. Pestaña "Historial" (si está habilitada)
4. Ver última ejecución, resultado, código de salida

### Ver Logs de Ejecución

```bash
cd "C:\Users\LENOVO\OneDrive\Escritorio\sam-2"

# Ver log de tareas programadas
type logs\scheduled_tasks.log

# Ver log de limpieza
type logs\cleanup_zips.log

# Ver registro de ejecuciones
type logs\task_execution.log
```

### Verificar en Base de Datos

```bash
cd "C:\Users\LENOVO\OneDrive\Escritorio\sam-2"
python manage.py shell
```

```python
from core.models import MaintenanceTask
from django.utils import timezone
from datetime import timedelta

# Ver últimas 10 tareas ejecutadas
tasks = MaintenanceTask.objects.order_by('-created_at')[:10]
for task in tasks:
    print(f"{task.created_at} - {task.get_task_type_display()} - {task.status}")

# Ver tareas de hoy
today = timezone.now().date()
today_tasks = MaintenanceTask.objects.filter(created_at__date=today)
print(f"\nTareas ejecutadas hoy: {today_tasks.count()}")
```

---

## ❓ PREGUNTAS FRECUENTES

### ¿Cuál opción debo usar?

- ✅ **Render Cron Jobs**: Si está en producción en Render.com (LO MEJOR)
- ✅ **Windows Task Scheduler**: Si está en tu computadora Windows
- ✅ **Linux Crontab**: Si está en servidor Linux propio

### ¿Las tareas se ejecutarán aunque mi computadora esté apagada?

- **Render Cron Jobs**: Sí, siempre se ejecutan (servidor en la nube)
- **Windows Task Scheduler**: NO, la computadora debe estar encendida
- **Linux Crontab en servidor**: Sí, siempre se ejecutan (servidor siempre encendido)

### ¿Cómo sé si las tareas se están ejecutando?

1. Verifica logs en `logs/scheduled_tasks.log`
2. Verifica en base de datos: `MaintenanceTask.objects.count()`
3. Verifica que lleguen notificaciones a los emails

### ¿Puedo cambiar los horarios?

Sí:

**Render (`render.yaml`):**
```yaml
schedule: "0 13 * * *"  # 13:00 UTC = 8:00 AM Colombia
```

**Windows (Programador de Tareas):**
- Clic derecho en la tarea > Propiedades > Desencadenadores > Editar

**Linux (crontab):**
```bash
crontab -e
# Cambiar: 0 8 * * * por otra hora
```

### ¿Las notificaciones se enviarán automáticamente ahora?

Sí, PERO solo si hay equipos con actividades próximas (15, 7 o 0 días).

Si no llegan notificaciones, es porque:
1. Los equipos tienen fechas muy lejanas (2026, 2028)
2. No hay equipos con fechas próximas a vencer

---

## ✅ CHECKLIST FINAL

Después de configurar:

- [ ] Tareas programadas creadas (Render/Windows/Linux)
- [ ] Script ejecutado manualmente y funciona
- [ ] Logs verificados y sin errores
- [ ] Tarea programada probada (ejecutar ahora)
- [ ] Esperado 24 horas y verificado ejecución automática
- [ ] Notificaciones llegando correctamente
- [ ] Archivos ZIP siendo limpiados
- [ ] Backups funcionando (si configurado)

---

## 🆘 PROBLEMAS COMUNES

### "Python no se reconoce como comando"

**Solución:**
En `ejecutar_tareas.bat`, usar ruta completa:
```batch
"C:\Users\LENOVO\AppData\Local\Programs\Python\Python313\python.exe" manage.py run_scheduled_tasks
```

### "No module named django"

**Solución:**
Activar entorno virtual en el script:
```batch
call venv\Scripts\activate.bat
python manage.py run_scheduled_tasks
```

### Tarea no se ejecuta en Windows

**Verificar:**
1. Que la ruta al script sea correcta
2. Que tengas permisos de ejecución
3. Que la tarea esté habilitada
4. Ver "Historial" en Programador de Tareas

### Notificaciones no llegan

**Verificar:**
1. Configuración de email en Django settings
2. Que existan equipos con fechas próximas (15, 7, 0 días)
3. Logs de error: `logs\sam_errors.log`

---

**¿Cuál opción quieres implementar?**
1. Render Cron Jobs (producción)
2. Windows Task Scheduler (local)
3. Linux Crontab (servidor propio)
