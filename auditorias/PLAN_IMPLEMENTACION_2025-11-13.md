# PLAN DE IMPLEMENTACIÓN DETALLADO
## Mejoras Sistema de Metrología SAM
**Fecha:** 13 de Noviembre de 2025
**Basado en:** Auditoría Completa 2025-11-13
**Duración Total Estimada:** 8-10 semanas
**Objetivo:** Pasar de 7.2/10 a 8.5-9/10 en calidad de código

---

## ÍNDICE

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Fase 1: Refactorización Core (Semanas 1-2)](#fase-1-refactorización-core)
3. [Fase 2: Optimización (Semanas 3-4)](#fase-2-optimización)
4. [Fase 3: Infraestructura (Semana 5)](#fase-3-infraestructura)
5. [Fase 4: Features Avanzados (Semanas 6-8)](#fase-4-features-avanzados)
6. [Tracking de Avances](#tracking-de-avances)
7. [Criterios de Aceptación](#criterios-de-aceptación)

---

## RESUMEN EJECUTIVO

Este plan implementa las recomendaciones de la auditoría en 4 fases priorizadas por ROI:

| Fase | Semanas | Impacto | Costo |
|------|---------|---------|-------|
| **Fase 1: Refactorización** | 1-2 | +60% mantenibilidad | 0€ |
| **Fase 2: Optimización** | 3-4 | +30-50% performance | 0€ |
| **Fase 3: Infraestructura** | 5 | 100% uptime | $50/mes |
| **Fase 4: Features Avanzados** | 6-8 | Escalabilidad | 0€ |

**Beneficios Totales:**
- Velocidad de desarrollo: +60%
- Onboarding: 5 días → 2 días (-60%)
- Performance: +30-50%
- Escalabilidad: De 50 a 500+ empresas

---

## FASE 1: REFACTORIZACIÓN CORE
**Duración:** 2 semanas (10 días laborables)
**Prioridad:** 🔴 CRÍTICA
**Impacto:** Alto (+60% mantenibilidad)
**Riesgo:** Bajo (94% cobertura de tests)

### TAREA 1.1: Refactorizar `models.py` (3,142 líneas)

#### **Día 1-2: Análisis y Preparación**

**Objetivo:** Entender dependencias y planificar migración

**Actividades:**
```bash
# 1. Backup completo
cd C:\Users\LENOVO\OneDrive\Escritorio\sam-2
python manage.py backup_data
cp core/models.py backups/models.py.before-refactor-$(date +%Y%m%d)

# 2. Análisis de dependencias
grep -r "from core.models import" core/ > auditorias/models_dependencies.txt
grep -r "from .models import" core/ >> auditorias/models_dependencies.txt

# 3. Ejecutar tests actuales (baseline)
pytest --cov=core.models --cov-report=html
# Guardar reporte en auditorias/test-coverage-before-refactor/
```

**Entregable:**
- ✅ Backup creado
- ✅ Lista de dependencias documentada
- ✅ Tests baseline ejecutados (158 tests passing)

---

#### **Día 3-5: División de Modelos**

**Objetivo:** Crear estructura modular `core/models/`

**Paso 1: Crear estructura de carpetas**
```bash
cd core
mkdir models
touch models/__init__.py
```

**Paso 2: Dividir modelos en archivos**

**Crear `core/models/empresa.py`** (~600 líneas)
```python
# core/models/empresa.py
from django.db import models
from django.utils import timezone
from datetime import date, timedelta
import logging

logger = logging.getLogger('core')

class Empresa(models.Model):
    """Modelo de Empresa - Multi-tenancy core"""
    # [MOVER CÓDIGO DE models.py líneas 68-599]
    # Incluir:
    # - Constantes de planes
    # - Campos del modelo
    # - Métodos: get_estado_suscripcion_display, activar_plan_pagado, etc.
    pass
```

**Crear `core/models/usuario.py`** (~400 líneas)
```python
# core/models/usuario.py
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from .empresa import Empresa

class CustomUser(AbstractUser):
    """Usuario personalizado con multi-tenancy"""
    # [MOVER CÓDIGO DE models.py - CustomUser]
    pass
```

**Crear `core/models/equipo.py`** (~500 líneas)
```python
# core/models/equipo.py
from django.db import models
from .empresa import Empresa
from .usuario import CustomUser

class Equipo(models.Model):
    """Modelo de Equipo de Metrología"""
    # [MOVER CÓDIGO DE models.py - Equipo]
    pass

class BajaEquipo(models.Model):
    """Registro de bajas de equipos"""
    # [MOVER CÓDIGO]
    pass
```

**Crear `core/models/actividades.py`** (~800 líneas)
```python
# core/models/actividades.py
from django.db import models
from .equipo import Equipo
from .empresa import Empresa

class Calibracion(models.Model):
    """Calibraciones de equipos"""
    # [MOVER CÓDIGO]
    pass

class Mantenimiento(models.Model):
    """Mantenimientos de equipos"""
    # [MOVER CÓDIGO]
    pass

class Comprobacion(models.Model):
    """Comprobaciones intermedias"""
    # [MOVER CÓDIGO]
    pass
```

**Crear `core/models/reportes.py`** (~400 líneas)
```python
# core/models/reportes.py
from django.db import models
from .usuario import CustomUser
from .empresa import Empresa

class ZipRequest(models.Model):
    """Sistema de cola de generación ZIP"""
    # [MOVER CÓDIGO]
    pass

class NotificacionZip(models.Model):
    """Notificaciones de ZIPs"""
    # [MOVER CÓDIGO]
    pass

class Notification(models.Model):
    """Sistema de notificaciones globales"""
    # [MOVER CÓDIGO]
    pass
```

**Crear `core/models/metricas.py`** (~300 líneas)
```python
# core/models/metricas.py
from django.db import models
from .empresa import Empresa

class MetricasEficienciaMetrologica(models.Model):
    """Métricas financieras y de eficiencia"""
    # [MOVER CÓDIGO]
    pass
```

**Crear `core/models/misc.py`** (~400 líneas)
```python
# core/models/misc.py
from django.db import models
from .empresa import Empresa

class Ubicacion(models.Model):
    """Ubicaciones físicas"""
    pass

class Procedimiento(models.Model):
    """Procedimientos de calibración"""
    pass

class Proveedor(models.Model):
    """Proveedores de servicios"""
    pass

class TerminosYCondiciones(models.Model):
    """T&C del sistema"""
    pass

class AceptacionTerminos(models.Model):
    """Registro de aceptaciones"""
    pass

class MaintenanceTask(models.Model):
    """Tareas de mantenimiento web"""
    pass

class SystemHealthCheck(models.Model):
    """Health checks del sistema"""
    pass

class Documento(models.Model):
    """Documentos genéricos"""
    pass
```

**Paso 3: Actualizar `core/models/__init__.py`**
```python
# core/models/__init__.py
"""
Modelos del sistema SAM Metrología

Organización:
- empresa.py: Empresa (multi-tenancy core)
- usuario.py: CustomUser
- equipo.py: Equipo, BajaEquipo
- actividades.py: Calibracion, Mantenimiento, Comprobacion
- reportes.py: ZipRequest, NotificacionZip, Notification
- metricas.py: MetricasEficienciaMetrologica
- misc.py: Ubicacion, Procedimiento, Proveedor, TerminosYCondiciones, etc.
"""

# Empresa y Usuario (core del multi-tenancy)
from .empresa import Empresa
from .usuario import CustomUser

# Equipos
from .equipo import Equipo, BajaEquipo

# Actividades de Metrología
from .actividades import Calibracion, Mantenimiento, Comprobacion

# Sistema de Reportes y Notificaciones
from .reportes import ZipRequest, NotificacionZip, Notification

# Métricas
from .metricas import MetricasEficienciaMetrologica

# Modelos Auxiliares
from .misc import (
    Ubicacion, Procedimiento, Proveedor, Documento,
    TerminosYCondiciones, AceptacionTerminos,
    MaintenanceTask, SystemHealthCheck
)

# Exponer todos los modelos (importante para migraciones)
__all__ = [
    'Empresa',
    'CustomUser',
    'Equipo',
    'BajaEquipo',
    'Calibracion',
    'Mantenimiento',
    'Comprobacion',
    'ZipRequest',
    'NotificacionZip',
    'Notification',
    'MetricasEficienciaMetrologica',
    'Ubicacion',
    'Procedimiento',
    'Proveedor',
    'Documento',
    'TerminosYCondiciones',
    'AceptacionTerminos',
    'MaintenanceTask',
    'SystemHealthCheck',
]
```

**Paso 4: Eliminar `core/models.py` antiguo**
```bash
# Renombrar (no eliminar aún por seguridad)
mv core/models.py core/models.py.old
```

**Entregables:**
- ✅ 8 archivos de modelos creados
- ✅ `__init__.py` configurado
- ✅ models.py antiguo respaldado

---

#### **Día 6: Testing y Validación**

**Objetivo:** Asegurar que TODO funciona igual

**Actividades:**
```bash
# 1. Ejecutar migraciones (no debe haber cambios)
python manage.py makemigrations
# Esperado: "No changes detected"

# 2. Ejecutar TODOS los tests
pytest -v

# 3. Verificar que 158 tests pasan
# Esperado: 158 passed

# 4. Verificar imports en toda la app
python manage.py check

# 5. Ejecutar servidor y probar manualmente
python manage.py runserver
# Probar: Login, Dashboard, Crear equipo, Generar reporte
```

**Criterios de Aceptación:**
- ✅ `makemigrations` no detecta cambios
- ✅ 158/158 tests pasan
- ✅ `python manage.py check` sin errores
- ✅ Aplicación funciona en desarrollo

**Si hay errores:**
1. Revisar imports circulares
2. Verificar que todos los modelos están en `__init__.py`
3. Revisar signals (post_save, post_delete)

---

### TAREA 1.2: Refactorizar `reports.py` (137 KB)

#### **Día 7-8: División de Reportes**

**Objetivo:** Crear módulo `core/views/reports/`

**Paso 1: Analizar `reports.py` actual**
```bash
# Ver estructura actual
wc -l core/views/reports.py
# Output esperado: ~3000 líneas

# Identificar secciones
grep -n "^def " core/views/reports.py > auditorias/reports_functions.txt
grep -n "^class " core/views/reports.py >> auditorias/reports_functions.txt
```

**Paso 2: Crear estructura**
```bash
cd core/views
mkdir reports
touch reports/__init__.py
```

**Paso 3: Dividir en archivos**

**Crear `core/views/reports/pdf_generator.py`**
```python
# core/views/reports/pdf_generator.py
"""Generación de PDFs para equipos y calibraciones"""

from ..base import *
from weasyprint import HTML
from django.template.loader import render_to_string

def generar_pdf_equipo(request, equipo_id):
    """Genera PDF individual de un equipo"""
    # [MOVER CÓDIGO DE reports.py]
    pass

def generar_pdf_calibracion(request, calibracion_id):
    """Genera PDF de certificado de calibración"""
    # [MOVER CÓDIGO]
    pass

# ... más funciones PDF
```

**Crear `core/views/reports/excel_generator.py`**
```python
# core/views/reports/excel_generator.py
"""Generación de archivos Excel"""

from ..base import *
import openpyxl
from openpyxl.styles import Font, Alignment

def generar_excel_equipos(request):
    """Exporta equipos a Excel"""
    # [MOVER CÓDIGO DE reports.py]
    pass

def generar_excel_consolidado(request, empresa_id):
    """Excel consolidado con todos los equipos"""
    # [MOVER CÓDIGO]
    pass
```

**Crear `core/views/reports/zip_manager.py`**
```python
# core/views/reports/zip_manager.py
"""Sistema de generación de ZIPs con cola"""

from ..base import *
from core.models import ZipRequest
import zipfile

def solicitar_zip_empresa(request):
    """Crea solicitud de ZIP en la cola"""
    # [MOVER CÓDIGO DE reports.py]
    pass

def descargar_zip(request, zip_request_id):
    """Descarga ZIP generado"""
    # [MOVER CÓDIGO]
    pass

def cancelar_zip(request, zip_request_id):
    """Cancela solicitud de ZIP"""
    # [MOVER CÓDIGO]
    pass
```

**Crear `core/views/reports/progress_api.py`**
```python
# core/views/reports/progress_api.py
"""APIs para tracking de progreso de generación"""

from ..base import *
from django.http import JsonResponse

def zip_progress_api(request):
    """API endpoint para progreso de ZIPs"""
    # [MOVER CÓDIGO DE reports.py]
    pass

def notifications_api(request):
    """API endpoint para notificaciones"""
    # [MOVER CÓDIGO]
    pass
```

**Crear `core/views/reports/utils.py`**
```python
# core/views/reports/utils.py
"""Utilidades compartidas para reportes"""

from ..base import *

def validate_file_in_storage(file_path):
    """Valida que archivo existe en S3/local"""
    # [MOVER CÓDIGO]
    pass

def get_logo_empresa(empresa):
    """Obtiene logo de empresa para PDFs"""
    # [MOVER CÓDIGO]
    pass
```

**Paso 4: Actualizar `core/views/reports/__init__.py`**
```python
# core/views/reports/__init__.py
"""
Módulo de generación de reportes SAM Metrología

Organización:
- pdf_generator.py: PDFs de equipos y calibraciones
- excel_generator.py: Exports a Excel
- zip_manager.py: Sistema de cola de ZIPs
- progress_api.py: APIs de progreso
- utils.py: Utilidades compartidas
"""

from .pdf_generator import (
    generar_pdf_equipo,
    generar_pdf_calibracion,
    # ... más funciones
)

from .excel_generator import (
    generar_excel_equipos,
    generar_excel_consolidado,
)

from .zip_manager import (
    solicitar_zip_empresa,
    descargar_zip,
    cancelar_zip,
)

from .progress_api import (
    zip_progress_api,
    notifications_api,
)

__all__ = [
    # PDFs
    'generar_pdf_equipo',
    'generar_pdf_calibracion',
    # Excel
    'generar_excel_equipos',
    'generar_excel_consolidado',
    # ZIPs
    'solicitar_zip_empresa',
    'descargar_zip',
    'cancelar_zip',
    # APIs
    'zip_progress_api',
    'notifications_api',
]
```

**Paso 5: Actualizar URLs**
```python
# core/urls.py
# ANTES:
from core.views.reports import generar_pdf_equipo, ...

# DESPUÉS:
from core.views.reports import (
    generar_pdf_equipo,
    generar_excel_equipos,
    solicitar_zip_empresa,
    zip_progress_api,
)
```

**Entregables Día 7-8:**
- ✅ 5 archivos de reportes creados
- ✅ `__init__.py` configurado
- ✅ URLs actualizadas

---

#### **Día 9: Testing Refactorización Reports**

**Actividades:**
```bash
# 1. Tests completos
pytest tests/test_views/

# 2. Probar generación de PDF manualmente
# - Ir a /core/equipos/1/pdf/
# - Verificar que descarga correctamente

# 3. Probar sistema ZIP
# - Solicitar ZIP de empresa
# - Verificar progreso en tiempo real
# - Descargar ZIP generado

# 4. Probar Excel
# - Exportar equipos a Excel
# - Verificar contenido correcto
```

**Criterios de Aceptación:**
- ✅ Tests de vistas pasan (60+ tests)
- ✅ PDFs se generan correctamente
- ✅ ZIPs funcionan con cola
- ✅ Excel exporta datos

---

### TAREA 1.3: Consolidar `services.py` y `services_new.py`

#### **Día 10: Consolidación de Services**

**Objetivo:** Un solo archivo `services.py` unificado

**Paso 1: Comparar archivos**
```bash
# Analizar diferencias
diff core/services.py core/services_new.py > auditorias/services_diff.txt

# Ver qué se usa más
grep -r "from core.services import" core/ | wc -l
grep -r "from core.services_new import" core/ | wc -l
```

**Paso 2: Mergear contenido**
```python
# core/services.py (versión unificada)
"""
Servicios de lógica de negocio SAM Metrología

Contiene:
- EquipmentService: Lógica de equipos
- FileUploadService: Manejo seguro de archivos
- CacheManager: Gestión de caché
- ValidationService: Validaciones de negocio
"""

import uuid
import re
import os
import logging
from datetime import datetime
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError
from django.db import transaction
from django.core.cache import cache
from .models import Equipo, Empresa

logger = logging.getLogger('core')

# [MERGEAR TODO EL CONTENIDO DE services.py y services_new.py]
# Eliminar duplicados
# Mantener versión más reciente de cada función

class EquipmentService:
    """Servicio para lógica de negocio de equipos"""
    # ...

class FileUploadService:
    """Servicio para upload seguro de archivos"""
    # ...

class CacheManager:
    """Gestión centralizada de caché"""
    # ...

class ValidationService:
    """Validaciones de negocio"""
    # ...
```

**Paso 3: Eliminar `services_new.py`**
```bash
mv core/services_new.py core/services_new.py.old
```

**Paso 4: Actualizar imports**
```bash
# Buscar y reemplazar imports
grep -rl "from core.services_new import" core/ | xargs sed -i 's/from core.services_new import/from core.services import/g'
```

**Paso 5: Testing**
```bash
pytest tests/test_services/
# Verificar que todos los tests de servicios pasan
```

**Entregables Día 10:**
- ✅ `services.py` unificado
- ✅ `services_new.py` eliminado
- ✅ Imports actualizados
- ✅ Tests pasan

---

### CHECKPOINT FASE 1 (Fin Semana 2)

**Verificación Final:**
```bash
# 1. Estructura de archivos
tree core/models/
tree core/views/reports/

# 2. Tests completos
pytest --cov=core --cov-report=html

# 3. Verificación de imports
python -c "from core.models import Empresa, CustomUser, Equipo; print('✅ Models OK')"
python -c "from core.views.reports import generar_pdf_equipo; print('✅ Reports OK')"
python -c "from core.services import EquipmentService; print('✅ Services OK')"

# 4. Check Django
python manage.py check --deploy
```

**Métricas de Éxito:**
- ✅ `core/models.py` eliminado (ahora es módulo con 8 archivos)
- ✅ `core/views/reports.py` eliminado (ahora es módulo con 5 archivos)
- ✅ `services_new.py` eliminado (unificado en `services.py`)
- ✅ 158/158 tests pasan
- ✅ Aplicación funciona en desarrollo

**Documentar Avances:**
```bash
# Crear reporte de progreso
cat > auditorias/PROGRESO_FASE1_$(date +%Y%m%d).md << 'EOF'
# PROGRESO FASE 1: Refactorización Core

## Fecha: $(date)

## Tareas Completadas

### ✅ Refactorización models.py
- Dividido en 8 archivos modulares
- Total líneas antes: 3,142
- Total líneas ahora: 3,142 (distribuidas)
- Tests: 158/158 ✅

### ✅ Refactorización reports.py
- Dividido en 5 archivos especializados
- Total líneas antes: ~3,000
- Tests de vistas: PASSING ✅

### ✅ Consolidación de Services
- services.py y services_new.py → services.py unificado
- Tests de servicios: 85/85 ✅

## Impacto Medido

- Mantenibilidad: +60% (archivos <600 líneas)
- Velocidad IDE: +40% (carga más rápida)
- Code review: +70% más rápido
- Onboarding: Reducido de 5 días a ~2.5 días

## Próximos Pasos

- Iniciar Fase 2: Optimización (Semana 3)
EOF
```

---

## FASE 2: OPTIMIZACIÓN
**Duración:** 2 semanas (Semanas 3-4)
**Prioridad:** 🟡 ALTA
**Impacto:** +30-50% performance
**Riesgo:** Bajo

### TAREA 2.1: Eliminar Código DEBUG (Semana 3, Días 1-2)

#### **Día 1: Identificar y Limpiar**

**Objetivo:** Reemplazar 37 `print()` por `logger.debug()`

**Actividades:**
```bash
# 1. Encontrar todos los prints de DEBUG
grep -rn "print.*DEBUG" core/ > auditorias/debug_prints.txt
grep -rn "print(f" core/views/ >> auditorias/debug_prints.txt

# 2. Análisis
cat auditorias/debug_prints.txt
# Identificar archivos afectados: activities.py, equipment.py
```

**Reemplazos:**

**En `core/views/activities.py`:**
```python
# ANTES:
print(f"DEBUG === POST CALIBRACIÓN - Datos recibidos ===")
print(f"DEBUG POST data: {dict(request.POST)}")

# DESPUÉS:
logger.debug("POST CALIBRACIÓN - Datos recibidos", extra={
    'post_data': dict(request.POST),
    'files': list(request.FILES.keys()),
    'empresa': equipo.empresa.nombre
})
```

**En `core/views/equipment.py`:**
```python
# ANTES:
print(f"DEBUG DEBUG DETALLE_EQUIPO - Equipo ID: {equipo.pk}")
print(f"DEBUG Calibraciones en BD: {calibraciones_count}")

# DESPUÉS:
logger.debug("Vista detalle_equipo", extra={
    'equipo_id': equipo.pk,
    'calibraciones_count': calibraciones_count,
    'mantenimientos_count': mantenimientos_count
})
```

**Script de reemplazo automático:**
```bash
# Backup
cp core/views/activities.py core/views/activities.py.before-cleanup
cp core/views/equipment.py core/views/equipment.py.before-cleanup

# Eliminar prints de DEBUG (revisar manualmente después)
# (Mejor hacerlo archivo por archivo manualmente para evitar errores)
```

**Entregable Día 1:**
- ✅ Lista completa de prints DEBUG
- ✅ 37 prints reemplazados por logger.debug()
- ✅ Código limpiado

---

#### **Día 2: Limpiar Comentarios TODO/FIXME**

**Actividades:**
```bash
# Encontrar TODOs
grep -rn "# TODO" core/ > auditorias/todos.txt
grep -rn "# FIXME" core/ >> auditorias/todos.txt
grep -rn "# HACK" core/ >> auditorias/todos.txt

# Revisar cada uno:
# - Si está resuelto: Eliminar comentario
# - Si es pendiente: Crear issue en GitHub o mover a backlog
```

**Crear issues para TODOs pendientes:**
```markdown
# auditorias/BACKLOG_TODOS.md

## TODOs Pendientes

1. **core/models/equipo.py:234** - Optimizar cálculo de próximas fechas
   - Prioridad: Media
   - Esfuerzo: 2 horas

2. **core/views/panel_decisiones.py:528** - Mejorar metodología de ROI
   - Prioridad: Baja
   - Esfuerzo: 4 horas
```

**Entregable Día 2:**
- ✅ Comentarios TODO/FIXME revisados
- ✅ Issues creados para pendientes
- ✅ Comentarios obsoletos eliminados

---

### TAREA 2.2: Optimizar Queries N+1 (Semana 3, Días 3-5)

#### **Día 3: Instalación y Auditoría**

**Instalar django-debug-toolbar:**
```bash
pip install django-debug-toolbar
```

**Configurar en settings.py:**
```python
# proyecto_c/settings.py (solo DEBUG=True)

if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1']
```

**Configurar URLs:**
```python
# proyecto_c/urls.py

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
```

**Auditar queries:**
```bash
# Iniciar servidor
python manage.py runserver

# Visitar:
# - /core/equipos/ (listado de equipos)
# - /core/dashboard/ (dashboard principal)
# - /core/panel-decisiones/ (panel financiero)

# Revisar Debug Toolbar → SQL queries
# Identificar queries duplicadas (problema N+1)
```

**Documentar problemas encontrados:**
```markdown
# auditorias/N+1_QUERIES_DETECTED.md

## Queries N+1 Detectadas

### 1. Vista: /core/equipos/
**Problema:** 1 + N queries para obtener empresa de cada equipo
**Queries:** 1 (equipos) + 50 (empresa por equipo) = 51 queries
**Solución:** select_related('empresa')

### 2. Vista: /core/dashboard/
**Problema:** 1 + N queries para calibraciones de equipos
**Queries:** 1 (equipos) + 20 (calibraciones) = 21 queries
**Solución:** prefetch_related('calibraciones_set')

### 3. Vista: /core/panel-decisiones/
**Problema:** Múltiples queries para métricas
**Queries:** 150+ queries
**Solución:** Aggregate + Annotate + Cache
```

**Entregable Día 3:**
- ✅ Debug Toolbar instalado
- ✅ Problemas N+1 documentados
- ✅ Lista de vistas a optimizar

---

#### **Día 4-5: Aplicar Optimizaciones**

**Optimizar vista de equipos:**
```python
# core/views/equipment.py

# ANTES:
def listar_equipos(request):
    equipos = Equipo.objects.filter(empresa=request.user.empresa)
    # Problema: 1 query equipos + N queries empresa + N queries ubicacion

# DESPUÉS:
def listar_equipos(request):
    equipos = Equipo.objects.filter(
        empresa=request.user.empresa
    ).select_related(
        'empresa',
        'ubicacion'
    ).prefetch_related(
        'calibraciones_set',
        'mantenimientos_set'
    ).only(
        'id', 'codigo_interno', 'nombre', 'marca', 'modelo',
        'estado', 'empresa__nombre', 'ubicacion__nombre'
    )
    # Resultado: 3-4 queries en total (90% reducción)
```

**Optimizar dashboard:**
```python
# core/views/dashboard.py

# ANTES:
equipos = Equipo.objects.filter(empresa=empresa)
for equipo in equipos:
    ultima_calibracion = equipo.calibraciones_set.latest('fecha_calibracion')
    # N queries

# DESPUÉS:
from django.db.models import Prefetch, Max

equipos = Equipo.objects.filter(empresa=empresa).select_related(
    'empresa',
    'ubicacion'
).prefetch_related(
    Prefetch(
        'calibraciones_set',
        queryset=Calibracion.objects.order_by('-fecha_calibracion')[:1],
        to_attr='ultima_calibracion_cache'
    )
).annotate(
    fecha_ultima_calibracion=Max('calibraciones_set__fecha_calibracion')
)

# Acceso:
for equipo in equipos:
    if equipo.ultima_calibracion_cache:
        ultima = equipo.ultima_calibracion_cache[0]
```

**Optimizar panel de decisiones:**
```python
# core/views/panel_decisiones.py

# ANTES:
total_calibraciones = 0
for equipo in equipos:
    total_calibraciones += equipo.calibraciones_set.count()
    # N queries

# DESPUÉS:
from django.db.models import Count, Sum, Avg

stats = Equipo.objects.filter(empresa=empresa).aggregate(
    total_equipos=Count('id'),
    total_calibraciones=Count('calibraciones_set'),
    costo_total_calibraciones=Sum('calibraciones_set__costo_calibracion'),
    costo_promedio=Avg('calibraciones_set__costo_calibracion')
)
# 1 query en lugar de N
```

**Testing de optimizaciones:**
```bash
# 1. Medir ANTES
# Queries en /core/equipos/: 51 queries

# 2. Aplicar optimizaciones

# 3. Medir DESPUÉS
# Queries en /core/equipos/: 4 queries (92% reducción)

# 4. Verificar performance
# Tiempo de carga ANTES: 1.2s
# Tiempo de carga DESPUÉS: 0.35s (71% mejora)
```

**Entregable Días 4-5:**
- ✅ 10+ vistas optimizadas
- ✅ Reducción de queries: 90%+
- ✅ Performance mejorado: 30-50%

---

### TAREA 2.3: Mejorar Tests de Vistas (Semana 4, Días 1-3)

#### **Objetivo:** Pasar de 60% a 80%+ cobertura en vistas

**Día 1: Identificar gaps de cobertura**
```bash
# Coverage actual
pytest --cov=core.views --cov-report=html

# Abrir htmlcov/index.html
# Identificar líneas no cubiertas (rojas)
```

**Día 2-3: Escribir tests faltantes**

**Ejemplo: Tests para `equipment.py`**
```python
# tests/test_views/test_equipment_views.py

import pytest
from django.urls import reverse
from core.models import Equipo

@pytest.mark.django_db
class TestEquipmentViews:

    def test_listar_equipos_con_filtros(self, authenticated_client, empresa_factory, equipo_factory):
        """Test listado de equipos con filtros de estado"""
        empresa = empresa_factory()
        equipo_activo = equipo_factory(empresa=empresa, estado='ACTIVO')
        equipo_inactivo = equipo_factory(empresa=empresa, estado='INACTIVO')

        # Filtrar solo activos
        response = authenticated_client.get(reverse('core:listar_equipos') + '?estado=ACTIVO')

        assert response.status_code == 200
        assert equipo_activo.nombre in response.content.decode()
        assert equipo_inactivo.nombre not in response.content.decode()

    def test_crear_equipo_limite_alcanzado(self, authenticated_client, empresa_factory):
        """Test que verifica límite de equipos por empresa"""
        empresa = empresa_factory(limite_equipos_empresa=5)

        # Crear 5 equipos (límite)
        for i in range(5):
            equipo_factory(empresa=empresa)

        # Intentar crear el 6to equipo (debe fallar)
        response = authenticated_client.post(reverse('core:añadir_equipo'), {
            'codigo_interno': 'TEST-006',
            'nombre': 'Equipo 6',
            # ... más datos
        })

        assert response.status_code == 400
        assert 'límite' in response.content.decode().lower()

    def test_editar_equipo_multitenancy(self, authenticated_client, equipo_factory, user_factory):
        """Test que verifica aislamiento multi-tenant"""
        empresa_A = empresa_factory()
        empresa_B = empresa_factory()

        equipo_A = equipo_factory(empresa=empresa_A)
        user_B = user_factory(empresa=empresa_B)

        client_B = Client()
        client_B.force_login(user_B)

        # Usuario de empresa B intenta editar equipo de empresa A
        response = client_B.post(reverse('core:editar_equipo', args=[equipo_A.id]), {
            'nombre': 'HACKED',
        })

        # Debe ser 403 o 404 (no tiene acceso)
        assert response.status_code in [403, 404]

    # ... más tests
```

**Tests para `reports.py`**
```python
# tests/test_views/test_reports_views.py

@pytest.mark.django_db
class TestReportsViews:

    def test_generar_pdf_equipo(self, authenticated_client, equipo_factory):
        """Test generación de PDF de equipo"""
        equipo = equipo_factory()

        response = authenticated_client.get(
            reverse('core:generar_pdf_equipo', args=[equipo.id])
        )

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        assert response['Content-Disposition'].startswith('attachment')

    def test_solicitar_zip_limite_equipos(self, authenticated_client, empresa_factory, equipo_factory):
        """Test que ZIP grande se divide en partes"""
        empresa = empresa_factory()

        # Crear 40 equipos (> 35 límite)
        for i in range(40):
            equipo_factory(empresa=empresa)

        response = authenticated_client.post(reverse('core:solicitar_zip_empresa'))

        assert response.status_code == 200

        # Verificar que se crearon 2 solicitudes (40/35 = 2 partes)
        zip_requests = ZipRequest.objects.filter(empresa=empresa)
        assert zip_requests.count() == 2

    # ... más tests
```

**Ejecutar y medir:**
```bash
# Coverage nuevo
pytest --cov=core.views --cov-report=html

# Verificar mejora
# ANTES: 60% cobertura en vistas
# DESPUÉS: 80%+ cobertura
```

**Entregable Días 1-3:**
- ✅ 30+ tests nuevos de vistas
- ✅ Cobertura vistas: 80%+
- ✅ Casos edge cubiertos

---

### CHECKPOINT FASE 2 (Fin Semana 4)

**Verificación:**
```bash
# 1. Tests completos
pytest --cov=core --cov-report=term-missing

# 2. Performance
# Medir queries en vistas principales
# ANTES: 50-150 queries por vista
# DESPUÉS: 3-10 queries por vista

# 3. Código limpio
grep -r "print(f" core/views/
# Output esperado: 0 matches (o solo en comentarios)
```

**Métricas de Éxito:**
- ✅ 37 `print()` DEBUG eliminados
- ✅ Queries optimizadas: -90%
- ✅ Performance: +30-50%
- ✅ Cobertura tests vistas: 80%+

**Documentar:**
```bash
cat > auditorias/PROGRESO_FASE2_$(date +%Y%m%d).md << 'EOF'
# PROGRESO FASE 2: Optimización

## Fecha: $(date)

## Tareas Completadas

### ✅ Limpieza de Código
- 37 prints DEBUG eliminados
- Comentarios TODO/FIXME revisados
- Logging estructurado implementado

### ✅ Optimización de Queries
- Queries reducidas: 90%
- Vistas optimizadas: 10+
- Performance: +30-50%

### ✅ Tests Mejorados
- Cobertura vistas: 60% → 80%
- Tests nuevos: 30+
- Casos edge cubiertos

## Impacto Medido

- Tiempo de carga equipos: 1.2s → 0.35s (-71%)
- Queries dashboard: 150 → 8 (-95%)
- Tests totales: 158 → 188

## Próximos Pasos

- Iniciar Fase 3: Infraestructura (Semana 5)
EOF
```

---

## FASE 3: INFRAESTRUCTURA
**Duración:** 1 semana (Semana 5)
**Prioridad:** 🟡 ALTA
**Impacto:** 100% uptime, 4x RAM
**Costo:** $50/mes

### TAREA 3.1: Migrar a Plan Pagado Render (Día 1)

#### **Paso 1: Configurar Plan Pagado**

**Acciones en Render Dashboard:**
1. Ir a https://dashboard.render.com
2. Seleccionar servicio `sam-metrologia`
3. Settings → Plan → Upgrade to **Starter** ($25/mes)
   - 2 GB RAM (vs 512 MB)
   - Sin sleep
   - 100% uptime
4. PostgreSQL Database → Upgrade to **Standard** ($20/mes)
   - 4 GB storage (vs 1 GB)
   - Backups automáticos diarios
   - 100% SLA

**Total:** $45/mes + impuestos

**Paso 2: Verificar Variables de Entorno**

Asegurar que están configuradas:
```
SECRET_KEY=<valor-seguro>
DATABASE_URL=<auto-configurado>
AWS_ACCESS_KEY_ID=<aws-key>
AWS_SECRET_ACCESS_KEY=<aws-secret>
AWS_STORAGE_BUCKET_NAME=sam-metrologia-files
AWS_S3_REGION_NAME=us-east-2
REDIS_URL=<opcional-pero-recomendado>
```

**Paso 3: Deploy**

Render hace auto-deploy automáticamente después del upgrade.

**Verificar:**
```bash
# 1. Acceder a la app
curl https://app.sammetrologia.com
# Debe responder (no dormir)

# 2. Verificar logs
# Render Dashboard → Logs
# Verificar que inicia sin errores

# 3. Test manual
# Login → Dashboard → Crear equipo → Generar PDF
```

**Entregable:**
- ✅ Plan Starter activado
- ✅ PostgreSQL Standard activado
- ✅ App funciona sin sleep
- ✅ 100% uptime verificado

---

### TAREA 3.2: Configurar Sentry para Logs (Día 2)

#### **Paso 1: Crear cuenta Sentry**

```bash
# 1. Ir a https://sentry.io
# 2. Crear cuenta (Developer plan: $26/mes para 50k eventos)
# 3. Crear proyecto: Django
# 4. Obtener DSN
```

**Paso 2: Instalar Sentry SDK**
```bash
pip install sentry-sdk[django]
pip freeze > requirements.txt
```

**Paso 3: Configurar en settings.py**
```python
# proyecto_c/settings.py

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

if not DEBUG:
    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,  # 10% de transacciones para performance
        send_default_pii=False,  # No enviar PII
        environment='production',
        release=os.environ.get('RENDER_GIT_COMMIT', 'unknown'),
    )
```

**Paso 4: Configurar variable en Render**
```
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
```

**Paso 5: Probar**
```python
# Agregar endpoint de prueba (temporal)
# core/views/admin.py

def test_sentry(request):
    """Endpoint temporal para probar Sentry"""
    if request.user.is_superuser:
        division_by_zero = 1 / 0
    return HttpResponse("Test")
```

**Verificar en Sentry Dashboard:**
- Ver error capturado
- Stack trace completo
- Variables de contexto

**Entregable:**
- ✅ Sentry configurado
- ✅ Errores capturados
- ✅ Alertas configuradas

---

### TAREA 3.3: Documentar APIs con Swagger (Días 3-4)

#### **Paso 1: Instalar drf-spectacular**
```bash
pip install djangorestframework drf-spectacular
pip freeze > requirements.txt
```

**Paso 2: Configurar en settings.py**
```python
# proyecto_c/settings.py

INSTALLED_APPS += [
    'rest_framework',
    'drf_spectacular',
]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'SAM Metrología API',
    'DESCRIPTION': 'API para gestión de equipos de metrología',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}
```

**Paso 3: Agregar URLs**
```python
# proyecto_c/urls.py

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns += [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
```

**Paso 4: Documentar endpoints existentes**

**Crear serializers para APIs existentes:**
```python
# core/api_serializers.py (nuevo archivo)

from rest_framework import serializers
from core.models import Equipo, Calibracion

class EquipoSerializer(serializers.ModelSerializer):
    """Serializer para modelo Equipo"""
    class Meta:
        model = Equipo
        fields = [
            'id', 'codigo_interno', 'nombre', 'marca', 'modelo',
            'estado', 'empresa', 'ubicacion'
        ]

class CalibracionSerializer(serializers.ModelSerializer):
    """Serializer para modelo Calibracion"""
    class Meta:
        model = Calibracion
        fields = '__all__'
```

**Convertir vistas API a DRF:**
```python
# core/views/reports/progress_api.py

from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

@extend_schema(
    description="API para consultar progreso de generación de ZIPs",
    responses={200: {
        'type': 'object',
        'properties': {
            'success': {'type': 'boolean'},
            'requests': {'type': 'array'},
            'total_active': {'type': 'integer'},
        }
    }}
)
@api_view(['GET'])
def zip_progress_api(request):
    """API endpoint para progreso de ZIPs"""
    # ... código existente
    return Response({
        'success': True,
        'requests': progress_data,
        'total_active': len(progress_data)
    })
```

**Paso 5: Generar documentación**
```bash
python manage.py spectacular --file schema.yml

# Verificar en navegador
# http://localhost:8000/api/docs/
# Debe mostrar Swagger UI con todos los endpoints
```

**Entregable:**
- ✅ Swagger UI accesible
- ✅ 10+ endpoints documentados
- ✅ Serializers creados

---

### CHECKPOINT FASE 3 (Fin Semana 5)

**Verificación:**
```bash
# 1. Plan Render
# Verificar que no hay sleep después de 15 min

# 2. Sentry
# Verificar que captura errores en https://sentry.io

# 3. Swagger
# Acceder a /api/docs/
# Verificar que muestra documentación
```

**Métricas:**
- ✅ Uptime: 100% (sin sleep)
- ✅ RAM: 2 GB (4x más)
- ✅ DB: 4 GB (4x más)
- ✅ Errores centralizados: Sentry
- ✅ APIs documentadas: Swagger

**Costo mensual:** $50

**Documentar:**
```bash
cat > auditorias/PROGRESO_FASE3_$(date +%Y%m%d).md << 'EOF'
# PROGRESO FASE 3: Infraestructura

## Tareas Completadas

### ✅ Migración Render
- Plan: Free → Starter ($25/mes)
- PostgreSQL: Free → Standard ($20/mes)
- RAM: 512MB → 2GB (4x)
- Uptime: ~70% → 100%

### ✅ Sentry Configurado
- Errores centralizados
- Alertas automáticas
- Stack traces completos

### ✅ Swagger Implementado
- 10+ endpoints documentados
- UI accesible en /api/docs/

## Impacto

- Uptime: +30%
- Capacidad: 100 → 400 empresas
- Debugging: -80% tiempo
- Documentación API: Completa

## Próximos Pasos

- Iniciar Fase 4: Features Avanzados (Semanas 6-8)
EOF
```

---

## FASE 4: FEATURES AVANZADOS
**Duración:** 3 semanas (Semanas 6-8)
**Prioridad:** 🟢 MEDIA
**Impacto:** Escalabilidad, Seguridad Enterprise
**Riesgo:** Medio

### TAREA 4.1: Implementar 2FA (Semana 6)

#### **Día 1-2: Instalación y Configuración**

**Instalar django-otp:**
```bash
pip install django-otp qrcode
pip freeze > requirements.txt
```

**Configurar settings.py:**
```python
# proyecto_c/settings.py

INSTALLED_APPS += [
    'django_otp',
    'django_otp.plugins.otp_totp',
]

MIDDLEWARE += [
    'django_otp.middleware.OTPMiddleware',
]
```

**Migrar DB:**
```bash
python manage.py migrate
```

#### **Día 3-4: Implementar Vistas**

**Crear vista de configuración 2FA:**
```python
# core/views/auth_2fa.py (nuevo)

from django.shortcuts import render, redirect
from django_otp.plugins.otp_totp.models import TOTPDevice
from django.contrib.auth.decorators import login_required
import qrcode
import io
import base64

@login_required
def setup_2fa(request):
    """Configurar 2FA para el usuario"""
    user = request.user

    # Verificar si ya tiene 2FA
    device = TOTPDevice.objects.filter(user=user, confirmed=True).first()

    if request.method == 'POST':
        # Verificar token
        token = request.POST.get('token')
        device = TOTPDevice.objects.filter(user=user, confirmed=False).first()

        if device and device.verify_token(token):
            device.confirmed = True
            device.save()
            messages.success(request, 'Autenticación de dos factores activada')
            return redirect('core:perfil_usuario')
        else:
            messages.error(request, 'Token inválido')

    # Crear dispositivo temporal
    if not device:
        device = TOTPDevice.objects.create(
            user=user,
            name='TOTP Device',
            confirmed=False
        )

    # Generar QR code
    url = device.config_url
    qr = qrcode.make(url)
    buffer = io.BytesIO()
    qr.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render(request, 'core/setup_2fa.html', {
        'qr_code': qr_base64,
        'secret': device.key,
    })
```

**Template:**
```html
<!-- core/templates/core/setup_2fa.html -->
{% extends 'base.html' %}

{% block content %}
<div class="max-w-2xl mx-auto">
    <h1 class="text-2xl font-bold mb-4">Configurar Autenticación de Dos Factores</h1>

    <div class="bg-white p-6 rounded shadow">
        <p class="mb-4">Escanea este código QR con Google Authenticator o similar:</p>

        <img src="data:image/png;base64,{{ qr_code }}" alt="QR Code" class="mx-auto mb-4">

        <p class="text-sm text-gray-600 mb-4">
            O ingresa manualmente: <code class="bg-gray-100 p-1">{{ secret }}</code>
        </p>

        <form method="post">
            {% csrf_token %}
            <label class="block mb-2">Ingresa el código de 6 dígitos:</label>
            <input type="text" name="token" class="form-input w-full" maxlength="6" required>
            <button type="submit" class="btn btn-primary mt-4">Activar 2FA</button>
        </form>
    </div>
</div>
{% endblock %}
```

#### **Día 5: Testing**

```python
# tests/test_auth/test_2fa.py

@pytest.mark.django_db
class Test2FA:

    def test_setup_2fa_genera_qr(self, authenticated_client):
        """Test que genera QR code para setup"""
        response = authenticated_client.get(reverse('core:setup_2fa'))

        assert response.status_code == 200
        assert 'qr_code' in response.context
        assert 'secret' in response.context

    def test_verificar_token_correcto(self, authenticated_client, user_factory):
        """Test verificación de token TOTP"""
        user = user_factory()
        device = TOTPDevice.objects.create(user=user, name='Test', confirmed=False)

        # Generar token válido
        token = device.generate_token()

        response = authenticated_client.post(reverse('core:setup_2fa'), {
            'token': token
        })

        device.refresh_from_db()
        assert device.confirmed == True
```

**Entregable Semana 6:**
- ✅ 2FA implementado
- ✅ QR code generation
- ✅ Tests 2FA
- ✅ Opcional por usuario

---

### TAREA 4.2: Implementar Celery (Semana 7)

#### **Día 1: Instalación**

```bash
pip install celery redis
pip freeze > requirements.txt
```

#### **Día 2-3: Configuración**

**Crear `proyecto_c/celery.py`:**
```python
# proyecto_c/celery.py

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')

app = Celery('sam_metrologia')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

**Actualizar `proyecto_c/__init__.py`:**
```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

**Configurar settings.py:**
```python
# proyecto_c/settings.py

CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Bogota'
```

#### **Día 4: Mover Tareas Pesadas a Celery**

**Ejemplo: Generación de PDFs**
```python
# core/tasks.py (nuevo)

from celery import shared_task
from core.models import Equipo
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def generar_pdf_equipo_async(self, equipo_id):
    """Genera PDF de equipo de forma asíncrona"""
    try:
        equipo = Equipo.objects.get(id=equipo_id)

        # ... lógica de generación PDF
        # Guardar en S3

        return {
            'success': True,
            'file_url': pdf_url,
            'equipo_id': equipo_id
        }

    except Exception as exc:
        logger.error(f"Error generando PDF equipo {equipo_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)
```

**Actualizar vista:**
```python
# core/views/reports/pdf_generator.py

from core.tasks import generar_pdf_equipo_async

def solicitar_pdf_equipo(request, equipo_id):
    """Solicita generación de PDF (asíncrono)"""

    # Encolar tarea
    task = generar_pdf_equipo_async.delay(equipo_id)

    # Guardar task_id para tracking
    request.session['pdf_task_id'] = task.id

    messages.success(request, 'PDF en proceso. Te notificaremos cuando esté listo.')
    return redirect('core:dashboard')
```

#### **Día 5: Deploy Celery en Render**

**Agregar worker a render.yaml:**
```yaml
# render.yaml

services:
  # ... web service existente

  - type: worker
    name: sam-celery-worker
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A proyecto_c worker --loglevel=info
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: sam-metrologia-db
          property: connectionString
      - key: REDIS_URL
        value: redis://red-xxx:6379/0  # Crear Redis en Render primero
```

**Crear Redis en Render:**
1. Render Dashboard → New → Redis
2. Plan: Free (25 MB) para empezar
3. Copiar REDIS_URL interna
4. Agregar a variables de entorno

**Entregable Semana 7:**
- ✅ Celery configurado
- ✅ Worker en Render
- ✅ PDFs generados async
- ✅ ZIPs en background

---

### TAREA 4.3: CI/CD con GitHub Actions (Semana 8)

#### **Crear `.github/workflows/ci.yml`:**
```yaml
# .github/workflows/ci.yml

name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements_test.txt

    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
        SECRET_KEY: test-secret-key
      run: |
        pytest --cov=core --cov-report=xml

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  security:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Run Bandit (security scan)
      run: |
        pip install bandit
        bandit -r core/ -f json -o bandit-report.json || true

    - name: Run Safety (dependency check)
      run: |
        pip install safety
        safety check --json > safety-report.json || true

  deploy:
    needs: [test, security]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - name: Trigger Render Deploy
      run: |
        curl -X POST https://api.render.com/deploy/xxx
```

**Entregable Semana 8:**
- ✅ CI/CD configurado
- ✅ Tests automáticos en PRs
- ✅ Security scan
- ✅ Auto-deploy a Render

---

## TRACKING DE AVANCES

### Ubicación de Reportes

Todos los reportes de progreso se guardan en:
```
auditorias/
├── AUDITORIA_COMPLETA_2025-11-13.md  (este documento)
├── PLAN_IMPLEMENTACION_2025-11-13.md (plan detallado)
├── PROGRESO_FASE1_YYYYMMDD.md
├── PROGRESO_FASE2_YYYYMMDD.md
├── PROGRESO_FASE3_YYYYMMDD.md
├── PROGRESO_FASE4_YYYYMMDD.md
├── models_dependencies.txt
├── debug_prints.txt
├── N+1_QUERIES_DETECTED.md
└── BACKLOG_TODOS.md
```

### Template de Reporte Semanal

```markdown
# REPORTE SEMANAL - Semana X

## Fecha: DD/MM/YYYY

## Resumen

- Fase actual: X
- Tareas completadas: X/Y
- % Progreso total: X%

## Tareas Completadas Esta Semana

### ✅ Tarea 1
- Descripción
- Resultado
- Tests: X/Y passing

### ✅ Tarea 2
- ...

## Bloqueadores

- Ninguno / Descripción

## Métricas

- Tests: X passing
- Coverage: X%
- Performance: +X%

## Próxima Semana

- Tarea 1
- Tarea 2
```

---

## CRITERIOS DE ACEPTACIÓN

### Fase 1: Refactorización
- ✅ `core/models/` con 8 archivos (<600 líneas c/u)
- ✅ `core/views/reports/` con 5 archivos
- ✅ `services_new.py` eliminado
- ✅ 158/158 tests pasan
- ✅ App funciona en desarrollo

### Fase 2: Optimización
- ✅ 0 `print()` DEBUG en código
- ✅ Queries reducidas 90%+
- ✅ Performance +30-50%
- ✅ Cobertura vistas 80%+

### Fase 3: Infraestructura
- ✅ Plan Render Starter activo
- ✅ Sentry captura errores
- ✅ Swagger docs accesibles
- ✅ 100% uptime

### Fase 4: Features
- ✅ 2FA opcional implementado
- ✅ Celery worker funcionando
- ✅ CI/CD en GitHub Actions
- ✅ Tests automáticos en PRs

---

## RECURSOS NECESARIOS

### Humanos
- 1 Desarrollador Full-Stack Senior
- Tiempo completo durante 8-10 semanas
- Soporte ocasional de DevOps (Fases 3-4)

### Infraestructura
- Render Starter: $25/mes
- PostgreSQL Standard: $20/mes
- Sentry Developer: $26/mes
- Redis (Render): $10/mes (opcional)
- **Total:** $50-81/mes

### Herramientas
- GitHub Actions: Gratis (2,000 min/mes)
- django-debug-toolbar: Gratis
- drf-spectacular: Gratis

---

## RIESGOS Y MITIGACIONES

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Tests fallan después refactor | Media | Alto | Backup completo + tests continuos |
| Performance empeora | Baja | Medio | Benchmark ANTES/DESPUÉS |
| Costos Render mayores | Baja | Bajo | Monitorear uso mensual |
| Celery falla en producción | Media | Medio | Fallback a sync + alertas |
| CI/CD rompe deploys | Baja | Alto | Branch protection + manual approval |

---

## CONCLUSIÓN

Este plan transforma SAM Metrología de **7.2/10 a 8.5-9/10** en calidad:

**Beneficios Finales:**
- ✅ Mantenibilidad: +60%
- ✅ Performance: +30-50%
- ✅ Escalabilidad: 50 → 500+ empresas
- ✅ Uptime: 70% → 100%
- ✅ Onboarding: 5 días → 2 días
- ✅ Velocidad desarrollo: +60%

**Inversión:**
- Tiempo: 8-10 semanas
- Dinero: $50-81/mes (infraestructura)
- ROI: **Altísimo** (plataforma enterprise-ready)

**Próximos Pasos:**
1. Aprobar plan con stakeholders
2. Asignar desarrollador
3. Iniciar Fase 1 (Semana 1)
4. Reportes semanales en `auditorias/`

---

**FIN DEL PLAN DE IMPLEMENTACIÓN**

**Contacto:** Ver DEVELOPER-GUIDE.md para soporte
**Fecha:** 13 de Noviembre de 2025
**Versión:** 1.0
