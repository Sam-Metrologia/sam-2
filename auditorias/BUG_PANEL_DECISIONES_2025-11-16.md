# BUG REPORT: Error 500 en Panel de Decisiones
**Fecha:** 16 de Noviembre de 2025
**Severidad:** 🔴 ALTA
**Afectación:** Panel de Decisiones con empresa_id=31
**Status:** EN INVESTIGACIÓN

---

## 📋 DESCRIPCIÓN DEL PROBLEMA

### Error Reportado
```
GET https://app.sammetrologia.com/core/panel-decisiones/?empresa_id=31
Status: 500 (Internal Server Error)
```

### Logs de Producción
```
10.22.88.166 - - [16/Nov/2025:14:48:06 -0500]
"GET /core/panel-decisiones/?empresa_id=31 HTTP/1.1" 500 145
```

**Contexto:**
- Usuario accede al panel de decisiones
- Selecciona empresa_id=31
- La vista falla con error 500

---

## 🔍 ANÁLISIS DEL PROBLEMA

### Archivos Involucrados

1. **`core/views/panel_decisiones.py`** (líneas 470-596)
2. **`core/utils/analisis_financiero.py`** (líneas 1-150)

### Causas Potenciales Identificadas

#### 🔴 CAUSA #1: División por Zero en Decimals

**Ubicación:** `core/utils/analisis_financiero.py:33`

```python
total_gasto_ytd = float(costos_calibracion_ytd) + float(costos_mantenimiento_ytd) + float(costos_comprobacion_ytd)
```

**Problema:**
- Si `costos_calibracion_ytd` es un objeto `Decimal` (de `.aggregate()`) y tiene valor `0` o `None`
- La conversión `float(None)` causa `TypeError`
- La conversión de `Decimal` puede causar problemas de precisión

**Solución:**
```python
# CORRECCIÓN RECOMENDADA:
from decimal import Decimal

costos_calibracion_ytd = Calibracion.objects.filter(...).aggregate(
    total=Sum('costo_calibracion')
)['total'] or Decimal('0')  # ← Usar Decimal('0') en lugar de 0

total_gasto_ytd = costos_calibracion_ytd + costos_mantenimiento_ytd + costos_comprobacion_ytd
# No convertir a float hasta el final, mantener Decimal para precisión
```

---

#### 🔴 CAUSA #2: División por Zero en Cálculo de Variación

**Ubicación:** `core/views/panel_decisiones.py:505-506`

```python
if analisis_financiero['gasto_ytd_total'] > 0:
    variacion_porcentaje = round(((proyeccion_costos['proyeccion_gasto_proximo_año'] /
                                   analisis_financiero['gasto_ytd_total']) * 100) - 100, 1)
```

**Problema:**
- Si `proyeccion_costos['proyeccion_gasto_proximo_año']` es `Decimal` y `analisis_financiero['gasto_ytd_total']` es `float` → puede causar error de tipo
- Si ambos son 0 pero pasa la validación → división por zero

**Solución:**
```python
# CORRECCIÓN RECOMENDADA:
from decimal import Decimal

gasto_ytd = Decimal(str(analisis_financiero['gasto_ytd_total']))
proyeccion = Decimal(str(proyeccion_costos['proyeccion_gasto_proximo_año']))

if gasto_ytd > 0 and proyeccion > 0:
    variacion_porcentaje = round(float((proyeccion / gasto_ytd) * 100) - 100, 1)
    diferencia_absoluta = float(proyeccion - gasto_ytd)
else:
    variacion_porcentaje = 0
    diferencia_absoluta = 0
```

---

#### 🟡 CAUSA #3: Problema con `strftime('%B')` en línea 520

**Ubicación:** `core/views/panel_decisiones.py:520`

```python
'periodo': f"Enero-{today.strftime('%B')} {current_year}",
```

**Problema:**
- `strftime('%B')` devuelve el nombre del mes en inglés si la localización no está configurada
- Podría causar problemas de encoding en algunos entornos

**Solución:**
```python
# CORRECCIÓN RECOMENDADA:
import calendar
import locale

# Configurar locale español (ya debería estar en settings.py)
locale.setlocale(locale.LC_TIME, 'es_CO.UTF-8')

nombre_mes = today.strftime('%B')  # Ahora retorna en español
# O usar calendar.month_name[today.month] con traducción
```

---

#### 🟡 CAUSA #4: KeyError en Diccionarios de Tendencias

**Ubicación:** `core/views/panel_decisiones.py:589-593`

```python
'tendencias_chart_data': json.dumps([{
    'mes': item['nombre_mes'],
    'gasto': float(item['gasto_total']),  # ← Podría fallar si item no tiene 'gasto_total'
    'actividades': item['actividades']
} for item in tendencias_historicas['datos_mensuales']]),
```

**Problema:**
- Si `calcular_tendencias_historicas()` retorna datos incompletos
- Si algún mes no tiene 'nombre_mes', 'gasto_total' o 'actividades' → KeyError

**Solución:**
```python
# CORRECCIÓN RECOMENDADA:
'tendencias_chart_data': json.dumps([{
    'mes': item.get('nombre_mes', 'Desconocido'),
    'gasto': float(item.get('gasto_total', 0)),
    'actividades': item.get('actividades', 0)
} for item in tendencias_historicas.get('datos_mensuales', [])]),
```

---

## 🛠️ SOLUCIÓN INMEDIATA (HOTFIX)

### Paso 1: Agregar Logging Detallado

**Editar:** `core/views/panel_decisiones.py` línea 470

```python
def _panel_decisiones_empresa(request, today, current_year, empresa_override=None):
    """Panel de Decisiones para GERENCIA de empresa individual"""
    import logging
    logger = logging.getLogger('core')

    try:
        user = request.user
        empresa = empresa_override if empresa_override else user.empresa

        logger.info(f"Panel decisiones - Empresa ID: {empresa.id}, Nombre: {empresa.nombre}")

        # ... resto del código

        # 4. ANÁLISIS FINANCIERO - AGREGAR TRY/CATCH
        try:
            analisis_financiero = calcular_analisis_financiero_empresa(empresa, current_year, today)
            logger.info(f"Análisis financiero OK: {analisis_financiero}")
        except Exception as e:
            logger.error(f"Error en análisis financiero empresa {empresa.id}: {e}", exc_info=True)
            # Valores por defecto
            analisis_financiero = {
                'gasto_ytd_total': 0,
                'costos_calibracion_ytd': 0,
                'costos_mantenimiento_ytd': 0,
                'costos_comprobacion_ytd': 0,
                'porcentaje_calibracion': 0,
                'porcentaje_mantenimiento': 0,
                'porcentaje_comprobacion': 0,
            }

        # ... continuar

    except Exception as e:
        logger.error(f"Error GENERAL en panel decisiones empresa {empresa.id if empresa else 'N/A'}: {e}", exc_info=True)
        raise  # Re-lanzar para ver el stacktrace completo
```

---

### Paso 2: Corregir Función de Análisis Financiero

**Editar:** `core/utils/analisis_financiero.py`

```python
from decimal import Decimal

def calcular_analisis_financiero_empresa(empresa, current_year, today):
    """Análisis financiero con manejo robusto de Decimals"""
    import logging
    logger = logging.getLogger('core')

    try:
        # Costos YTD - USAR DECIMAL EXPLÍCITAMENTE
        costos_calibracion_ytd = Calibracion.objects.filter(
            equipo__empresa=empresa,
            fecha_calibracion__year=current_year,
            fecha_calibracion__lte=today
        ).aggregate(total=Sum('costo_calibracion'))['total'] or Decimal('0')

        costos_mantenimiento_ytd = Mantenimiento.objects.filter(
            equipo__empresa=empresa,
            fecha_mantenimiento__year=current_year,
            fecha_mantenimiento__lte=today
        ).aggregate(total=Sum('costo_sam_interno'))['total'] or Decimal('0')

        costos_comprobacion_ytd = Comprobacion.objects.filter(
            equipo__empresa=empresa,
            fecha_comprobacion__year=current_year,
            fecha_comprobacion__lte=today
        ).aggregate(total=Sum('costo_comprobacion'))['total'] or Decimal('0')

        # MANTENER COMO DECIMAL HASTA EL FINAL
        total_gasto_ytd = costos_calibracion_ytd + costos_mantenimiento_ytd + costos_comprobacion_ytd

        # Calcular porcentajes con validación
        if total_gasto_ytd > 0:
            porcentaje_calibracion = round(float(costos_calibracion_ytd / total_gasto_ytd) * 100, 1)
            porcentaje_mantenimiento = round(float(costos_mantenimiento_ytd / total_gasto_ytd) * 100, 1)
            porcentaje_comprobacion = round(float(costos_comprobacion_ytd / total_gasto_ytd) * 100, 1)
        else:
            porcentaje_calibracion = porcentaje_mantenimiento = porcentaje_comprobacion = 0

        # CONVERTIR A FLOAT SOLO PARA RETORNO (para JSON)
        return {
            'gasto_ytd_total': float(total_gasto_ytd),
            'costos_calibracion_ytd': float(costos_calibracion_ytd),
            'costos_mantenimiento_ytd': float(costos_mantenimiento_ytd),
            'costos_comprobacion_ytd': float(costos_comprobacion_ytd),
            'porcentaje_calibracion': porcentaje_calibracion,
            'porcentaje_mantenimiento': porcentaje_mantenimiento,
            'porcentaje_comprobacion': porcentaje_comprobacion,
        }

    except Exception as e:
        logger.error(f"Error calculando análisis financiero para empresa {empresa.id}: {e}", exc_info=True)
        # Retornar valores seguros
        return {
            'gasto_ytd_total': 0.0,
            'costos_calibracion_ytd': 0.0,
            'costos_mantenimiento_ytd': 0.0,
            'costos_comprobacion_ytd': 0.0,
            'porcentaje_calibracion': 0,
            'porcentaje_mantenimiento': 0,
            'porcentaje_comprobacion': 0,
        }
```

---

### Paso 3: Corregir Cálculo de Variación

**Editar:** `core/views/panel_decisiones.py` líneas 503-540

```python
# Calcular variación proyectada con validación robusta
from decimal import Decimal

try:
    gasto_ytd = Decimal(str(analisis_financiero.get('gasto_ytd_total', 0)))
    proyeccion_gasto = Decimal(str(proyeccion_costos.get('proyeccion_gasto_proximo_año', 0)))

    if gasto_ytd > 0 and proyeccion_gasto > 0:
        variacion_porcentaje = round(float((proyeccion_gasto / gasto_ytd) * 100) - 100, 1)
        diferencia_absoluta = float(proyeccion_gasto - gasto_ytd)
    else:
        variacion_porcentaje = 0
        diferencia_absoluta = 0

except (TypeError, ValueError, ZeroDivisionError, KeyError) as e:
    logger.warning(f"Error calculando variación para empresa {empresa.id}: {e}")
    variacion_porcentaje = 0
    diferencia_absoluta = 0

# Fórmulas con validación de keys
formula_gastos_reales = {
    'total': analisis_financiero.get('gasto_ytd_total', 0),
    'calibraciones': analisis_financiero.get('costos_calibracion_ytd', 0),
    'mantenimientos': analisis_financiero.get('costos_mantenimiento_ytd', 0),
    'comprobaciones': analisis_financiero.get('costos_comprobacion_ytd', 0),
    'porcentaje_cal': analisis_financiero.get('porcentaje_calibracion', 0),
    'porcentaje_mant': analisis_financiero.get('porcentaje_mantenimiento', 0),
    'porcentaje_comp': analisis_financiero.get('porcentaje_comprobacion', 0),
    'periodo': f"Enero-{today.strftime('%B')} {current_year}",
    'calculo_ejemplo': f"${analisis_financiero.get('costos_calibracion_ytd', 0):,.0f} + ${analisis_financiero.get('costos_mantenimiento_ytd', 0):,.0f} + ${analisis_financiero.get('costos_comprobacion_ytd', 0):,.0f} = ${analisis_financiero.get('gasto_ytd_total', 0):,.0f} COP"
}
```

---

## 🧪 TESTING

### Test Manual en Desarrollo

```bash
# 1. Activar entorno
cd C:\Users\LENOVO\OneDrive\Escritorio\sam-2
python manage.py shell

# 2. Simular el error
from core.models import Empresa
from core.utils.analisis_financiero import calcular_analisis_financiero_empresa
from datetime import date

empresa = Empresa.objects.get(id=31)
today = date.today()
current_year = today.year

# Ejecutar y ver errores
resultado = calcular_analisis_financiero_empresa(empresa, current_year, today)
print(resultado)
```

### Test Automatizado

**Crear:** `tests/test_views/test_panel_decisiones_bug.py`

```python
import pytest
from django.urls import reverse
from core.models import Empresa

@pytest.mark.django_db
class TestPanelDecisionesBug:

    def test_panel_con_empresa_sin_datos(self, authenticated_client, empresa_factory):
        """Test panel con empresa sin calibraciones/mantenimientos"""
        empresa = empresa_factory(id=31)

        url = reverse('core:panel_decisiones') + f'?empresa_id={empresa.id}'
        response = authenticated_client.get(url)

        # No debe dar error 500
        assert response.status_code == 200
        assert 'gasto_ytd_total' in response.context

    def test_calculo_variacion_con_zeros(self, authenticated_client, empresa_factory):
        """Test cálculo de variación cuando gastos son 0"""
        empresa = empresa_factory()

        # Empresa sin actividades = gastos en 0
        url = reverse('core:panel_decisiones') + f'?empresa_id={empresa.id}'
        response = authenticated_client.get(url)

        assert response.status_code == 200
        # No debe fallar con división por zero
```

---

## 📊 IMPACTO Y PRIORIDAD

**Severidad:** 🔴 ALTA
- Afecta funcionalidad crítica de toma de decisiones
- Bloquea acceso al panel para empresa específica

**Usuarios Afectados:**
- Empresa ID=31
- Posiblemente otras empresas con datos similares

**Prioridad de Fix:** 🔴 INMEDIATA
- Deploy hotfix en <24 horas

---

## 📝 PLAN DE ACCIÓN

### Hoy (16 Nov 2025)
- [ ] Agregar logging detallado en panel_decisiones.py
- [ ] Revisar logs de producción en Render para ver stacktrace completo
- [ ] Identificar causa raíz específica

### Mañana (17 Nov 2025)
- [ ] Implementar correcciones en analisis_financiero.py
- [ ] Implementar correcciones en panel_decisiones.py
- [ ] Testing local exhaustivo
- [ ] Crear tests automatizados
- [ ] Code review

### Deploy (18 Nov 2025)
- [ ] Deploy a producción (main)
- [ ] Verificar en empresa_id=31
- [ ] Monitorear logs 24 horas
- [ ] Cerrar issue

---

## 🔗 REFERENCIAS

- **Auditoría Completa:** `auditorias/AUDITORIA_COMPLETA_2025-11-13.md` (Sección Seguridad)
- **DEVELOPER-GUIDE.md:** Sección "Áreas Críticas" → Modelos Financieros
- **Historial Similar:** Bug de Decimal en panel decisiones (Nov 2024) - Ver DEVELOPER-GUIDE líneas 34-46

---

## 📞 CONTACTO

**Reportado por:** Usuario en producción
**Investigado por:** Equipo de desarrollo
**Fecha:** 16 de Noviembre de 2025
**Status:** 🔴 EN INVESTIGACIÓN

---

**PRÓXIMO PASO:** Revisar logs completos de producción en Render Dashboard para confirmar stacktrace exacto.
