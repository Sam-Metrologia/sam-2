# 🐛 Bug Fix: Comprobaciones No Incluidas en ZIP

**Fecha:** 21 de Enero de 2026
**Severidad:** 🔴 Alta (datos de usuario no descargados)
**Reportado por:** Usuario (empresa DEMO)

---

## 📋 Descripción del Problema

**Reporte del usuario:**
> "En la segunda descarga del zip en la empresa demo hay un equipo EQ-0012, aunque tienen 3 comprobaciones no las veo en el zip, aunque en el equipo 01 si se descargo todo"

### Investigación

**Equipo afectado:** EQ-0012 (Empresa: DEMO SAS)

**Comprobaciones en base de datos:**
```
Comprobacion 8 (2024-11-05):  comprobacion_pdf ✅
Comprobacion 9 (2025-03-05):  comprobacion_pdf ✅
Comprobacion 10 (2025-07-08): comprobacion_pdf ✅
```

Todas las comprobaciones tienen archivos en el campo `comprobacion_pdf`, pero NO aparecían en el ZIP descargado.

---

## 🔍 Análisis de Causa Raíz

### Bug #1: Campo Inexistente
**Ubicación:** `core/zip_functions.py` línea 708

**Código INCORRECTO:**
```python
# Análisis Interno
if comp.analisis_interno:  # ❌ Este campo NO EXISTE
    try:
        if default_storage.exists(comp.analisis_interno.name):
            # ...
```

**Problema:** El modelo `Comprobacion` NO tiene el campo `analisis_interno`. El campo correcto es `documento_interno`.

### Bug #2: Campo Faltante
**Problema:** El código NO procesaba el campo `comprobacion_pdf`, que es donde están los certificados principales de comprobación.

**Campos del modelo Comprobacion:**
- ✅ `comprobacion_pdf` - **Certificado principal (FALTABA)**
- ✅ `documento_externo` - Procesado correctamente
- ❌ `analisis_interno` - NO EXISTE (debería ser `documento_interno`)
- ✅ `documento_comprobacion` - Procesado correctamente

---

## ✅ Solución Implementada

### Cambios en `core/zip_functions.py`

**1. Agregado procesamiento de `comprobacion_pdf`:**
```python
# Comprobación PDF (certificados principales)
if comp.comprobacion_pdf:
    try:
        if default_storage.exists(comp.comprobacion_pdf.name):
            with default_storage.open(comp.comprobacion_pdf.name, 'rb') as f:
                content = f.read()
                filename = f"comp_{comp_cert_idx}.pdf"
                zf.writestr(f"{equipo_folder}/Comprobaciones/Certificados_Comprobacion/{filename}", content)
                comp_cert_idx += 1
    except Exception as e:
        logger.error(f"Error añadiendo certificado comprobación: {e}")
```

**2. Corregido nombre de campo:**
```python
# ANTES (INCORRECTO):
if comp.analisis_interno:

# DESPUÉS (CORRECTO):
if comp.documento_interno:
```

**3. Actualizada carpeta de destino:**
```python
# ANTES:
f"{equipo_folder}/Comprobaciones/Analisis_Internos/{filename}"

# DESPUÉS:
f"{equipo_folder}/Comprobaciones/Documentos_Internos/{filename}"
```

---

## 📂 Estructura de Carpetas

### ANTES (incompleta):
```
Equipos/
  EQ-0012/
    Comprobaciones/
      Documentos_Externos/     (vacío)
      Analisis_Internos/       (ERROR - campo no existe)
      Documentos_Generales/    (vacío)
```

### DESPUÉS (completa):
```
Equipos/
  EQ-0012/
    Comprobaciones/
      Certificados_Comprobacion/   (comp_1.pdf, comp_2.pdf, comp_3.pdf)
      Documentos_Externos/         (si existen)
      Documentos_Internos/         (si existen)
      Documentos_Generales/        (si existen)
```

---

## 🧪 Validación

### Antes del Fix
```
❌ EQ-0012 con 3 comprobaciones → ZIP sin archivos de comprobaciones
✅ EQ-0001 (calibraciones funcionaban correctamente)
```

### Después del Fix
```
✅ EQ-0012 con 3 comprobaciones → ZIP con 3 certificados
✅ EQ-0001 (sin cambios, sigue funcionando)
```

---

## 📊 Impacto

**Equipos afectados:** Cualquier equipo con comprobaciones que usen el campo `comprobacion_pdf`

**Alcance:**
- Función `descarga_directa_rapida()` en `zip_functions.py`
- Afecta descarga de ZIPs para empresas con ≤20 equipos (descarga directa)
- Sistema asíncrono probablemente tiene el mismo bug

**Datos perdidos:** Certificados de comprobación no se incluían en ZIP

---

## ✅ Archivos Modificados

1. `core/zip_functions.py` (líneas 693-727)
   - Agregado procesamiento de `comprobacion_pdf`
   - Corregido `analisis_interno` → `documento_interno`
   - Actualizada estructura de carpetas

---

## 🎯 Próximos Pasos

- [x] Corregir bug en función de descarga directa
- [ ] Verificar si `async_zip_improved.py` tiene el mismo bug
- [ ] Agregar test automatizado para validar comprobaciones en ZIP
- [ ] Actualizar documentación de estructura de ZIP

---

## 📝 Lecciones Aprendidas

1. **Validar nombres de campos:** El código asumía un campo `analisis_interno` que no existía en el modelo
2. **Testing con datos reales:** El bug se descubrió con usuario real (DEMO), no en tests
3. **Documentación de modelos:** Mantener documentación actualizada de campos disponibles
4. **Paridad entre modelos:** Calibraciones usan `confirmacion_metrologica_pdf`, Comprobaciones usan `comprobacion_pdf` - nombres inconsistentes

---

## 🔗 Referencias

- Modelo: `core/models.py` → clase `Comprobacion`
- Vista: `core/zip_functions.py` → función `descarga_directa_rapida()`
- Reporte: Usuario DEMO - equipo EQ-0012
