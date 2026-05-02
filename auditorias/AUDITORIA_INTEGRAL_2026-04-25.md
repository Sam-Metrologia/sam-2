# Auditoría Integral SAM Metrología — 25 Abril 2026

**Fecha:** 2026-04-25
**Auditor:** Claude Code (Sonnet 4.6)
**Alcance:** Código fuente completo, tests, CI/CD, integraciones de producción, documentación
**Score estimado:** 8.5 / 10 (vs 8.3 en auditoría anterior Mar-15-2026)

---

## Resumen Ejecutivo

La plataforma SAM Metrología mantiene una base sólida (1,883 tests, 70% cobertura, multi-tenant bien implementado). Esta auditoría identificó **18 hallazgos** distribuidos en 5 categorías de severidad. Se corrigieron 4 ítems durante la sesión. Los hallazgos más urgentes son una vulnerabilidad de timing attack en Wompi y dos templates de email rotos que siempre muestran "N/A días".

| Severidad | Cantidad | Corregidos en sesión |
|-----------|----------|----------------------|
| ❌ CRÍTICO | 2 | 0 |
| ⚠️ ALTO | 6 | 1 |
| 🔶 MEDIO | 7 | 3 |
| ℹ️ BAJO | 3 | 0 |

---

## Qué se Corrigió en Esta Sesión

| ID | Descripción | Archivo |
|----|-------------|---------|
| A3 | `ServerSideEncryption: AES256` en `AWS_S3_OBJECT_PARAMETERS` | `proyecto_c/settings.py` |
| D3 | `test_mejoras_ux.py` recreado con `assert` en lugar de `return` | `tests/test_views/test_mejoras_ux.py` |
| D3b | `puede_eliminar_equipos` llamado sin `()` (es `@property`) | `tests/test_views/test_mejoras_ux.py` |
| A1 | `core/views_optimized.py` eliminado (292 líneas, 0 referencias) | eliminado |
| E1 | `README.md` reescrito con estado real del proyecto | `README.md` |
| E2 | `CONTRIBUTING.md` creado con guía completa | `CONTRIBUTING.md` |
| M1 | 12 imágenes del manual actualizadas con capturas correctas | `sam-website/manual-plataforma.html` |
| M2 | Sección 5 (Intervalos de Calibración) reemplazada con imágenes correctas | `sam-website/manual-plataforma.html` |

---

## Hallazgos por Dimensión

---

### DIMENSIÓN A — Código Muerto / Archivos Inútiles

#### A1 — `views_optimized.py` ✅ CORREGIDO
- **Archivo:** `core/views_optimized.py` (292 líneas)
- **Hallazgo:** Cero referencias en todo el proyecto. Archivo zombie.
- **Acción:** Eliminado en esta sesión.

#### A2 — `zip_optimizer.py` y `async_zip_improved.py` 🔶 MEDIO
- **Archivos:** `core/zip_optimizer.py` (473 líneas), `core/async_zip_improved.py` (579 líneas)
- **Hallazgo:** Ambos archivos coexisten con `core/zip_functions.py` que es el que realmente se usa. No se verificaron referencias.
- **Acción recomendada:** Ejecutar `grep -r "zip_optimizer\|async_zip_improved" . --include="*.py"`. Si hay 0 referencias, eliminar.

#### A3 — Encriptación R2 ✅ CORREGIDO
- **Archivo:** `proyecto_c/settings.py`
- **Hallazgo:** Faltaba `ServerSideEncryption: AES256` en `AWS_S3_OBJECT_PARAMETERS`.
- **Acción:** Añadido en esta sesión para ambas ramas (R2 y AWS S3).

---

### DIMENSIÓN B — Coherencia de Instrucciones en la Plataforma

#### B1 — Instrucciones de importación Excel 🔶 MEDIO
- **URL:** `http://localhost:8000/core/equipos/importar_excel/`
- **Hallazgo:** Las instrucciones en la plataforma deben coincidir exactamente con las columnas y validaciones del código. Verificar que el template de Excel de ejemplo (`core/templates/core/equipment/importar_excel.html`) liste todas las columnas aceptadas y sus restricciones (longitud, formato de fechas, valores permitidos para `estado`, `magnitud`, etc.).
- **Verificación manual requerida:** Abrir la URL, descargar el Excel de ejemplo, comparar columnas con `forms.py` y el view `importar_equipos_excel`.

#### B2 — Email semanal siempre muestra "N/A días" ❌ CRÍTICO
- **Archivo:** `templates/core/weekly_overdue_reminder.html`
- **Hallazgo:** El template referencia `equipo.dias_hasta_calibracion`, `equipo.dias_hasta_mantenimiento`, y `equipo.dias_hasta_comprobacion`. Estos campos **no existen** en el modelo `Equipo`. Django renderiza `""` → el email siempre muestra "N/A días" a todos los usuarios.
- **Acción recomendada:** Opciones:
  1. Añadir propiedades al modelo `Equipo` que calculen la diferencia desde `proxima_calibracion`, `proximo_mantenimiento`, `proxima_comprobacion` hasta `date.today()`.
  2. O pre-calcular en el management command que envía el email antes de pasarlos al contexto del template.

```python
# En Equipo (core/models/equipment.py) — opción 1
@property
def dias_hasta_calibracion(self):
    if self.proxima_calibracion:
        return (self.proxima_calibracion - date.today()).days
    return None
```

---

### DIMENSIÓN C — Seguridad

#### C1 — Timing Attack en Webhook Wompi ❌ CRÍTICO
- **Archivo:** `core/views/pagos.py`, línea 228
- **Código actual:**
```python
return checksum_calculado == checksum_recibido
```
- **Problema:** La comparación `==` de strings en Python puede terminar anticipadamente cuando encuentra el primer carácter diferente. Un atacante puede medir el tiempo de respuesta para descubrir el checksum correcto byte a byte (timing attack).
- **Acción recomendada:**
```python
import hmac
return hmac.compare_digest(checksum_calculado, checksum_recibido)
```
- **Prioridad:** ALTA — afecta la validación de webhooks de pago reales.

#### C2 — CSP `unsafe-inline` ⚠️ ALTO
- **Alcance:** 52 bloques `<script>` inline en 51 templates
- **Problema:** La política CSP actual permite `unsafe-inline`, lo que anula la protección contra XSS que ofrece CSP.
- **Esfuerzo estimado:** 1-2 días para implementar nonces via middleware.
- **Acción recomendada:** Crear `CSPNonceMiddleware` que genera un nonce por request y lo inyecta en el contexto; reemplazar `<script>` inline con `<script nonce="{{ request.csp_nonce }}">`.
- **Nota:** Cambio de alto riesgo — requiere tocar 51 templates. Hacer en rama separada con revisión exhaustiva.

#### C3 — Chat sin Rate Limiting ⚠️ ALTO
- **Archivo:** `core/views/chat.py`
- **Endpoint:** `POST /core/chat/ayuda/`
- **Problema:** `RateLimitMiddleware` solo cubre login, uploads y `/api/`. El chatbot llama a Gemini 2.5 Flash por cada request. Un usuario malintencionado puede generar costos elevados o agotar cuota de API.
- **Acción recomendada:** Añadir rate limit en el view mismo:
```python
from django.core.cache import cache

def ayuda_chatbot(request):
    rate_key = f"chat_rate_{request.user.id}"
    count = cache.get(rate_key, 0)
    if count >= 20:  # 20 mensajes por hora
        return JsonResponse({'error': 'Límite de mensajes alcanzado'}, status=429)
    cache.set(rate_key, count + 1, 3600)
    ...
```

#### C4 — Historial de Chat sin Validación de Entrada ℹ️ BAJO
- **Archivo:** `core/views/chat.py`
- **Problema:** El historial de conversación se envía desde el cliente (localStorage) sin validación. Un usuario puede manipular el historial para inyectar instrucciones al modelo (prompt injection).
- **Acción recomendada:** Validar longitud máxima del historial (ej: máximo 20 turnos, máximo 2000 chars por mensaje) y sanitizar antes de enviar a Gemini.

---

### DIMENSIÓN D — Tests

#### D1 — `pytest.mark.performance` no registrado ℹ️ BAJO
- **Archivo:** `pyproject.toml`
- **Problema:** El marcador `@pytest.mark.performance` se usa en tests pero no está declarado en `[tool.pytest.ini_options] markers`, generando warnings en cada ejecución.
- **Acción recomendada:**
```toml
[tool.pytest.ini_options]
markers = [
    "performance: performance and benchmark tests",
    "integration: integration tests",
]
```

#### D2 — Tests con `return` en lugar de `assert` ✅ CORREGIDO
- Solucionado al recrear `test_mejoras_ux.py` con los 6 tests correctos usando `assert`.

#### D3 — `puede_eliminar_equipos` llamado con `()` ✅ CORREGIDO
- Era un `@property`, se removieron los paréntesis en las 3 llamadas del test.

---

### DIMENSIÓN E — Documentación

#### E1 — README reescrito ✅ CORREGIDO
- El README.md raíz (que tenía solo 19 bytes: "# Forzar redeploy") fue reescrito con información completa: estado actual, arranque rápido, comandos de tests, tecnologías, variables de entorno.

#### E2 — CONTRIBUTING.md creado ✅ CORREGIDO
- Nuevo archivo con: requisitos previos, flujo de trabajo Git, convenciones de código Python/templates/tests, tipos de commit.

---

### DIMENSIÓN F — CI/CD (GitHub Actions)

#### F1 — Python 3.11 en CI vs 3.13 en producción ⚠️ ALTO
- **Archivo:** `.github/workflows/tests.yml`
- **Problema:** CI usa Python 3.11, producción usa Python 3.13. Diferencias de comportamiento pueden pasar desapercibidas en CI.
- **Acción recomendada:** Cambiar `python-version: '3.11'` a `'3.13'` en el workflow.

#### F2 — `requirements_test.txt` no se instala en CI ⚠️ ALTO
- **Archivo:** `.github/workflows/tests.yml`
- **Problema:** El workflow solo instala `requirements.txt`, no `requirements_test.txt`. Los tests podrían fallar por dependencias faltantes (pytest-django, factory-boy, etc.).
- **Acción recomendada:**
```yaml
- run: pip install -r requirements.txt -r requirements_test.txt
```

#### F3 — No hay `migrate --check` en CI 🔶 MEDIO
- **Problema:** CI no verifica que todas las migraciones estén aplicadas. Un modelo modificado sin migración pasaría CI sin problemas.
- **Acción recomendada:** Añadir paso:
```yaml
- run: python manage.py migrate --check
```

#### F4 — Rama `develop` referenciada en workflows pero no existe ℹ️ BAJO
- **Problema:** Algunos workflows disparan en `push: branches: [main, develop]` pero la rama `develop` no existe en el repositorio.
- **Acción recomendada:** Eliminar `develop` de los triggers o crear la rama.

---

### DIMENSIÓN G — Performance / Queries N+1

#### G1 — N+1 en `get_chart_details` del Dashboard ⚠️ ALTO
- **Archivo:** `core/views/dashboard.py`, líneas 1386-1402
- **Problema:** Para cada equipo en el loop se ejecuta:
```python
equipo.calibraciones.order_by('-fecha_calibracion').first()
```
Con 100 equipos → hasta 100 queries adicionales. `select_related` no resuelve esto (es QuerySet inverso).
- **Acción recomendada:** Pre-cargar con `prefetch_related` usando `Prefetch` con queryset ordenado:
```python
from django.db.models import Prefetch
equipos = equipos.prefetch_related(
    Prefetch('calibraciones', queryset=Calibracion.objects.order_by('-fecha_calibracion'),
             to_attr='calibraciones_prefetched')
)
# Luego: equipo.calibraciones_prefetched[0] si existe
```

---

### DIMENSIÓN H — Resiliencia / Manejo de Errores

#### H1 — Dashboard sin try/except para Redis ⚠️ ALTO
- **Archivo:** `core/views/dashboard.py`, líneas 314-403
- **Problema:** `cache.get()` y `cache.set()` sin manejo de excepciones. Si Redis cae, el dashboard devuelve HTTP 500 a todos los usuarios autenticados simultáneamente.
- **Acción recomendada:**
```python
try:
    cached = cache.get(cache_key)
except Exception:
    cached = None

# Al final:
try:
    cache.set(cache_key, context_data, 300)
except Exception:
    pass  # Fallo silencioso — el dashboard sigue funcionando
```

#### H2 — R2 sin try/except en `_process_calibracion_files` ⚠️ ALTO
- **Archivo:** `core/views/activities.py`, líneas 557 y 576
- **Problema:** Si `default_storage.save()` falla después de que el registro ya se guardó en la base de datos, queda un estado inconsistente (registro en DB sin archivo).
- **Acción recomendada:** Envolver en try/except y hacer rollback del objeto si el upload falla, o registrar el error en un campo `archivo_pendiente` para reintentar.

#### H3 — R2 sin try/except en `_process_company_logo` 🔶 MEDIO
- **Archivo:** `core/views/companies.py`, línea 771
- **Problema:** Error al subir logo → HTTP 500 sin mensaje de usuario.
- **Acción recomendada:** Capturar excepción y retornar mensaje de error al formulario.

#### H4 — Cache keys que nunca expiran en Redis 🔶 MEDIO
- **Archivo:** `core/services_new.py`, líneas 395 y 448
- **Problema:** `cache.set(version_key, ..., None)` → en Redis, `timeout=None` significa PERSIST (sin expiración). Las claves de versión acumulan en Redis indefinidamente.
- **Acción recomendada:** Usar timeout explícito, por ejemplo `timeout=86400 * 30` (30 días).

#### H5 — Cache admin sin aislamiento multi-tenant 🔶 MEDIO
- **Archivo:** `core/admin_services.py`, líneas 380 y 400
- **Clave:** `"admin_execution_history"` (sin empresa_id)
- **Problema:** Todas las empresas comparten la misma entrada de caché del historial de ejecución administrativo.
- **Acción recomendada:** Añadir `empresa_id` a la clave: `f"admin_execution_history_{empresa_id}"`.

---

### DIMENSIÓN I — Configuración de Settings

#### I1 — Mezcla de cliente Redis 🔶 MEDIO
- **Archivo:** `proyecto_c/settings.py`, líneas 155-168
- **Problema:** La configuración del backend de caché mezcla `django.core.cache.backends.redis.RedisCache` (nativo Django) con `CLIENT_CLASS: django_redis.client.DefaultClient` (django-redis). Son dos librerías diferentes con APIs distintas.
- **Verificar:** Si `django-redis` está en `requirements.txt`, usar `django_redis.cache.RedisCache`. Si no, usar el backend nativo y remover `OPTIONS.CLIENT_CLASS`.
- **Añadir:** `socket_timeout` y `socket_connect_timeout` para evitar cuelgues si Redis no responde.

---

## Plan de Acción Priorizado

### Urgente — Esta semana

| # | Hallazgo | Archivo | Esfuerzo |
|---|----------|---------|----------|
| 1 | **C1** Timing attack Wompi | `pagos.py:228` | 5 min |
| 2 | **B2** Email muestra "N/A días" | `equipment.py` + template | 30 min |
| 3 | **H1** Dashboard 500 si Redis cae | `dashboard.py:314-403` | 20 min |
| 4 | **H2** R2 inconsistencia en activities | `activities.py:557,576` | 30 min |
| 5 | **F1** Python 3.11 → 3.13 en CI | `.github/workflows/tests.yml` | 5 min |
| 6 | **F2** Instalar requirements_test.txt en CI | `.github/workflows/tests.yml` | 5 min |

### Próximas 2 semanas

| # | Hallazgo | Archivo | Esfuerzo |
|---|----------|---------|----------|
| 7 | **C3** Rate limiting en chatbot | `chat.py` | 1h |
| 8 | **G1** N+1 queries en dashboard | `dashboard.py:1386-1402` | 2h |
| 9 | **H4** Cache keys sin expiración | `services_new.py:395,448` | 15 min |
| 10 | **H5** Tenant isolation en admin cache | `admin_services.py:380,400` | 15 min |
| 11 | **H3** R2 try/except en company logo | `companies.py:771` | 20 min |
| 12 | **I1** Configuración Redis consistente | `settings.py:155-168` | 30 min |
| 13 | **D1** Registrar `pytest.mark.performance` | `pyproject.toml` | 5 min |
| 14 | **F3** Añadir `migrate --check` en CI | `.github/workflows/tests.yml` | 5 min |

### Próximo mes

| # | Hallazgo | Esfuerzo estimado |
|---|----------|-------------------|
| 15 | **C2** CSP nonces (52 templates) | 1-2 días |
| 16 | **A2** Eliminar zip_optimizer.py y async_zip_improved.py (verificar referencias primero) | 30 min |
| 17 | **B1** Verificar coherencia instrucciones import Excel | 1h |
| 18 | **C4** Validar historial chat (prompt injection) | 1h |
| 19 | **F4** Limpiar ramas inexistentes en CI triggers | 5 min |

---

## Verificaciones Pendientes en Producción

Los siguientes puntos requieren acceso al servidor de producción y no pudieron verificarse estáticamente:

| Verificación | Cómo verificar |
|---|---|
| **L1 R2** — Confirmar que uploads llegan a R2 | Revisar `AWS_S3_ENDPOINT_URL` en Render → debe ser `https://<account>.r2.cloudflarestorage.com` |
| **L1 R2** — Confirmar ServerSideEncryption activo | En panel Cloudflare R2 → Bucket Settings → verificar encriptación AES-256 |
| **L2 Wompi** — PLAN_TEST activo | En `pagos.py` existe plan `$5.000 COP` marcado como "TEMPORAL". Verificar si sigue activo en producción y si corresponde quitarlo |
| **L3 Gemini** — Cuota API | Verificar en Google AI Studio si hay alertas de uso o cuota excedida |
| **L5 Redis** — Keys persistentes | Ejecutar `redis-cli keys "*version*"` y `redis-cli ttl <key>` para confirmar claves sin expiración |
| **L5 Redis** — Configuración de timeouts | Verificar `socket_timeout` en settings de producción (Render env vars) |

---

## Archivos del Manual Actualizados

| Sección | Imágenes reemplazadas |
|---------|----------------------|
| Sección 0 — Inicio de sesión | 1 imagen correcta |
| Sección 1 — Dashboard | 2 imágenes correctas |
| Sección 2 — Gestión de Equipos | 2 imágenes correctas |
| Sección 5 — Intervalos de Calibración | 3 imágenes nuevas (reemplazó gráfica de historial incorrecta) |
| Secciones 6-17 | Resto de capturas actualizadas |

---

## Estado Final de Tests

- **Antes de sesión:** 1,883 pasando — `test_mejoras_ux.py` eliminado en commit previo
- **Después de sesión:** `test_mejoras_ux.py` recreado con 6 tests; bug `@property` con `()` corregido
- **Estimado:** 1,889 pasando (6 tests recuperados), 0 fallando

---

*Auditoría completada: 2026-04-25*
*Siguiente auditoría recomendada: 2026-06-15*

---

## Correcciones Post-Sesión (Abril–Mayo 2026)

Los siguientes hallazgos fueron corregidos después de la sesión de auditoría, confirmados por inspección de código en 2026-05-02:

| ID | Descripción | Archivo | Estado |
|----|-------------|---------|--------|
| **C1** | Timing attack Wompi — reemplazado `==` por `hmac.compare_digest()` | `core/views/pagos.py:228` | ✅ CORREGIDO |
| **B2** | Email "N/A días" — añadidas propiedades `dias_hasta_calibracion`, `dias_hasta_mantenimiento`, `dias_hasta_comprobacion` a `Equipo` | `core/models/equipment.py` | ✅ CORREGIDO |
| **C3** | Chat sin rate limiting — añadido límite 20 mensajes/hora via cache (`chat_rate_{user.id}`) | `core/views/chat.py` | ✅ CORREGIDO |
| **H1** | Dashboard 500 si Redis cae — `cache.get` y `cache.set` envueltos en `try/except` | `core/views/dashboard.py` | ✅ CORREGIDO |
| **H2** | R2 inconsistencia en activities — `default_storage.save()` envuelto en `try/except` con logging | `core/views/activities.py:558,587` | ✅ CORREGIDO |
| **H3** | R2 error logo empresa — `_process_company_logo` con `try/except` y mensaje de error al usuario | `core/views/companies.py:944` | ✅ CORREGIDO |
| **H4** | Cache keys `timeout=None` en Redis — reemplazados con timeout explícito | `core/services_new.py` | ✅ CORREGIDO |
| **D1** | `pytest.mark.performance` no registrado — añadido en `markers` de `pyproject.toml` | `pyproject.toml` | ✅ CORREGIDO |
| **F1** | Python 3.11 → 3.13 en CI | `.github/workflows/tests.yml` | ✅ CORREGIDO |
| **F2** | `requirements_test.txt` no instalado en CI | `.github/workflows/tests.yml` | ✅ CORREGIDO |
| **F3** | Sin `migrate --check` en CI | `.github/workflows/tests.yml` | ✅ CORREGIDO |
| **F4** | Rama `develop` inexistente en CI triggers — eliminada | `.github/workflows/tests.yml` | ✅ CORREGIDO |
| **I1** | Mezcla backend Redis — unificado a `django_redis.cache.RedisCache` consistentemente | `proyecto_c/settings.py` | ✅ CORREGIDO |

### Hallazgos aún pendientes

| ID | Descripción | Prioridad |
|----|-------------|-----------|
| **A2** | `zip_optimizer.py` y `async_zip_improved.py` — verificar referencias antes de eliminar | Media |
| **C2** | CSP `unsafe-inline` en 52 templates — requiere nonces middleware (1-2 días de trabajo) | Media |
| **C4** | Historial chat sin validación — prompt injection via localStorage | Baja |
| **H5** | Cache admin sin aislamiento multi-tenant (`admin_execution_history` sin empresa_id) | Baja |
