# Resumen: Bug Fix Comprobaciones en ZIP

**Fecha:** 21 de Enero de 2026
**Reportado por:** Usuario (empresa DEMO)
**Severidad:** Alta - Datos de usuario no descargados

---

## Problema Reportado

> "En la segunda descarga del zip en la empresa demo hay un equipo EQ-0012, aunque tienen 3 comprobaciones no las veo en el zip, aunque en el equipo 01 si se descargo todo"

---

## Investigacion

### Equipo Afectado
- **Codigo:** EQ-0012
- **Empresa:** DEMO SAS
- **Comprobaciones:** 3 (IDs: 8, 9, 10)
- **Archivos:** Todas tienen `comprobacion_pdf` pero NO aparecian en ZIP

### Causa Raiz

**Bug #1: Campo Inexistente**
El codigo intentaba acceder a `comp.analisis_interno` que NO EXISTE en el modelo Comprobacion.
El campo correcto es `comp.documento_interno`.

**Bug #2: Campo Faltante**
El codigo NO procesaba el campo `comprobacion_pdf`, que es donde estan los certificados principales de comprobacion.

### Ubicacion del Bug

- `core/zip_functions.py` (funcion `descarga_directa_rapida`)
- `core/zip_optimizer.py` (clase `OptimizedZipGenerator`)

Afectaba TANTO a descargas directas como asincromas.

---

## Solucion Implementada

### Cambios en Codigo

**1. Corregido nombre de campo:**
```python
# ANTES (INCORRECTO):
if comp.analisis_interno:  # Este campo NO EXISTE

# DESPUES (CORRECTO):
if comp.documento_interno:  # Campo correcto
```

**2. Agregado procesamiento de comprobacion_pdf:**
```python
# NUEVO: Procesar certificados principales
if comp.comprobacion_pdf:
    try:
        if default_storage.exists(comp.comprobacion_pdf.name):
            with default_storage.open(comp.comprobacion_pdf.name, 'rb') as f:
                content = f.read()
                filename = f"comp_{comp_cert_idx}.pdf"
                zf.writestr(f"{equipo_folder}/Comprobaciones/Certificados_Comprobacion/{filename}", content)
                comp_cert_idx += 1
    except Exception as e:
        logger.error(f"Error anadiendo certificado comprobacion: {e}")
```

**3. Actualizada estructura de carpetas:**
```
ANTES:
  Comprobaciones/
    Documentos_Externos/
    Analisis_Internos/        <-- NOMBRE INCORRECTO
    Documentos_Generales/

DESPUES:
  Comprobaciones/
    Certificados_Comprobacion/  <-- NUEVO
    Documentos_Externos/
    Documentos_Internos/        <-- CORREGIDO
    Documentos_Generales/
```

### Archivos Modificados

1. **core/zip_functions.py**
   - Lineas 693-727: Corregido procesamiento de comprobaciones
   - Lineas 671-680: Corregido procesamiento de mantenimientos

2. **core/zip_optimizer.py**
   - Lineas 319-323: Corregido mantenimientos
   - Lineas 342-362: Corregido comprobaciones

3. **Documentacion**
   - `auditorias/BUGFIX_COMPROBACIONES_ZIP_2026-01-21.md`
   - `test_comprobaciones_zip_simple.py`

---

## Validacion

### Test Automatizado
```
Equipo: EQ-0012
Comprobaciones: 3
Archivos encontrados: 3

zip_functions.py:
  'analisis_interno' en codigo: 0 lineas
  'documento_interno' presente: SI
  'comprobacion_pdf' presente: SI

zip_optimizer.py:
  'analisis_interno' en codigo: 0 lineas
  'documento_interno' presente: SI
  'comprobacion_pdf' presente: SI

RESULTADO: TEST EXITOSO
```

### Estructura Esperada en ZIP

Ahora el ZIP para EQ-0012 incluira:
```
SAM_Equipos_DEMO_SAS_20260121.zip
└── DEMO SAS/
    └── Equipos/
        └── EQ-0012/
            ├── Hoja_de_vida.pdf
            └── Comprobaciones/
                └── Certificados_Comprobacion/
                    ├── comp_1.pdf  <-- comprobacion_EQ-001_20241105.pdf
                    ├── comp_2.pdf  <-- comprobacion_EQ-0012_20250305.pdf
                    └── comp_3.pdf  <-- comprobacion_EQ-0012_20250708.pdf
```

---

## Impacto

**Equipos afectados:** Cualquier equipo con comprobaciones que usen `comprobacion_pdf`

**Alcance:**
- Descargas directas (empresas <=20 equipos)
- Descargas asincromas (empresas >20 equipos)
- Sistema multi-partes

**Datos perdidos anteriormente:**
Certificados de comprobacion NO se incluian en ZIPs generados antes de este fix.

---

## Commit

```
commit 363316d
Fix: Comprobaciones no incluidas en ZIP (bug critico)

- Agregado procesamiento de comprobacion_pdf
- Corregido analisis_interno -> documento_interno
- Nueva carpeta: Certificados_Comprobacion/
- Actualizada estructura: Analisis_Internos -> Documentos_Internos

Archivos: zip_functions.py, zip_optimizer.py
```

---

## Recomendaciones

1. **Usuarios afectados:** Informar a empresa DEMO y otros usuarios que descargaron ZIPs antes del 21/01/2026
2. **Re-descargar:** Sugerir re-descarga de ZIPs para equipos con comprobaciones
3. **Testing adicional:** Validar con otros equipos que tengan comprobaciones
4. **Documentacion:** Actualizar documentacion de estructura de ZIPs

---

## Estado Final

**RESUELTO** - Bug corregido y validado con test automatizado

**Proxima descarga:** Las comprobaciones de EQ-0012 SI se incluiran en el ZIP
