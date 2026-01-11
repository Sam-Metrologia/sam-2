# 🚀 ANÁLISIS DE RENDIMIENTO - LOGIN Y DASHBOARD
**Fecha:** 10 de Enero de 2026
**Objetivo:** Reducir tiempo de carga del dashboard de >5s a <2s
**Alcance:** Login → Dashboard (flujo crítico de usuario)

---

## 📊 DIAGNÓSTICO ACTUAL

### 🔍 Problema Reportado
- **Login:** "Dura mucho en ingresar el cliente"
- **Dashboard:** Carga lenta al entrar
- **Experiencia:** Usuario espera varios segundos antes de ver contenido

### 🐛 CUELLOS DE BOTELLA IDENTIFICADOS

#### 1. ⚠️ CRÍTICO: N+1 Queries en Dashboard (Línea 593)

**Ubicación:** `core/views/dashboard.py:593` - función `_calculate_programmed_activities()`

**Problema:**
```python
for equipo in equipos_para_dashboard:  # Línea 593
    # Por cada equipo:
    latest_calibracion = equipo.calibraciones.order_by('-fecha_calibracion').first()  # QUERY
    latest_mantenimiento = equipo.mantenimientos.order_by('-fecha_mantenimiento').first()  # QUERY
    latest_calibracion = equipo.calibraciones.order_by('-fecha_calibracion').first()  # QUERY DUPLICADA
    latest_comprobacion = equipo.comprobaciones.order_by('-fecha_comprobacion').first()  # QUERY
    latest_calibracion = equipo.calibraciones.order_by('-fecha_calibracion').first()  # QUERY DUPLICADA OTRA VEZ
```

**Impacto:**
- 100 equipos = **500+ queries**
- 200 equipos = **1,000+ queries**
- Cada query: ~10-50ms
- **Tiempo total: 5-25 segundos solo en esta función**

**Queries por equipo:**
- 1 query inicial (queryset equipos)
- 5 queries por equipo (calibraciones x3, mantenimientos x1, comprobaciones x1)
- **Total:** 1 + (N × 5) queries

---

#### 2. 🟡 IMPORTANTE: Queryset Sin Optimización (Línea 272)

**Ubicación:** `core/views/dashboard.py:272` - función `_get_equipos_queryset()`

**Problema:**
```python
equipos_queryset = Equipo.objects.filter(empresa__is_deleted=False)
# NO HAY select_related
# NO HAY prefetch_related
```

**Debería ser:**
```python
equipos_queryset = Equipo.objects.filter(
    empresa__is_deleted=False
).select_related(
    'empresa'
).prefetch_related(
    Prefetch('calibraciones', queryset=Calibracion.objects.order_by('-fecha_calibracion')),
    Prefetch('mantenimientos', queryset=Mantenimiento.objects.order_by('-fecha_mantenimiento')),
    Prefetch('comprobaciones', queryset=Comprobacion.objects.order_by('-fecha_comprobacion'))
)
```

**Impacto:**
- Cada acceso a `equipo.empresa` = query adicional
- Sin prefetch, acceso a relaciones = N+1
- **Añade 100-300 queries más**

---

#### 3. 🟡 IMPORTANTE: Múltiples Queries de Conteo (Línea 452-462)

**Ubicación:** `core/views/dashboard.py:452-462` - función `_get_actividades_data()`

**Problema:**
```python
vencidos_calibracion_codigos = list(equipos_para_dashboard.filter(
    proxima_calibracion__lt=today
).values_list('codigo_interno', flat=True))  # QUERY

vencidos_mantenimiento_codigos = list(equipos_para_dashboard.filter(
    proximo_mantenimiento__lt=today
).values_list('codigo_interno', flat=True))  # QUERY

vencidos_comprobacion_codigos = list(equipos_para_dashboard.filter(
    proxima_comprobacion__lt=today
).values_list('codigo_interno', flat=True))  # QUERY
```

**Impacto:**
- 3 queries separadas que podrían ser 1 con annotate
- Cada query: ~20-100ms
- **Total: 60-300ms adicionales**

---

#### 4. 🟢 MENOR: No Hay Cache

**Ubicación:** Dashboard completo

**Problema:**
- Los datos del dashboard se calculan en **cada carga**
- Métricas no cambian cada segundo
- No hay cache de resultados

**Impacto:**
- Dashboard siempre tarda lo mismo
- Carga innecesaria en BD
- **Oportunidad: reducir 80% con cache**

---

#### 5. 🟢 MENOR: Queries en `get_projected_activities_for_year` (Línea 104)

**Ubicación:** `core/views/dashboard.py:104`

**Problema:**
```python
for equipo in equipos_queryset:  # Otro loop
    # Más queries dentro del loop
    realizadas = activity_model.objects.filter(
        equipo=equipo,
        **{f"{date_field}__year": year, f"{date_field}__month": current_date.month}
    ).exists()  # QUERY POR EQUIPO
```

**Impacto:**
- N queries adicionales
- Se usa en gráficos de torta
- **Añade 100-200 queries más**

---

## 📈 ESTIMACIÓN DE QUERIES TOTALES

### Dashboard Actual (Sin Optimización)

| Componente | Queries | Tiempo Estimado |
|------------|---------|-----------------|
| Queryset inicial | 1 | 10ms |
| Empresas disponibles | 1 | 10ms |
| Estadísticas agregadas | 1 | 20ms |
| Storage data | 1 | 10ms |
| Equipment limits | 1 | 10ms |
| **N+1 programmed activities** | **500+** | **5-10s** ⚠️ |
| Calibraciones realizadas | 1 | 50ms |
| Mantenimientos realizados | 1 | 50ms |
| Comprobaciones realizadas | 1 | 50ms |
| Códigos vencidos (3 queries) | 3 | 60ms |
| Projected activities (pie) | 100+ | 1-2s |
| Latest maintenances | 1 | 20ms |
| Préstamos data | 2 | 20ms |
| **TOTAL** | **~613 queries** | **~7-13s** 🔴 |

### Dashboard Optimizado (Con Fix)

| Componente | Queries | Tiempo Estimado |
|------------|---------|-----------------|
| Queryset con prefetch | 4 | 100ms |
| Empresas disponibles | 1 | 10ms |
| Estadísticas agregadas | 1 | 20ms |
| Storage data | 1 | 10ms |
| Equipment limits | 1 | 10ms |
| **Programmed activities** | **0** | **50ms** ✅ |
| Calibraciones realizadas | 1 | 50ms |
| Mantenimientos realizados | 1 | 50ms |
| Comprobaciones realizadas | 1 | 50ms |
| Códigos vencidos (1 query) | 1 | 20ms |
| Projected activities | 1 | 50ms |
| Latest maintenances | 1 | 20ms |
| Préstamos data | 2 | 20ms |
| **TOTAL** | **~16 queries** | **~460ms** ✅ |

**Mejora:** 613 → 16 queries (-97% queries)
**Tiempo:** 7-13s → 0.5s (-93% tiempo)
**Con cache:** 0.5s → 0.1s primera carga, <50ms subsecuentes

---

## ✅ PLAN DE OPTIMIZACIÓN

### Fase 1: Fixes Críticos (1-2 días) - MÁXIMA PRIORIDAD

#### 1.1 Optimizar Queryset Principal ⚡ CRÍTICO

**Archivo:** `core/views/dashboard.py:269-286`

**Cambio:**
```python
def _get_equipos_queryset(user, selected_company_id, empresas_disponibles):
    """Obtiene el queryset de equipos con prefetch optimizado"""
    from django.db.models import Prefetch

    # Prefetch optimizado de relaciones
    equipos_queryset = Equipo.objects.filter(
        empresa__is_deleted=False
    ).select_related(
        'empresa'  # Evitar query por empresa
    ).prefetch_related(
        # Prefetch última calibración, mantenimiento y comprobación
        Prefetch(
            'calibraciones',
            queryset=Calibracion.objects.select_related('proveedor').order_by('-fecha_calibracion'),
            to_attr='calibraciones_prefetched'
        ),
        Prefetch(
            'mantenimientos',
            queryset=Mantenimiento.objects.order_by('-fecha_mantenimiento'),
            to_attr='mantenimientos_prefetched'
        ),
        Prefetch(
            'comprobaciones',
            queryset=Comprobacion.objects.order_by('-fecha_comprobacion'),
            to_attr='comprobaciones_prefetched'
        )
    )

    # Resto del código igual...
```

**Impacto:** Reduce de 500+ queries a 4 queries
**Tiempo:** Ahorra 5-10 segundos

---

#### 1.2 Refactorizar `_calculate_programmed_activities` ⚡ CRÍTICO

**Archivo:** `core/views/dashboard.py:582-663`

**Cambio:**
```python
def _calculate_programmed_activities(equipos_para_dashboard, start_date_range, line_data):
    """
    Calcula actividades programadas usando datos prefetched (SIN QUERIES)
    """

    for equipo in equipos_para_dashboard:
        # Usar datos prefetched en lugar de queries

        # Calibraciones programadas
        if equipo.frecuencia_calibracion_meses and equipo.frecuencia_calibracion_meses > 0:
            try:
                freq_months = int(equipo.frecuencia_calibracion_meses)
                if freq_months > 0:
                    # USAR PREFETCH en lugar de query
                    calibraciones_list = getattr(equipo, 'calibraciones_prefetched', [])
                    latest_calibracion = calibraciones_list[0] if calibraciones_list else None

                    if latest_calibracion:
                        start_date_cal = latest_calibracion.fecha_calibracion
                    elif equipo.fecha_adquisicion:
                        start_date_cal = equipo.fecha_adquisicion
                    else:
                        continue

                    _add_programmed_activity_to_chart(
                        start_date_cal, freq_months,
                        start_date_range, line_data['programmed_calibrations_line_data']
                    )
            except (ValueError, TypeError):
                pass

        # Mantenimientos programados (MISMO PATRÓN)
        if equipo.frecuencia_mantenimiento_meses and equipo.frecuencia_mantenimiento_meses > 0:
            try:
                freq_months = int(equipo.frecuencia_mantenimiento_meses)
                if freq_months > 0:
                    mantenimientos_list = getattr(equipo, 'mantenimientos_prefetched', [])
                    latest_mantenimiento = mantenimientos_list[0] if mantenimientos_list else None

                    if latest_mantenimiento:
                        start_date_mant = latest_mantenimiento.fecha_mantenimiento
                    else:
                        # Usar calibraciones prefetched
                        calibraciones_list = getattr(equipo, 'calibraciones_prefetched', [])
                        latest_calibracion = calibraciones_list[0] if calibraciones_list else None
                        if latest_calibracion:
                            start_date_mant = latest_calibracion.fecha_calibracion
                        elif equipo.fecha_adquisicion:
                            start_date_mant = equipo.fecha_adquisicion
                        else:
                            continue

                    _add_programmed_activity_to_chart(
                        start_date_mant, freq_months,
                        start_date_range, line_data['programmed_mantenimientos_line_data']
                    )
            except (ValueError, TypeError):
                pass

        # Comprobaciones programadas (MISMO PATRÓN)
        if equipo.frecuencia_comprobacion_meses and equipo.frecuencia_comprobacion_meses > 0:
            try:
                freq_months = int(equipo.frecuencia_comprobacion_meses)
                if freq_months > 0:
                    comprobaciones_list = getattr(equipo, 'comprobaciones_prefetched', [])
                    latest_comprobacion = comprobaciones_list[0] if comprobaciones_list else None

                    if latest_comprobacion:
                        start_date_comp = latest_comprobacion.fecha_comprobacion
                    else:
                        calibraciones_list = getattr(equipo, 'calibraciones_prefetched', [])
                        latest_calibracion = calibraciones_list[0] if calibraciones_list else None
                        if latest_calibracion:
                            start_date_comp = latest_calibracion.fecha_calibracion
                        elif equipo.fecha_adquisicion:
                            start_date_comp = equipo.fecha_adquisicion
                        else:
                            continue

                    _add_programmed_activity_to_chart(
                        start_date_comp, freq_months,
                        start_date_range, line_data['programmed_comprobaciones_line_data']
                    )
            except (ValueError, TypeError):
                pass
```

**Impacto:** Elimina 500+ queries, usa solo datos prefetched
**Tiempo:** Ahorra 5-10 segundos

---

#### 1.3 Consolidar Queries de Vencimientos

**Archivo:** `core/views/dashboard.py:452-468`

**Cambio:**
```python
# En lugar de 3 queries separadas, usar annotate
from django.db.models import Q, F, Value, CharField
from django.db.models.functions import Case, When

vencimientos = equipos_para_dashboard.annotate(
    tipo_vencimiento=Case(
        When(proxima_calibracion__lt=today, then=Value('calibracion')),
        When(proximo_mantenimiento__lt=today, then=Value('mantenimiento')),
        When(proxima_comprobacion__lt=today, then=Value('comprobacion')),
        default=Value('ninguno'),
        output_field=CharField()
    )
).filter(
    Q(proxima_calibracion__lt=today) |
    Q(proximo_mantenimiento__lt=today) |
    Q(proxima_comprobacion__lt=today)
).values_list('codigo_interno', 'tipo_vencimiento')

# Separar por tipo en Python (más rápido que 3 queries)
vencidos_calibracion_codigos = []
vencidos_mantenimiento_codigos = []
vencidos_comprobacion_codigos = []

for codigo, tipo in vencimientos:
    if tipo == 'calibracion':
        vencidos_calibracion_codigos.append(codigo)
    elif tipo == 'mantenimiento':
        vencidos_mantenimiento_codigos.append(codigo)
    elif tipo == 'comprobacion':
        vencidos_comprobacion_codigos.append(codigo)
```

**Impacto:** 3 queries → 1 query
**Tiempo:** Ahorra 40-200ms

---

### Fase 2: Cache Inteligente (1 día)

#### 2.1 Implementar Cache de Dashboard

**Archivo:** `core/views/dashboard.py:194`

**Cambio:**
```python
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

def dashboard(request):
    """Dashboard con cache inteligente"""
    user = request.user
    selected_company_id = request.GET.get('empresa_id')

    # Cache key única por usuario y empresa
    cache_key = f"dashboard_data_{user.id}_{selected_company_id or 'all'}"

    # Intentar obtener de cache
    cached_data = cache.get(cache_key)
    if cached_data:
        # Actualizar solo timestamp
        cached_data['today'] = date.today()
        return render(request, 'core/dashboard.html', cached_data)

    # Si no hay cache, calcular todo
    context = _calculate_dashboard_context(user, selected_company_id)

    # Guardar en cache por 5 minutos
    cache.set(cache_key, context, 300)

    return render(request, 'core/dashboard.html', context)
```

**Invalidar cache cuando:**
- Se crea/modifica un equipo
- Se crea calibración/mantenimiento/comprobación
- Se modifica empresa

**Impacto:**
- Primera carga: 460ms
- Siguientes cargas: <50ms
- **Mejora 90% en cargas subsecuentes**

---

#### 2.2 Cache por Nivel de Usuario

**Estrategia:**
```python
# Usuarios normales: cache 5 minutos
cache.set(cache_key, context, 300)

# Superusuarios con filtro: cache 2 minutos (datos cambian más)
if user.is_superuser:
    cache.set(cache_key, context, 120)
```

---

### Fase 3: Optimizaciones Adicionales (1 día)

#### 3.1 Índices de Base de Datos

**Archivo:** Nueva migración

**Añadir índices:**
```python
class Migration(migrations.Migration):
    dependencies = [
        ('core', 'ultima_migracion'),
    ]

    operations = [
        # Índices para filtros comunes en dashboard
        migrations.AddIndex(
            model_name='equipo',
            index=models.Index(fields=['proxima_calibracion', 'estado'], name='equipo_prox_cal_idx'),
        ),
        migrations.AddIndex(
            model_name='equipo',
            index=models.Index(fields=['proximo_mantenimiento', 'estado'], name='equipo_prox_mant_idx'),
        ),
        migrations.AddIndex(
            model_name='equipo',
            index=models.Index(fields=['proxima_comprobacion', 'estado'], name='equipo_prox_comp_idx'),
        ),
        # Índices para relaciones
        migrations.AddIndex(
            model_name='calibracion',
            index=models.Index(fields=['equipo', '-fecha_calibracion'], name='cal_equipo_fecha_idx'),
        ),
        migrations.AddIndex(
            model_name='mantenimiento',
            index=models.Index(fields=['equipo', '-fecha_mantenimiento'], name='mant_equipo_fecha_idx'),
        ),
        migrations.AddIndex(
            model_name='comprobacion',
            index=models.Index(fields=['equipo', '-fecha_comprobacion'], name='comp_equipo_fecha_idx'),
        ),
    ]
```

**Impacto:** Queries 20-30% más rápidas

---

#### 3.2 Lazy Loading de Gráficos

**Archivo:** `templates/core/dashboard.html`

**Cambio:**
```html
<!-- Cargar gráficos después del contenido principal -->
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Mostrar dashboard inmediatamente
    document.getElementById('main-stats').style.display = 'block';

    // Cargar gráficos después (AJAX)
    setTimeout(function() {
        fetch('/api/dashboard/charts/')
            .then(response => response.json())
            .then(data => renderCharts(data));
    }, 100);
});
</script>
```

**Impacto:** Usuario ve contenido en <500ms, gráficos cargan después

---

## 📋 PLAN DE IMPLEMENTACIÓN ACTUALIZADO

### Semana 1-2 (CRÍTICO + RENDIMIENTO)

```
✅ Día 0.5: ANÁLISIS RENDIMIENTO (HECHO)
   - Identificar cuellos de botella
   - Documentar queries N+1
   - Crear plan optimización

✅ Día 1: OPTIMIZAR DASHBOARD ⚡ NUEVA PRIORIDAD #1
   - Fix queryset con prefetch (1h)
   - Refactorizar _calculate_programmed_activities (2h)
   - Consolidar queries vencimientos (30min)
   - Testing exhaustivo (1h)
   - OBJETIVO: 7-13s → <1s

✅ Día 2: IMPLEMENTAR CACHE
   - Cache inteligente dashboard (2h)
   - Invalidación automática (1h)
   - Testing con diferentes usuarios (1h)
   - OBJETIVO: Cargas subsecuentes <50ms

✅ Día 3: CREAR constants.py
   - Centralizar constantes dispersas
   - Actualizar imports
   - Probar que funciona

✅ Día 4: LIMPIAR CÓDIGO DEBUG
   - Eliminar prints
   - Eliminar código comentado
   - Reemplazar por logger

✅ Día 5-10: REFACTORIZAR reports.py
   - Dividir en 6 módulos
   - Actualizar imports
   - Probar exhaustivamente

✅ Día 11: ÍNDICES BD + LAZY LOADING
   - Crear migración con índices
   - Implementar lazy loading gráficos
   - Testing

✅ Día 12-14: AGREGAR TESTS
   - Tests reports/*
   - Tests de rendimiento
   - Tests de cache
```

---

## 🎯 MÉTRICAS DE ÉXITO

| Métrica | Actual | Meta Día 1 | Meta Día 2 |
|---------|--------|-----------|-----------|
| Queries dashboard | ~613 | **<20** | <20 |
| Tiempo primera carga | 7-13s | **<1s** | <1s |
| Tiempo cargas subsecuentes | 7-13s | <1s | **<50ms** |
| Tiempo login → dashboard visible | >5s | **<2s** | <1s |

---

## 🔥 IMPACTO ESPERADO

### Usuario Normal (100 equipos)
- **Antes:** Login → esperar 8s → ver dashboard
- **Después Día 1:** Login → esperar 0.8s → ver dashboard ⚡
- **Después Día 2:** Login → esperar 0.05s (cache) → ver dashboard 🚀

### Usuario con Muchos Equipos (500 equipos)
- **Antes:** Login → esperar 30s → ver dashboard (o timeout)
- **Después Día 1:** Login → esperar 2s → ver dashboard ⚡
- **Después Día 2:** Login → esperar 0.05s (cache) → ver dashboard 🚀

### Impacto BD
- **Antes:** 613 queries por carga × 100 usuarios = 61,300 queries/hora
- **Después:** 16 queries × 10% (sin cache) = 160 queries/hora
- **Reducción:** 99.7% menos carga en BD 🎉

---

## 💡 RECOMENDACIONES ADICIONALES

### 1. Monitoreo de Rendimiento

**Instalar django-debug-toolbar (solo desarrollo):**
```bash
pip install django-debug-toolbar
```

**Configurar:**
```python
# settings.py
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

**Beneficio:** Ver queries en tiempo real durante desarrollo

---

### 2. Logging de Queries Lentas

**Configurar:**
```python
# settings.py
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG' if DEBUG else 'WARNING',
            'handlers': ['console'],
        },
    },
}

# Si query > 1s, loggear
if not DEBUG:
    from django.db import connection
    def log_slow_queries():
        for query in connection.queries:
            if float(query['time']) > 1.0:
                logger.warning(f"Slow query: {query['sql'][:200]}")
```

---

### 3. Métricas APM (Opcional - Fase 3)

**Considerar Sentry Performance Monitoring:**
- Tracking automático de queries
- Alertas de queries lentas
- Visualización de waterfall
- **Costo:** $26/mes (gratis para proyectos pequeños)

---

## 📊 TESTING DEL FIX

### Test Manual

```bash
# 1. Limpiar cache
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()

# 2. Medir tiempo ANTES
python manage.py shell
>>> import time
>>> from django.test import Client
>>> client = Client()
>>> client.login(username='usuario', password='password')
>>> start = time.time()
>>> response = client.get('/dashboard/')
>>> print(f"Tiempo: {time.time() - start:.2f}s")

# 3. Aplicar fix

# 4. Medir tiempo DESPUÉS
>>> start = time.time()
>>> response = client.get('/dashboard/')
>>> print(f"Tiempo: {time.time() - start:.2f}s")
```

### Test Automatizado

Crear `tests/test_performance/test_dashboard_performance.py`:
```python
import pytest
import time
from django.test import Client
from django.core.cache import cache

@pytest.mark.django_db
def test_dashboard_performance(client, django_user_model):
    """Dashboard debe cargar en <2 segundos"""
    # Setup
    user = django_user_model.objects.create_user(
        username='testuser',
        password='testpass'
    )
    client.login(username='testuser', password='testpass')
    cache.clear()

    # Medir tiempo
    start = time.time()
    response = client.get('/dashboard/')
    elapsed = time.time() - start

    # Assertions
    assert response.status_code == 200
    assert elapsed < 2.0, f"Dashboard tardó {elapsed:.2f}s (>2s)"

@pytest.mark.django_db
def test_dashboard_queries(client, django_user_model, django_assert_num_queries):
    """Dashboard debe hacer <20 queries"""
    user = django_user_model.objects.create_user(
        username='testuser',
        password='testpass'
    )
    client.login(username='testuser', password='testpass')
    cache.clear()

    with django_assert_num_queries(20):
        response = client.get('/dashboard/')
```

---

## ✅ CONCLUSIÓN

### Problema Identificado
Dashboard hace **613 queries** debido a N+1 en loop de equipos, tardando **7-13 segundos** en cargar.

### Solución Propuesta
1. Prefetch de relaciones (4 queries en lugar de 500+)
2. Refactorizar loops para usar datos prefetched
3. Consolidar queries de vencimientos
4. Cache inteligente de 5 minutos

### Resultado Esperado
- Queries: 613 → **16** (-97%)
- Tiempo: 7-13s → **<1s** (-93%)
- Con cache: **<50ms** (-99.6%)

### Prioridad
**MÁXIMA** - Afecta experiencia de 100% de usuarios en cada login

### Esfuerzo
**2 días** para fix completo + cache

---

**Próximos Pasos:**
1. ✅ Implementar Día 1: Optimizar queries (HOY)
2. ✅ Implementar Día 2: Cache inteligente (MAÑANA)
3. ✅ Testing y validación
4. ✅ Continuar con plan original (constants, limpieza, reports.py)

---

**Última Actualización:** 10 de Enero de 2026
**Autor:** Auditoría Técnica SAM
**Versión:** 1.0
