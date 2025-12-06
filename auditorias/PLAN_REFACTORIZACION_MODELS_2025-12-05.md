# PLAN DE REFACTORIZACIÓN - models.py
**SAM Metrología**
**Fecha:** 5 de Diciembre de 2025
**Objetivo:** Dividir models.py (3,214 líneas) en módulos manejables
**Prioridad:** ALTA - Mejora mantenibilidad

---

## SITUACIÓN ACTUAL

**Archivo:** `core/models.py` - 3,214 líneas
**Problema:** Archivo monolítico muy difícil de navegar y mantener

**Modelos identificados (24 clases):**
1. Empresa (línea 68)
2. PlanSuscripcion (línea 825)
3. CustomUser (línea 852)
4. Unidad (línea 1053)
5. Ubicacion (línea 1067)
6. Procedimiento (línea 1092)
7. Proveedor (línea 1123)
8. Equipo (línea 1159)
9. Calibracion (línea 1430)
10. Mantenimiento (línea 1494)
11. Comprobacion (línea 1585)
12. BajaEquipo (línea 1666)
13. Documento (línea 1693)
14. ZipRequest (línea 1893)
15. NotificacionZip (línea 1973)
16. EmailConfiguration (línea 2008)
17. SystemScheduleConfig (línea 2234)
18. MetricasEficienciaMetrologica (línea 2437)
19. NotificacionVencimiento (línea 2681)
20. TerminosYCondiciones (línea 2792)
21. AceptacionTerminos (línea 2859)
22. MaintenanceTask (línea 2977)
23. CommandLog (línea 3083)
24. SystemHealthCheck (línea 3126)

**Funciones auxiliares:**
- `meses_decimales_a_relativedelta()` (línea 29)

---

## ESTRATEGIA DE DIVISIÓN

### Enfoque: División por Dominio Funcional

Agrupar modelos relacionados en archivos temáticos:

```
core/
├── models.py (ACTUAL - 3,214 líneas) ❌
└── models/ (NUEVO) ✅
    ├── __init__.py           # Exporta todos los modelos
    ├── base.py               # Imports y funciones auxiliares
    ├── empresa.py            # Empresa, PlanSuscripcion
    ├── usuario.py            # CustomUser
    ├── equipo.py             # Equipo
    ├── actividades.py        # Calibracion, Mantenimiento, Comprobacion
    ├── catalogos.py          # Unidad, Ubicacion, Procedimiento, Proveedor
    ├── documentos.py         # Documento, BajaEquipo
    ├── zip_system.py         # ZipRequest, NotificacionZip
    ├── configuracion.py      # EmailConfiguration, SystemScheduleConfig
    ├── metricas.py           # MetricasEficienciaMetrologica
    ├── notificaciones.py     # NotificacionVencimiento
    ├── terminos.py           # TerminosYCondiciones, AceptacionTerminos
    └── sistema.py            # MaintenanceTask, CommandLog, SystemHealthCheck
```

---

## PLAN DETALLADO DE MIGRACIÓN

### Fase 1: Preparación (SEGURO)
1. ✅ Crear directorio `core/models/`
2. ✅ Crear archivo `core/models/base.py` con imports y helpers
3. ✅ Crear archivo `core/models/__init__.py` vacío

### Fase 2: División de Modelos (POR ETAPAS)

#### Etapa 1: Modelos Independientes (Sin Foreign Keys complejas)
**Archivo:** `core/models/catalogos.py`
```python
# Modelos:
- Unidad
- Ubicacion
- Procedimiento
- Proveedor
```
**Razón:** Modelos simples, pocas dependencias

#### Etapa 2: Empresa y Suscripciones
**Archivo:** `core/models/empresa.py`
```python
# Modelos:
- Empresa
- PlanSuscripcion
```

#### Etapa 3: Usuario
**Archivo:** `core/models/usuario.py`
```python
# Modelos:
- CustomUser
```

#### Etapa 4: Equipo (CRÍTICO - Muchas relaciones)
**Archivo:** `core/models/equipo.py`
```python
# Modelos:
- Equipo
```

#### Etapa 5: Actividades Metrológicas
**Archivo:** `core/models/actividades.py`
```python
# Modelos:
- Calibracion
- Mantenimiento
- Comprobacion
```

#### Etapa 6: Documentos
**Archivo:** `core/models/documentos.py`
```python
# Modelos:
- Documento
- BajaEquipo
```

#### Etapa 7: Sistema ZIP
**Archivo:** `core/models/zip_system.py`
```python
# Modelos:
- ZipRequest
- NotificacionZip
```

#### Etapa 8: Configuración
**Archivo:** `core/models/configuracion.py`
```python
# Modelos:
- EmailConfiguration
- SystemScheduleConfig
```

#### Etapa 9: Métricas y Notificaciones
**Archivo:** `core/models/metricas.py`
```python
# Modelos:
- MetricasEficienciaMetrologica
```

**Archivo:** `core/models/notificaciones.py`
```python
# Modelos:
- NotificacionVencimiento
```

#### Etapa 10: Términos y Sistema
**Archivo:** `core/models/terminos.py`
```python
# Modelos:
- TerminosYCondiciones
- AceptacionTerminos
```

**Archivo:** `core/models/sistema.py`
```python
# Modelos:
- MaintenanceTask
- CommandLog
- SystemHealthCheck
```

### Fase 3: Actualización de __init__.py
Exportar todos los modelos para mantener compatibilidad:
```python
from .base import meses_decimales_a_relativedelta
from .empresa import Empresa, PlanSuscripcion
from .usuario import CustomUser
from .equipo import Equipo
from .actividades import Calibracion, Mantenimiento, Comprobacion
from .catalogos import Unidad, Ubicacion, Procedimiento, Proveedor
from .documentos import Documento, BajaEquipo
from .zip_system import ZipRequest, NotificacionZip
from .configuracion import EmailConfiguration, SystemScheduleConfig
from .metricas import MetricasEficienciaMetrologica
from .notificaciones import NotificacionVencimiento
from .terminos import TerminosYCondiciones, AceptacionTerminos
from .sistema import MaintenanceTask, CommandLog, SystemHealthCheck

__all__ = [
    'meses_decimales_a_relativedelta',
    'Empresa', 'PlanSuscripcion',
    'CustomUser',
    'Equipo',
    'Calibracion', 'Mantenimiento', 'Comprobacion',
    'Unidad', 'Ubicacion', 'Procedimiento', 'Proveedor',
    'Documento', 'BajaEquipo',
    'ZipRequest', 'NotificacionZip',
    'EmailConfiguration', 'SystemScheduleConfig',
    'MetricasEficienciaMetrologica',
    'NotificacionVencimiento',
    'TerminosYCondiciones', 'AceptacionTerminos',
    'MaintenanceTask', 'CommandLog', 'SystemHealthCheck',
]
```

### Fase 4: Migración del Archivo Original
1. ✅ Renombrar `core/models.py` a `core/models_OLD_BACKUP.py`
2. ✅ Verificar imports en toda la aplicación
3. ✅ Ejecutar `python manage.py check`
4. ✅ Ejecutar `python manage.py makemigrations` (no debería crear migraciones)
5. ✅ Probar servidor de desarrollo

### Fase 5: Limpieza Final
1. ✅ Si todo funciona correctamente, eliminar `models_OLD_BACKUP.py`
2. ✅ Actualizar documentación
3. ✅ Crear entrada en auditorías

---

## COMPATIBILIDAD GARANTIZADA

### Imports Actuales NO Cambian
```python
# ANTES (funcionará igual):
from core.models import Equipo, Calibracion, Empresa

# DESPUÉS (MISMO resultado):
from core.models import Equipo, Calibracion, Empresa
```

**Razón:** `core/models/__init__.py` re-exporta todo

### Migraciones NO Afectadas
- Django detecta modelos por `app_label` y nombre de clase
- NO importa en qué archivo estén físicamente
- NO se crearán migraciones nuevas

### Admin NO Afectado
```python
# core/admin.py (sin cambios necesarios)
from core.models import Equipo  # Funciona igual
```

---

## RIESGOS Y MITIGACIONES

### Riesgo 1: Imports Circulares
**Problema:** Modelo A importa Modelo B que importa Modelo A
**Mitigación:**
- Usar imports dentro de métodos cuando sea necesario
- Usar `'app.Model'` (string) en ForeignKey si hay dependencia circular

### Riesgo 2: Signals No Se Registran
**Problema:** Signals definidos en archivos no importados
**Mitigación:**
- Mover signals a archivos separados (`core/signals.py`)
- Importar en `core/apps.py` para garantizar registro

### Riesgo 3: Orden de Importación
**Problema:** Modelo base debe importarse antes que derivados
**Mitigación:**
- Orden correcto en `__init__.py` (base primero)
- Funciones auxiliares en `base.py`

---

## VALIDACIÓN POST-MIGRACIÓN

### Checklist de Verificación:
- [ ] `python manage.py check` sin errores
- [ ] `python manage.py makemigrations` sin migraciones nuevas
- [ ] `python manage.py runserver` inicia correctamente
- [ ] Admin de Django accesible
- [ ] Crear equipo desde interfaz funciona
- [ ] Dashboard carga correctamente
- [ ] Exportar Excel funciona
- [ ] Sistema ZIP funciona

---

## BENEFICIOS ESPERADOS

### Antes:
```
core/models.py - 3,214 líneas ❌
- Difícil de navegar
- Búsqueda lenta
- Confusión entre modelos
```

### Después:
```
core/models/
├── base.py              ~50 líneas
├── empresa.py           ~800 líneas
├── usuario.py           ~200 líneas
├── equipo.py            ~300 líneas
├── actividades.py       ~350 líneas
├── catalogos.py         ~150 líneas
├── documentos.py        ~250 líneas
├── zip_system.py        ~200 líneas
├── configuracion.py     ~450 líneas
├── metricas.py          ~250 líneas
├── notificaciones.py    ~120 líneas
├── terminos.py          ~150 líneas
├── sistema.py           ~250 líneas
└── __init__.py          ~40 líneas
```

✅ **Archivos más pequeños y manejables**
✅ **Fácil encontrar un modelo específico**
✅ **Mejor organización lógica**
✅ **Más fácil para nuevos desarrolladores**

---

## ESTIMACIÓN DE TIEMPO

**Total estimado:** 2-3 horas

- Fase 1: 15 minutos
- Fase 2: 90 minutos (10 etapas)
- Fase 3: 10 minutos
- Fase 4: 30 minutos (verificación)
- Fase 5: 15 minutos

---

## DECISIÓN REQUERIDA

¿Proceder con esta refactorización?

**Opciones:**
1. ✅ **Sí, proceder ahora** - Refactorizar models.py completo
2. 🔄 **Fase piloto primero** - Comenzar solo con catalogos.py como prueba
3. ❌ **Posponer** - Dejar para más adelante

---

**FIN DEL PLAN DE REFACTORIZACIÓN**
