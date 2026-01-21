# Solución: CB-003 Comprobaciones No Aparecen en ZIP

## Diagnóstico Completado ✅

He verificado el equipo CB-003 y confirmé que:

### Estado del Archivo
- ✅ Comprobación ID 52 existe
- ✅ Archivo `comprobacion_CB-003_20260105.pdf` existe (65,320 bytes)
- ✅ Archivo puede ser leído sin errores
- ✅ Archivo puede ser escrito en ZIP sin problemas
- ✅ Código de `zip_functions.py` está CORRECTO

### El Problema
**El servidor Django tiene la versión VIEJA del código en memoria.**

Aunque hayas reiniciado 3 veces, hay dos posibles causas:

1. **Múltiples procesos de Django corriendo** (el viejo sigue activo)
2. **Caché de módulos Python** no se está limpiando

---

## Solución Paso a Paso

### Opción 1: Reinicio Completo (RECOMENDADO)

#### Paso 1: Verificar procesos activos
```batch
# En Windows, ejecuta:
VERIFICAR_SERVIDOR_DJANGO.bat

# O manualmente:
tasklist | findstr /i "python"
```

Si ves MÚLTIPLES procesos de `python.exe`, necesitas **matarlos TODOS**.

#### Paso 2: Terminar TODOS los procesos de Django

**Método A - Task Manager:**
1. Presiona `Ctrl+Shift+Esc`
2. Busca TODOS los procesos llamados `python.exe` o `Python`
3. Click derecho → "End Task" en CADA UNO
4. Cierra Task Manager

**Método B - Línea de comandos:**
```batch
# CUIDADO: Esto cierra TODOS los procesos de Python
taskkill /F /IM python.exe
```

#### Paso 3: Limpiar caché de Python
```bash
# En la carpeta del proyecto:
cd C:\Users\LENOVO\OneDrive\Escritorio\sam-2

# Eliminar archivos .pyc
del /s /q *.pyc

# Eliminar carpetas __pycache__
for /d /r . %d in (__pycache__) do @if exist "%d" rd /s /q "%d"
```

#### Paso 4: Reiniciar servidor desde CERO
```bash
# Iniciar servidor limpio
python manage.py runserver
```

#### Paso 5: Generar ZIP NUEVO
1. **NO uses ningún ZIP descargado antes**
2. Ve a la página de equipos
3. Solicita un ZIP **completamente NUEVO**
4. Descarga el ZIP
5. Extrae y verifica:
   ```
   DEMO SAS/
     Equipos/
       CB-003/
         Comprobaciones/
           Certificados_Comprobacion/
             comp_1.pdf  <-- DEBE ESTAR AQUÍ
         Mantenimientos/
           Documentos_Generales/
             mantenimiento_CB-003_20260121.pdf
   ```

---

### Opción 2: Reinicio con Limpieza Forzada

Si Opción 1 no funciona, haz una limpieza más agresiva:

```bash
# 1. Detener servidor (Ctrl+C)

# 2. Limpiar TODO el caché de Python
python -c "import sys; import os; [os.remove(os.path.join(root, f)) for root, dirs, files in os.walk('.') for f in files if f.endswith('.pyc')]"

# 3. Eliminar carpetas __pycache__
for /d /r . %d in (__pycache__) do @if exist "%d" rd /s /q "%d"

# 4. Reiniciar Python Shell para limpiar imports
exit

# 5. Abrir CMD/Terminal NUEVO

# 6. Iniciar servidor
cd C:\Users\LENOVO\OneDrive\Escritorio\sam-2
python manage.py runserver
```

---

## Cómo Verificar Que Funcionó

### Test 1: Verificar que el código nuevo se cargó

Después de reiniciar el servidor, ejecuta:
```bash
python test_cb003_zip.py
```

Debe mostrar:
```
Codigo de Comprobaciones:
  - Procesa comprobacion_pdf: SI
  - Usa default_storage.exists: SI
  - Usa writestr: SI
```

### Test 2: Verificar ZIP

1. Genera ZIP NUEVO para empresa DEMO
2. Extrae el ZIP
3. Navega a: `DEMO SAS/Equipos/CB-003/Comprobaciones/Certificados_Comprobacion/`
4. **DEBE contener:** `comp_1.pdf` (65 KB)

---

## Diferencia: Mantenimiento SÍ vs Comprobación NO

### Por qué el mantenimiento funciona:
El campo `documento_mantenimiento` estaba ANTES del fix, por lo que el código viejo ya lo procesaba.

### Por qué la comprobación NO funciona:
El campo `comprobacion_pdf` fue AGREGADO en el fix (commit 363316d), por lo que el código viejo NO lo procesaba.

**Esto confirma que el servidor está usando código VIEJO.**

---

## Solución Definitiva

Si nada de lo anterior funciona, es posible que estés usando un servidor con deployment especial (Gunicorn, uWSGI, etc.). En ese caso:

```bash
# Si usas Gunicorn:
pkill gunicorn
gunicorn proyecto_c.wsgi:application

# Si usas uWSGI:
pkill uwsgi
uwsgi --ini uwsgi.ini

# Si usas systemd:
sudo systemctl restart sam-metrologia
```

---

## Resultado Esperado

Después de seguir estos pasos, cuando generes un ZIP NUEVO:

```
CB-003/
  ├── Hoja_de_vida.pdf
  ├── Comprobaciones/
  │   └── Certificados_Comprobacion/
  │       └── comp_1.pdf  ← ¡DEBE APARECER!
  └── Mantenimientos/
      └── Documentos_Generales/
          └── mantenimiento_CB-003_20260121.pdf
```

---

## Si Aún No Funciona

Ejecuta el diagnóstico completo:
```bash
python test_cb003_zip.py
```

Y envíame la salida completa. También verifica:

1. ¿Qué mensaje aparece cuando inicias el servidor?
2. ¿Hay algún error en la consola?
3. ¿Estás usando desarrollo (`runserver`) o producción (Gunicorn/uWSGI)?

---

**Archivos de ayuda creados:**
- `test_cb003_zip.py` - Diagnóstico completo
- `VERIFICAR_SERVIDOR_DJANGO.bat` - Verificar procesos
- `SOLUCION_CB003_COMPROBACIONES.md` - Este archivo
