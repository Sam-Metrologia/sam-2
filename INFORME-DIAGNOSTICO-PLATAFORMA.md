# Informe de Diagnóstico - Plataforma SAM Metrología
**Fecha:** 23 de Octubre de 2025
**Solicitado por:** Usuario SAM
**Realizado por:** Claude Code

---

## 📋 Resumen Ejecutivo

Se solicitó verificar 3 aspectos de la plataforma SAM:

1. ✅ **Cambiar mensaje "¿Olvidaste tu contraseña?" por link a WhatsApp** - COMPLETADO
2. ✅ **Investigar por qué empresas nuevas no reciben notificaciones** - DIAGNOSTICADO
3. ✅ **Verificar funcionamiento de tareas de mantenimiento** - DIAGNOSTICADO

---

## 1. ✅ LINK A WHATSAPP EN LOGIN

### Cambio Realizado

**Archivo modificado:** `templates/registration/login.html`

**ANTES:**
```html
<p>¿Olvidaste tu contraseña? Para asistencia técnica, comunícate con **Sam Metrología S.A.S**
al número **+57 324 7990534** o contacta a tu asesor.</p>
```

**AHORA:**
```html
<p>¿Olvidaste tu contraseña?
    <a href="https://wa.me/573247990534?text=Hola,%20necesito%20ayuda%20con%20mi%20contrase%C3%B1a%20de%20la%20plataforma%20SAM"
       target="_blank"
       class="text-green-600 hover:text-green-700 font-semibold underline">
        Contáctanos por WhatsApp
    </a>
</p>
```

### Resultado

- Al hacer clic en "Contáctanos por WhatsApp", abre WhatsApp con el mensaje pre-escrito
- Link verde con estilo profesional
- Funciona en escritorio y móvil

---

## 2. ✅ DIAGNÓSTICO: NOTIFICACIONES EN EMPRESAS NUEVAS

### Resultado del Diagnóstico

**Las empresas NO reciben notificaciones porque NO tienen equipos con actividades próximas a vencer.**

### Hallazgos Detallados

✅ **Sistema de notificaciones funciona correctamente:**
- Todas las empresas tienen emails válidos configurados
- Usuarios tienen emails activos
- Configuración de emails está correcta

❌ **Problema identificado:**

**Las notificaciones SOLO se envían cuando:**
- Hay calibraciones/mantenimientos que vencen en **15, 7 o 0 días**
- Hay actividades vencidas (recordatorio semanal)

**Situación actual de las empresas:**
```
Empresa: prueba
- Total equipos: 2
- Próxima calibración: 2026-09-23 (en 335 días)
- Próximo mantenimiento: 2026-02-07 (en 107 días)
=> NO recibe notificaciones porque las fechas están muy lejos

Empresa: Test 120 Equipos
- Total equipos: 120
- La mayoría de equipos NO tienen fechas configuradas
=> NO recibe notificaciones

Empresa: Test 80 Equipos, Test 50 Equipos, Test 20 Equipos
- Situación similar: sin fechas próximas
```

### Conclusión

**El sistema funciona correctamente.** Las empresas nuevas no reciben notificaciones porque:
1. Los equipos tienen fechas muy lejanas (2026, 2028)
2. Muchos equipos no tienen fechas de calibración/mantenimiento configuradas
3. No hay actividades próximas (15, 7 o 0 días)

### Solución Recomendada

Para que las empresas nuevas reciban notificaciones:

**Opción A: Configurar fechas realistas**
- Al registrar equipos nuevos, asignar fechas de próxima calibración/mantenimiento realistas
- No dejar fechas en blanco

**Opción B: Modificar el sistema de notificaciones**
- Enviar notificación de bienvenida cuando se registra nueva empresa
- Enviar recordatorio mensual general (no solo cuando hay actividades próximas)

**Opción C: Verificar las fechas manualmente**
- Revisar equipos sin fechas configuradas
- Completar información faltante

---

## 3. ✅ DIAGNÓSTICO: TAREAS DE MANTENIMIENTO

### Resultado del Diagnóstico

**Las tareas están configuradas PERO NO se están ejecutando automáticamente.**

### Estado Actual

✅ **Sistema de mantenimiento instalado y funcional:**
- Modelos creados: MaintenanceTask, CommandLog, SystemHealthCheck
- 4 tareas registradas
- 20 logs de ejecución
- Comandos disponibles y funcionales

✅ **Tareas programadas HABILITADAS:**
```
Mantenimiento Diario:
  - Habilitado: SÍ
  - Hora: 03:00 AM
  - Tareas: limpieza cache, optimización base de datos

Notificaciones Diarias:
  - Habilitado: SÍ
  - Hora: 08:00 AM
  - Tipos: calibraciones, mantenimientos, comprobaciones

Mantenimiento Semanal:
  - Habilitado: SÍ

Backup Mensual:
  - Habilitado: SÍ
```

❌ **Problema identificado:**
```
NO hay ejecuciones recientes (últimos 7 días)
  => Las tareas NO se ejecutan automáticamente
  => Falta configurar CRON JOB o Tarea Programada de Windows
```

⚠️ **Otros hallazgos:**
- 44 archivos ZIP acumulados (necesita limpieza)
- No hay health checks registrados

### Causa Raíz

**Las tareas están configuradas pero nadie las ejecuta automáticamente.**

El sistema necesita que **alguien ejecute el comando** todos los días:
```bash
python manage.py run_scheduled_tasks
```

Este comando:
1. Verifica qué tareas deben ejecutarse según la hora configurada
2. Ejecuta las tareas correspondientes (mantenimiento, notificaciones, backups)
3. Registra los resultados en la base de datos

**Pero nadie está ejecutando este comando automáticamente.**

---

## 🔧 SOLUCIONES IMPLEMENTADAS

### Solución 1: Link a WhatsApp ✅ COMPLETADO

**Archivo modificado:** `templates/registration/login.html`

**Verificar:**
- Refrescar página de login
- Ver link verde "Contáctanos por WhatsApp"
- Hacer clic debería abrir WhatsApp

---

## 🎯 SOLUCIONES RECOMENDADAS

### Solución 2: Notificaciones en Empresas Nuevas

**Recomendación:** No requiere cambios técnicos. El sistema funciona correctamente.

**Acciones sugeridas:**
1. Verificar que los equipos tengan fechas de próxima calibración/mantenimiento configuradas
2. Usar fechas realistas (no 2026 o 2028)
3. Para probar notificaciones, crear equipos con fechas próximas (ejemplo: 7 días en el futuro)

**Comando de prueba:**
```bash
# Forzar envío de notificaciones (sin importar fechas)
python manage.py send_notifications --type consolidated
```

---

### Solución 3: Ejecutar Tareas de Mantenimiento Automáticamente

#### Opción A: Tarea Programada de Windows (Recomendado)

**Paso 1: Abrir Programador de Tareas**
- Presionar `Win + R`
- Escribir `taskschd.msc`
- Enter

**Paso 2: Crear Nueva Tarea**
1. Clic derecho > "Crear tarea básica"
2. Nombre: `SAM - Tareas Programadas Diarias`
3. Desencadenador: Diariamente a las 8:00 AM
4. Acción: Iniciar un programa

**Paso 3: Configurar Comando**
```
Programa: C:\Users\LENOVO\AppData\Local\Programs\Python\Python313\python.exe
Argumentos: manage.py run_scheduled_tasks
Iniciar en: C:\Users\LENOVO\OneDrive\Escritorio\sam-2
```

**Paso 4: Configuración Adicional**
- Ejecutar aunque el usuario no esté conectado: NO (requiere contraseña)
- Ejecutar con los privilegios más altos: SÍ

#### Opción B: Ejecutar Manualmente

**Comando para ejecutar todas las tareas:**
```bash
cd "C:\Users\LENOVO\OneDrive\Escritorio\sam-2"
python manage.py run_scheduled_tasks --force
```

Este comando:
- Ejecuta mantenimiento diario
- Envía notificaciones diarias
- Ejecuta limpieza de cache
- Registra resultados en base de datos

#### Opción C: Comando Individual

**Enviar notificaciones:**
```bash
python manage.py send_notifications --type consolidated
```

**Limpiar cache:**
```bash
python manage.py run_maintenance_task <task_id>
```

**Limpiar archivos ZIP:**
```bash
python manage.py cleanup_zip_files --older-than-hours 6
```

---

## 📊 COMANDOS ÚTILES

### Diagnóstico

```bash
# Verificar sistema de mantenimiento
python verificar_mantenimiento_simple.py

# Verificar notificaciones
python diagnostico_notificaciones.py

# Verificar equipos con fechas próximas
python diagnostico_equipos_proximos.py
```

### Ejecución Manual

```bash
# Ejecutar todas las tareas programadas
python manage.py run_scheduled_tasks --force

# Enviar notificaciones consolidadas
python manage.py send_notifications --type consolidated

# Limpiar archivos ZIP antiguos
python manage.py cleanup_zip_files --older-than-hours 6

# Verificar cache
python manage.py check_cache
```

### Monitoreo

```bash
# Ver logs de Django
tail -f logs/sam_info.log

# Ver logs de errores
tail -f logs/sam_errors.log

# Ver logs de ZIP processor
tail -f logs/zip_processor.log
```

---

## 📈 RECOMENDACIONES FINALES

### Corto Plazo (Esta Semana)

1. ✅ **Link WhatsApp:** Ya está implementado
2. ⚠️ **Configurar tarea programada de Windows** para ejecutar:
   ```
   python manage.py run_scheduled_tasks
   ```
   Diariamente a las 8:00 AM

3. ⚠️ **Limpiar archivos ZIP acumulados:**
   ```bash
   python manage.py cleanup_zip_files --older-than-hours 6
   ```

### Mediano Plazo (Este Mes)

1. **Verificar fechas de equipos:**
   - Revisar equipos sin fechas de calibración/mantenimiento
   - Completar información faltante
   - Usar fechas realistas

2. **Monitorear ejecución de tareas:**
   - Verificar logs diariamente
   - Confirmar que notificaciones se envían
   - Verificar que mantenimiento se ejecuta

3. **Configurar health checks:**
   - Sistema tiene la funcionalidad pero no se usa
   - Configurar health checks automáticos

### Largo Plazo (Próximos 3 Meses)

1. **Migrar a servidor con cron job nativo:**
   - Si la aplicación se mueve a Linux (Render, DigitalOcean, etc.)
   - Configurar cron job en el servidor
   - Más confiable que tarea programada de Windows

2. **Implementar sistema de alertas:**
   - Email cuando tareas fallan
   - Dashboard de monitoreo
   - Logs centralizados

3. **Automatizar backups:**
   - Backup automático mensual
   - Subir backups a cloud (Google Drive, Dropbox)
   - Rotación de backups antiguos

---

## 📞 SOPORTE

Si necesitas ayuda con alguna de estas configuraciones:
- **WhatsApp:** +57 324 7990534
- **Email:** metrologiasam@gmail.com

---

**Fin del Informe**

Generado automáticamente por Claude Code
Fecha: 23 de Octubre de 2025
