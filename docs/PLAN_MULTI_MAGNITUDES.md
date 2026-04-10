# Plan: Soporte Multi-Magnitud en Confirmación Metrológica

**Fecha:** 2026-04-09  
**Estado:** En progreso — implementación local primero  
**Objetivo:** Que un mismo registro de confirmación pueda contener varias variables (ej: multímetro con Tensión DC, Corriente DC, Resistencia), cada una con su propio EMP, puntos de medición y gráfica.

---

## Diseño elegido: Propuesta 2 — Magnitudes dentro de un registro

Un único registro `Calibracion` almacena múltiples magnitudes en el campo JSONField `confirmacion_metrologica_datos`. La UI muestra pestañas, una por variable.

---

## Estructura JSON nueva (v2)

```json
{
  "version": 2,
  "magnitudes": [
    {
      "nombre": "Tensión DC",
      "unidad": "V",
      "emp": 0.5,
      "emp_unidad": "%",
      "puntos_medicion": [
        {"nominal": 1.0, "lectura": 1.003, "incertidumbre": 0.005,
         "error": 0.003, "emp_valor": 0.5, "emp_tipo": "%",
         "emp_absoluto": 0.005, "conformidad": "CUMPLE", "desviacion_abs": 0.003}
      ],
      "resultado": "APTO"
    },
    {
      "nombre": "Corriente DC",
      "unidad": "A",
      "emp": 1.0,
      "emp_unidad": "%",
      "puntos_medicion": [...],
      "resultado": "APTO"
    }
  ],
  "version": 2,
  "fecha_confirmacion": "2026-04-09",
  "desviacion_maxima": 0.003,
  "regla_decision": "guard_band_U",
  "decision": "APTO",
  "responsable": "John Doe",
  "laboratorio": "Lab X",
  "fecha_certificado": "2026-03-01",
  "numero_certificado": "CAL-2026-001",
  "conclusion": {
    "decision": "apto",
    "observaciones": "...",
    "responsable": "John Doe"
  }
}
```

**Compatibilidad hacia atrás:** Si no hay clave `magnitudes` en el JSON guardado,
se trata como una sola magnitud (formato v1).

---

## Archivos a modificar

### 1. `core/templates/core/confirmacion_metrologica.html` (1,448 líneas)

**Cambios en Section 1 (Datos del equipo):**
- Mantener `unidad-equipo` y `emp` / `emp-unidad` como valores por defecto.
- Agregar nota: "Estos valores se usan como default al crear nuevas variables".

**Cambios en Section 3 (Confirmación Metrológica):**
- Agregar barra de pestañas ENCIMA de la tabla de mediciones.
- Cada pestaña = una magnitud. Incluye: nombre (editable en el tab), unidad, EMP.
- Botón "➕ Variable" para agregar nueva magnitud.
- Botón "🗑" para eliminar una magnitud (solo si hay > 1).
- La tabla de mediciones sigue siendo la misma, los datos se "swappean" al cambiar tab.

**Cambios en Section 4 (Conclusión):**
- Mostrar el resultado por magnitud (auto-calculado: APTO si todas las filas cumplen).
- Conclusión general al final.

**Cambios en `guardarPDF()`:**
- Guardar el tab activo antes de recopilar.
- Recopilar array `magnitudes` con todos los datos.
- POST incluye `{ magnitudes: [...], version: 2, ...campos_comunes }`.

**Nueva lógica JS:**
```javascript
// Array que almacena los puntos de cada magnitud
let magnitudesData = [
  { nombre: '', unidad: 'lx', emp: 8, emp_unidad: '%', puntos: [] }
];
let magActiva = 0;  // índice del tab activo

function guardarTabActual() { /* guarda tbody en magnitudesData[magActiva].puntos */ }
function cargarTab(idx) { /* carga magnitudesData[idx].puntos en tbody */ }
function agregarMagnitud() { /* push nuevo entry, crear tab, activar */ }
function eliminarMagnitud(idx) { /* si length>1, splice y re-render tabs */ }
```

---

### 2. `core/views/confirmacion.py`

**`generar_pdf_confirmacion()` (línea ~790):**
- Detectar si POST tiene `magnitudes` o `puntos_medicion` (formato viejo).
- Si `magnitudes`: generar una gráfica por magnitud (`_generar_grafica_confirmacion()`).
- Guardar en `confirmacion_metrologica_datos` con estructura v2.
- Si `puntos_medicion` (viejo): procesar como antes (no romper nada).

**`_preparar_contexto_confirmacion()` (línea ~224):**
- Al pre-llenar datos guardados: detectar v2 (tiene `magnitudes`) o v1.
- Si v2: pasar `magnitudes` al contexto para pre-llenar múltiples tabs.
- Si v1: convertir a `magnitudes[0]` con nombre = '' para UI.

---

### 3. `core/templates/core/confirmacion_metrologica_print.html` (623 líneas)

- Añadir soporte para `magnitudes` en el contexto.
- Si hay `magnitudes`: loop — una sección por magnitud con su tabla y gráfica.
- Si es formato viejo: renderizar como antes (una sola sección).

---

### 4. `core/views/confirmacion.py` — `generar_pdf_confirmacion()`

Pasar `graficas` (lista, una por magnitud) en lugar de `grafica_imagen` (una sola).

---

## Pasos de implementación

1. [x] Analizar estructura actual — HECHO
2. [x] Modificar `confirmacion_metrologica.html`:
   - [x] Agregar barra de pestañas (HTML + campos por tab)
   - [x] JS para manejo de magnitudes (magnitudesData, cargarTab, renderizarTabs, etc.)
   - [x] Actualizar `guardarPDF()` — envía `{version:2, magnitudes:[...]}`
   - [x] DOMContentLoaded: usa `inicializarMagnitudes()` en lugar de `inicializarTabla()`
   - [x] `recalcularTodasFilas()` llama `actualizarResultadoBadge()`
3. [x] Modificar `generar_pdf_confirmacion()` en `confirmacion.py`:
   - [x] Detecta v2 (magnitudes) vs v1 (puntos_medicion)
   - [x] Genera N gráficas (una por magnitud) y las embebe en magnitudes_template
   - [x] Guarda JSON v2 con campos legacy para intervalos de calibración
4. [x] Modificar `_preparar_contexto_confirmacion()`:
   - [x] Construye `magnitudes_template` (v2 desde POST/datos_guardados, v1 como wrapper)
   - [x] Pasa `magnitudes` en `datos_confirmacion_template`
   - [x] `datos_previos_json` ya pasa JSON completo (v2 auto-detectado por JS)
5. [x] Modificar `confirmacion_metrologica_print.html`:
   - [x] Loop `{% for mag in datos_confirmacion.magnitudes %}`
   - [x] Cabecera por magnitud (solo si hay >1)
   - [x] Tabla de medición por magnitud con unidades correctas
   - [x] Gráfica embebida por magnitud (`mag.grafica`)
6. [ ] Prueba manual local:
   - [ ] Confirmación con 1 variable (no rompe nada)
   - [ ] Confirmación con 2+ variables (nueva funcionalidad)
   - [ ] Ver PDF con múltiples secciones
   - [ ] Volver a editar y ver que se pre-llenan los datos
7. [ ] Correr tests: `python -m pytest`
8. [ ] Push a producción (Render)

---

## Decisiones de diseño

- **No se cambia el modelo `Calibracion`** — solo cambia la estructura del JSONField existente.
- **No se crea migración** — el campo JSONField ya existe.
- **Una magnitud = un resultado** — "APTO" solo si TODAS las magnitudes están dentro del EMP.
- **El resultado de la magnitud** se calcula en el JS al vuelo (igual que hoy), no se recalcula en el backend.
- **Intervalos de Calibración** — Por ahora usa solo la primera magnitud para el análisis de deriva (mejora futura: dejar elegir qué magnitud analizar).
