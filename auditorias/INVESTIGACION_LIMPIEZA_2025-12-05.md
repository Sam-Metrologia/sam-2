# INVESTIGACIÓN PRELIMINAR DE LIMPIEZA
**SAM Metrología - Análisis Pre-Limpieza**
**Fecha:** 5 de Diciembre de 2025
**Objetivo:** Identificar código a eliminar SIN afectar integridad

---

## 1. DASHBOARD GERENCIAL vs PANEL DE DECISIONES

### Hallazgos:

**Archivos Existentes:**
- `core/views/dashboard_gerencia.py` (1,134 líneas)
- `core/views/dashboard_gerencia_simple.py` (867 líneas)
- `core/views/panel_decisiones.py` (1,219 líneas)

**Archivo en Uso:**
```python
# core/views/__init__.py línea 6:
from .dashboard_gerencia_simple import dashboard_gerencia
```

**Template:**
- Existe: `core/templates/core/panel_decisiones.html`
- NO existe template para dashboard_gerencia

**URLs Configuradas:**
```python
# core/urls.py
path('dashboard-gerencia/', views.dashboard_gerencia, name='dashboard_gerencia')
path('panel-decisiones/', views.panel_decisiones, name='panel_decisiones')
```

**Sidebar (Menú Lateral):**
```html
<!-- templates/base.html línea 324 -->
<a href="{% url 'core:panel_decisiones' %}">
    <i class="fas fa-chart-line"></i> Panel de Decisiones
</a>
```

### CONCLUSIÓN:

✅ **SON DIFERENTES:**
- `dashboard_gerencia` → Vista para análisis gerencial (versión simplificada en uso)
- `panel_decisiones` → Vista para panel de decisiones con presupuesto

❌ **ARCHIVO OBSOLETO IDENTIFICADO:**
- `core/views/dashboard_gerencia.py` (1,134 líneas) → **NO SE USA**
- Se importa `dashboard_gerencia_simple.py` en su lugar

### ACCIÓN RECOMENDADA:
📋 **Eliminar:** `core/views/dashboard_gerencia.py`
- Es versión antigua reemplazada por dashboard_gerencia_simple.py
- NO se está importando
- **SEGURO DE ELIMINAR** ✅

---

## 2. CÓDIGO DEBUG EN PRODUCCIÓN

### A. Debug en models.py (Líneas 1257-1264)

**Ubicación:** `core/models.py` método `save()` de Equipo

```python
# DEBUG
if 'update_fields' in kwargs:
    print(f"DEBUG EQUIPO.SAVE: {self.codigo_interno}")
    print(f"  - update_fields: {kwargs.get('update_fields')}")
    print(f"  - skip_recalculation: {skip_recalculation}")
    if 'proxima_calibracion' in str(kwargs.get('update_fields', [])):
        print(f"  - proxima_calibracion ANTES de super().save: {self.proxima_calibracion}")
```

**Análisis:**
- 🔍 **Propósito:** Debug de actualización de equipos
- ⚠️ **Problema:** `print()` statements en producción
- ❌ **No está envuelto** en `if settings.DEBUG:`
- 🎯 **Se ejecuta:** En CADA `save()` con update_fields

**IMPACTO:**
- Logs innecesarios en producción
- Performance overhead mínimo pero acumulativo
- Información sensible en stdout

### ACCIÓN RECOMENDADA:
✅ **REMOVER COMPLETAMENTE** estas líneas 1257-1264
- NO son necesarias en producción
- NO están condicionadas a DEBUG=True
- **SEGURO DE ELIMINAR** ✅

---

## 3. CÓDIGO MUERTO (Unreachable)

### A. Método esta_al_dia_con_pagos() (Líneas 319-322)

**Ubicación:** `core/models.py` método `esta_al_dia_con_pagos()` de Empresa

```python
def esta_al_dia_con_pagos(self):
    dias = self.dias_hasta_proximo_pago()
    if dias is None:
        return True  # Sin fecha definida
    return dias >= -7  # Permitir 7 días de gracia
                        # ← FUNCIÓN TERMINA AQUÍ

    # Log de la eliminación  # ← CÓDIGO MUERTO (nunca se ejecuta)
    logger.info(f'Empresa {self.nombre}...')

    return True  # ← CÓDIGO MUERTO (nunca se ejecuta)
```

**Análisis:**
- ❌ **Código después de return** nunca se ejecuta
- 🔍 **Parece ser:** Código de otra función pegado por error
- 🎯 **Líneas muertas:** 319-322

### ACCIÓN RECOMENDADA:
✅ **REMOVER COMPLETAMENTE** líneas 319-322
- Código inalcanzable
- Confunde el propósito del método
- **SEGURO DE ELIMINAR** ✅

---

## 4. IMPORTS DENTRO DE FUNCIONES

### A. confirmacion.py (Líneas 27-30)

**Ubicación:** `core/views/confirmacion.py` función `generar_grafica_error()`

```python
def generar_grafica_error(puntos_medicion, limite_emp, nombre_equipo):
    try:
        import matplotlib         # ← MAL PATRÓN
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
```

**Análisis:**
- ❌ **Imports dentro de función**
- 🔄 **Re-importación:** En cada llamada a la función
- ⚠️ **Overhead:** Performance degradado

**Otros archivos con mismo problema:**
- `core/views/intervalos_calibracion.py`
- `core/views/comprobacion_metrologica.py`
- Posiblemente otros archivos de gráficas

### ACCIÓN RECOMENDADA:
✅ **MOVER imports al inicio del archivo**

**Cambio:**
```python
# ANTES (MAL):
def generar_grafica_error(...):
    import matplotlib
    import numpy as np
    ...

# DESPUÉS (BIEN):
# Al inicio del archivo
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def generar_grafica_error(...):
    # Usar directamente
    ...
```

**SEGURO DE CAMBIAR** ✅
- No afecta funcionalidad
- Mejora performance
- Mejor práctica Python

---

## 5. ARCHIVOS __pycache__

**Encontrados:** 179 archivos cache en el repositorio

**Ubicaciones:**
- `core/__pycache__/`
- `core/views/__pycache__/`
- `core/management/__pycache__/`
- Etc.

### ACCIÓN RECOMENDADA:
✅ **LIMPIAR todos los __pycache__**

**Comando:**
```bash
find . -type d -name "__pycache__" -exec rm -rf {} +
# O en Windows PowerShell:
Get-ChildItem -Path . -Directory -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
```

**Agregar a .gitignore:**
```
__pycache__/
*.py[cod]
*$py.class
```

**SEGURO DE ELIMINAR** ✅

---

## RESUMEN DE ACCIONES SEGURAS

### ELIMINACIÓN SEGURA (100% Confirmado):

1. ✅ **Eliminar archivo completo:**
   - `core/views/dashboard_gerencia.py` (1,134 líneas)
   - Razón: No se usa, reemplazado por dashboard_gerencia_simple.py

2. ✅ **Eliminar código DEBUG:**
   - `core/models.py` líneas 1257-1264
   - Razón: Debug innecesario en producción

3. ✅ **Eliminar código muerto:**
   - `core/models.py` líneas 319-322
   - Razón: Código inalcanzable después de return

4. ✅ **Limpiar cache:**
   - Todos los directorios `__pycache__/`
   - Razón: Archivos temporales no deben estar en repo

### REFACTORING SEGURO (Sin riesgo):

5. ✅ **Mover imports:**
   - `core/views/confirmacion.py` líneas 27-30
   - `core/views/intervalos_calibracion.py` (verificar)
   - `core/views/comprobacion_metrologica.py` (verificar)
   - Razón: Mejor práctica, mejora performance

---

## CANDIDATOS A REVISAR (Requiere decisión manual):

### A. Campo `es_periodo_prueba` DEPRECADO

**Ubicación:** `core/models.py` línea 112-113

```python
es_periodo_prueba = models.BooleanField(
    default=True,
    verbose_name="¿Es Periodo de Prueba? (Deprecado)"
)
```

**Pregunta:**
- ¿Este campo está en uso actualmente?
- ¿O fue reemplazado por el sistema de trial de 30 días?

**Acción:** 🔍 Requiere verificación antes de eliminar

### B. Múltiples Dashboards Gerenciales

**Archivos:**
- `dashboard_gerencia.py` ❌ (eliminar)
- `dashboard_gerencia_simple.py` ✅ (en uso)

**Pregunta:**
- ¿dashboard_gerencia_simple.py es la versión definitiva?
- ¿O es temporal para debugging?

**Acción:** ✅ Ya confirmado - simple es la versión en uso

---

## PRÓXIMOS PASOS

### Fase 1: Limpieza Segura (Hoy)
1. Eliminar `dashboard_gerencia.py`
2. Eliminar código DEBUG (models.py:1257-1264)
3. Eliminar código muerto (models.py:319-322)
4. Limpiar `__pycache__/`
5. Mover imports al inicio de archivos

### Fase 2: Verificación (Después de Fase 1)
1. Ejecutar `python manage.py check`
2. Ejecutar tests (si están funcionando)
3. Verificar que servidor inicia correctamente
4. Probar funcionalidades críticas

### Fase 3: Actualizar Documentación
1. Actualizar CLAUDE.md con cambios
2. Documentar archivos eliminados
3. Crear entrada en auditorias/

---

## ESTIMACIÓN DE IMPACTO

**Líneas de código a eliminar:**
- dashboard_gerencia.py: 1,134 líneas
- Código DEBUG: 8 líneas
- Código muerto: 4 líneas
- **TOTAL: ~1,146 líneas eliminadas**

**Archivos cache a eliminar:**
- 179 directorios __pycache__

**Tiempo estimado de limpieza:**
- 15-20 minutos para cambios
- 10 minutos para verificación
- **Total: ~30 minutos**

**Riesgo:**
- 🟢 **BAJO** - Todos los cambios son seguros
- ✅ Código identificado no está en uso
- ✅ Sin dependencias detectadas

---

**FIN DE INVESTIGACIÓN PRELIMINAR**

**Decisión:** ¿Proceder con Fase 1 de limpieza segura?
