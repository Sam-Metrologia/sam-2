# Instrucciones - Fixes Aplicados (21 Enero 2026)

## Fixes Implementados

### 1. Bug ZIP: Comprobaciones no incluidas (CRITICO)
**Commit:** 363316d
**Problema:** Equipo EQ-0012 con 3 comprobaciones no aparecian en ZIP descargado

**Solucion:**
- Corregido campo inexistente `analisis_interno` → `documento_interno`
- Agregado procesamiento de `comprobacion_pdf` (certificados principales)
- Corregido en `zip_functions.py` y `zip_optimizer.py`

**Nueva estructura de carpetas:**
```
Comprobaciones/
├── Certificados_Comprobacion/  ← NUEVO (comprobacion_pdf)
├── Documentos_Externos/
├── Documentos_Internos/        ← CORREGIDO (antes: Analisis_Internos)
└── Documentos_Generales/
```

### 2. Bug Grafica: Solo muestra 2-3 puntos (CRITICO)
**Commit:** e41c74e
**Problema:** PDF de confirmacion metrologica solo mostraba 2-3 puntos en grafica

**Solucion:**
- Modificado filtro en `_generar_grafica_confirmacion()` (linea 57-59)
- Ahora acepta puntos con nominal Y (error O lectura)
- Calcula error automaticamente si solo tiene lectura
- TODOS los puntos validos se incluyen en la grafica

---

## IMPORTANTE: Pasos para Aplicar los Fixes

### Paso 1: Reiniciar Servidor Django

Los cambios en el codigo Python requieren reiniciar el servidor:

```bash
# 1. Detener servidor (Ctrl+C en la terminal donde corre)
# 2. Reiniciar servidor
python manage.py runserver
```

**Por que es necesario?**
Django carga el codigo Python al inicio. Los cambios en archivos .py NO se aplican hasta reiniciar.

### Paso 2: Generar ZIP NUEVO

**IMPORTANTE:** Los ZIPs generados ANTES del fix NO incluiran las correcciones.

**Para verificar que el fix funciona:**
1. Reinicia el servidor Django (Paso 1)
2. Ve a la pagina de equipos
3. Solicita un ZIP NUEVO para empresa DEMO
4. Descarga el ZIP
5. Extrae y verifica que incluya:
   - Carpeta `Comprobaciones/Certificados_Comprobacion/` con 3 archivos para EQ-0012
   - Carpeta `Mantenimientos/` (vacia si equipo no tiene mantenimientos)

### Paso 3: Probar Confirmacion Metrologica

**Para verificar que la grafica funciona:**
1. Reinicia el servidor Django (Paso 1)
2. Ve a cualquier equipo con calibracion
3. Click en "Confirmacion Metrologica"
4. Completa los datos de los puntos
5. Genera el PDF
6. Verifica que la grafica muestre TODOS los puntos (no solo 2-3)

---

## Tests Disponibles

### Test 1: Validar Comprobaciones en ZIP
```bash
python test_comprobaciones_zip_simple.py
```

Verifica que el codigo NO usa `analisis_interno` y SI procesa `comprobacion_pdf`.

### Test 2: Validar Estructura de ZIP
```bash
python test_zip_estructura.py
```

Muestra la estructura esperada del ZIP y verifica que el codigo este correcto.

---

## Diagnostico de Problemas

### Problema: "ZIP aun no incluye comprobaciones"

**Posibles causas:**
1. Servidor Django no reiniciado → REINICIAR SERVIDOR
2. Descargando ZIP viejo generado antes del fix → GENERAR ZIP NUEVO
3. Procesador asincrono de ZIPs usa version vieja → REINICIAR PROCESADOR

**Solucion:**
```bash
# 1. Detener servidor Django (Ctrl+C)
# 2. Si usas procesador asincrono de ZIPs, detenerlo:
./stop_zip_processor.sh  # Si existe

# 3. Reiniciar servidor Django
python manage.py runserver

# 4. Si usas procesador asincrono, reiniciarlo:
./start_zip_processor.sh  # Si existe

# 5. Generar ZIP NUEVO
```

### Problema: "Grafica aun muestra solo 2-3 puntos"

**Posibles causas:**
1. Servidor Django no reiniciado → REINICIAR SERVIDOR
2. Cache del navegador → LIMPIAR CACHE
3. PDF generado antes del fix → GENERAR PDF NUEVO

**Solucion:**
```bash
# 1. Reiniciar servidor Django
python manage.py runserver

# 2. En el navegador, presionar Ctrl+Shift+R (recarga dura)
# 3. Volver a generar el PDF de confirmacion
```

---

## Verificacion del Fix

### Checklist: ZIP Corregido

- [ ] Servidor Django reiniciado
- [ ] ZIP NUEVO generado (no usar ZIP viejo)
- [ ] ZIP extraido y verificado
- [ ] Carpeta `Comprobaciones/Certificados_Comprobacion/` existe
- [ ] Archivos de comprobacion presentes (si equipo tiene comprobaciones)
- [ ] Carpeta `Mantenimientos/` existe (vacia si no hay mantenimientos)

### Checklist: Grafica Corregida

- [ ] Servidor Django reiniciado
- [ ] Cache del navegador limpiado
- [ ] PDF de confirmacion generado NUEVO
- [ ] Grafica muestra TODOS los puntos (no solo 2-3)
- [ ] Barras de incertidumbre visibles
- [ ] Lineas EMP dibujadas correctamente

---

## Commits Aplicados

```
e41c74e - Fix: Grafica confirmacion metrologica solo muestra 2-3 puntos (21 Enero 2026)
363316d - Fix: Comprobaciones no incluidas en ZIP (bug critico) (21 Enero 2026)
```

Para ver los cambios:
```bash
git show 363316d
git show e41c74e
```

---

## Proximos Pasos (Pendiente)

### 1. Tabla de Confirmacion mas Facil
**Solicitado por usuario:** "me gustaria que la tabla de confirmacion fuera como la de comprobacion, la de comprobacion es mas facil de diligenciar"

**TODO:**
- Revisar tabla de comprobacion actual
- Identificar que la hace "mas facil"
- Aplicar mismo patron a tabla de confirmacion

### 2. Validacion Adicional
**Recomendado:**
- Probar descarga de ZIP con empresa que tenga muchos mantenimientos
- Probar confirmacion metrologica con 10+ puntos
- Verificar que incertidumbres se muestren correctamente

---

## Contacto y Soporte

**Documentacion creada:** 21 de Enero de 2026
**Autor:** Claude Sonnet 4.5 (Anthropic)

**Archivos de referencia:**
- `auditorias/BUGFIX_COMPROBACIONES_ZIP_2026-01-21.md`
- `RESUMEN_BUG_FIX_COMPROBACIONES.md`
- `test_comprobaciones_zip_simple.py`
- `test_zip_estructura.py`
