# PLAN DE AUDITORÍA INTEGRAL — SAM v2.x
**Fecha de elaboración:** 24 de Abril de 2026
**Basado en:** AUDITORIA_INTEGRAL_2026-03-15.md (Score: 8.3/10)
**Meta:** Alcanzar 9.0/10 en próxima auditoría

---

## CONTEXTO — ¿DÓNDE ESTAMOS?

La última auditoría (Mar-15-2026) dejó el sistema en **8.3/10** con los siguientes hallazgos pendientes:

| Hallazgo | Prioridad | Estado actual |
|----------|-----------|---------------|
| confirmacion.py sin `@access_check` | ALTA | Pendiente |
| `unsafe-inline` en CSP script-src/style-src | MEDIA | Pendiente |
| SSE en R2 no configurada explícitamente | MEDIA | Parcialmente resuelto (comentario corregido) |
| README.md vacío (19 bytes) | ALTA | Pendiente |
| CONTRIBUTING.md inexistente | BAJA | Pendiente |
| Safety/Bandit con `continue-on-error: true` | BAJA | Pendiente |
| `esta_al_dia_con_pagos()` código muerto | MEDIA | Pendiente |
| Cobertura confirmacion.py < 60% | ALTA | **RESUELTO** (58.77% → sobre umbral) |
| Bug `eliminar_equipo.html` template | CRITICA | **RESUELTO** |
| `core/models.py` monolítico 4,592 líneas | ALTA | **RESUELTO** (paquete `core/models/`) |

---

## AVANCES DESDE MAR-15-2026

| Cambio | Impacto en score |
|--------|-----------------|
| **models.py → paquete `core/models/`** (12 módulos) | +0.15 arquitectura |
| **Multi-magnitud v2** (Apr-09) — confirmaciones y comprobaciones con múltiples variables | +0.05 lógica |
| **Préstamos UX** (Apr-24) — secciones colapsables, filtro, chips | Calidad UX |
| **Coverage confirmacion.py 58.77%** — supera umbral 50% | +0.075 tests |

**Score estimado actual (sin auditar):** ~8.5–8.6/10

---

## ALCANCE DE LA PRÓXIMA AUDITORÍA

### Dimensión 1: SEGURIDAD (peso 25%)
**Objetivo: 8.5 → 9.0** (+0.125 en score final)

Tareas:
- [ ] **A1.** Agregar `@access_check` a todas las vistas de `confirmacion.py`
  - Archivo: `core/views/confirmacion.py`
  - Patrón: igual que `activities.py` línea 25-28
  - Esfuerzo: 2 horas
- [ ] **A2.** Eliminar `unsafe-inline` de CSP en `settings.py`
  - Reemplazar con nonces via `django-csp` (`CSP_INCLUDE_NONCE_IN=['script-src']`)
  - Agregar atributo `nonce="{{ request.csp_nonce }}"` en los 52 bloques `<script>` inline
  - Esfuerzo: 1-2 días
  - **Bloqueo conocido:** 52 bloques inline en 51 templates — requiere recorrer todos
- [ ] **A3.** Configurar SSE explícitamente en R2
  - `settings.py`: agregar `AWS_S3_OBJECT_PARAMETERS = {'ServerSideEncryption': 'AES256'}`
  - Esfuerzo: 15 minutos

### Dimensión 2: MULTI-TENANCY (peso 15%)
**Objetivo: 8.5 → 9.0** (+0.075 en score final)

Tareas:
- [ ] **B1.** Verificar que `confirmacion.py` bloquea correctamente acceso cross-empresa tras agregar `@access_check`
- [ ] **B2.** Test funcional HTTP: intentar acceder a confirmaciones de otra empresa → debe retornar 403/404

### Dimensión 3: LÓGICA DE NEGOCIO (peso 15%)
**Objetivo: 8.0 → 9.0** (+0.15 en score final)

Tareas:
- [ ] **C1.** Eliminar código muerto `esta_al_dia_con_pagos()` en `core/models/payments.py` (o el módulo donde quedó)
  - Verificar primero que no es llamada desde ningún lugar (grep)
  - Esfuerzo: 15 minutos
- [ ] **C2.** Auditar lógica multi-magnitud v2
  - Verificar integridad de datos v1 vs v2 en migración implícita
  - Verificar que PDF genera correctamente con múltiples variables
  - Verificar gráficas históricas normalizadas por EMP
- [ ] **C3.** Verificar módulos del paquete `core/models/` — que ningún import se rompió
  - Correr `python manage.py check` → debe dar 0 issues

### Dimensión 4: TESTS Y COVERAGE (peso 15%)
**Objetivo: 9.0 → 9.5** (+0.075 en score final)

Tareas:
- [ ] **D1.** Correr suite completa y verificar que ≥1,847 tests pasan, 0 fallando
- [ ] **D2.** Verificar coverage ≥ 70% (meta sostenida)
- [ ] **D3.** Revisar y corregir los 6 tests en `test_mejoras_ux.py` que usan `return` en lugar de `assert`
  - Bug conocido desde Mar-12 sin resolver
  - Esfuerzo: 30 minutos
- [ ] **D4.** Registrar `pytest.mark.performance` en `pyproject.toml`
  - Evita warnings de markers no registrados
  - Esfuerzo: 5 minutos

### Dimensión 5: ARQUITECTURA (peso 10%)
**Objetivo: 7.0 → 8.5** (+0.15 en score final)
*(El split de models.py ya suma aquí)*

Tareas:
- [ ] **E1.** Crear `README.md` funcional en la raíz
  - Contenido mínimo: resumen del sistema, setup en 5 pasos, link a `📚-LEER-PRIMERO-DOCS/`
  - Esfuerzo: 1 hora
- [ ] **E2.** Crear `CONTRIBUTING.md`
  - Flujo de trabajo, convenciones, cómo correr tests, cómo hacer deploy
  - Esfuerzo: 2 horas
- [ ] **E3.** Evaluar y limpiar archivos posiblemente obsoletos:
  - `core/views_optimized.py` (292 líneas)
  - `core/zip_optimizer.py` (473 líneas)
  - `core/async_zip_improved.py` (579 líneas, deshabilitado)
  - Verificar con grep si son importados activamente. Si no → eliminar.

### Dimensión 6: CI/CD (peso 10%)
**Objetivo: 8.5 → 9.0** (+0.05 en score final)

Tareas:
- [ ] **F1.** Cambiar `continue-on-error: true` a `false` en Safety y Bandit en `tests.yml`
  - O al menos emitir un GitHub Issue automático si detectan algo crítico
  - Esfuerzo: 30 minutos

### Dimensión 7: LEY 1581 + DOCS (peso 10%)
**Objetivo: 7.5 → 8.0** (+0.05 en score final)

Tareas:
- [ ] **G1.** Configurar SSE en R2 (ver A3 arriba — coincide con Ley 1581 encriptación en reposo)
- [ ] **G2.** Evaluar `django-auditlog` para PII audit trail (quién accede a datos de usuarios)

---

## NUEVAS ÁREAS A EXPLORAR (no estaban en auditoría anterior)

| Área | Riesgo | Descripción |
|------|--------|-------------|
| Multi-magnitud data integrity | MEDIO | ¿Los datos v1 se leen correctamente como v2? ¿El PDF no falla si no hay `emp`? |
| Paquete `core/models/` imports | BAJO | Verificar que `__init__.py` re-exporta todo y no hay ImportError oculto |
| Préstamos UX — tests | BAJO | El nuevo dashboard.html necesita tests de template rendering |
| Chatbot Señor SAM — límites | BAJO | ¿Hay rate limiting en el endpoint de Gemini? ¿Qué pasa si `GEMINI_API_KEY` no está? |

---

## PROYECCIÓN DE SCORE

Si se completan las tareas A1, A2, A3, B1, C1, D1-D4, E1, E2, F1, G1:

| Dimensión | Actual (est.) | Proyectado | Δ ponderado |
|-----------|--------------|-----------|-------------|
| Seguridad (25%) | 8.5 | 9.0 | +0.125 |
| Multi-tenancy (15%) | 8.5 | 9.0 | +0.075 |
| Lógica (15%) | 8.5 | 9.0 | +0.075 |
| Tests (15%) | 9.0 | 9.5 | +0.075 |
| Arquitectura (10%) | 8.0 | 8.5 | +0.050 |
| CI/CD (10%) | 8.5 | 9.0 | +0.050 |
| Ley 1581 + Docs (10%) | 7.5 | 8.0 | +0.050 |
| **TOTAL** | **~8.55** | **~9.0** | **+0.5** |

**Con tarea A2 (CSP nonces) completa → 9.0/10 alcanzable.**
**Sin A2 → ~8.8/10.**

---

## ORDEN DE EJECUCIÓN RECOMENDADO

| Orden | Tarea | Esfuerzo | Impacto |
|-------|-------|---------|---------|
| 1 | **A3** — SSE en R2 (settings.py, 1 línea) | 15 min | Seguridad + Ley 1581 |
| 2 | **D3** — Corregir tests con `return` | 30 min | Tests |
| 3 | **D4** — Registrar pytest.mark.performance | 5 min | Tests |
| 4 | **C1** — Eliminar código muerto `esta_al_dia_con_pagos` | 15 min | Lógica |
| 5 | **F1** — Safety/Bandit no continue-on-error | 30 min | CI/CD |
| 6 | **A1** — `@access_check` en confirmacion.py | 2 h | Seguridad |
| 7 | **E1** — README.md funcional | 1 h | Arquitectura |
| 8 | **E2** — CONTRIBUTING.md | 2 h | Arquitectura |
| 9 | **E3** — Limpiar archivos obsoletos | 1 h | Arquitectura |
| 10 | **A2** — Eliminar unsafe-inline CSP | 1-2 días | Seguridad (+0.125) |

---

---

## DIMENSIÓN 8: DOCUMENTACIÓN Y CONTENIDO DESACTUALIZADO (nuevo)
**Objetivo:** Garantizar que lo que dice el sistema coincide con lo que hace

Este es el área más ignorada en auditorías técnicas y la que más confunde a usuarios y desarrolladores nuevos.

### Qué revisar

| Ítem | Cómo verificar |
|------|----------------|
| Instrucciones en templates (tooltips, placeholders, textos de ayuda) | Abrir cada módulo en el navegador y comparar con el código real |
| Instrucciones de importación Excel (`/core/equipos/importar_excel/`) | ¿Los pasos del template coinciden con la vista actual? ¿Las columnas del template Excel siguen siendo las mismas? |
| Textos en mensajes flash (messages.py) | ¿Son precisos? ¿Mencionan campos o URLs que ya no existen? |
| Comentarios en el código | ¿Hay comentarios `# TODO` o `# FIXME` que llevan meses sin resolverse? |
| CLAUDE.md y docs/ | ¿Las rutas, comandos y versiones mencionadas aún son correctas? |
| Emails de notificación | ¿El texto de los emails menciona funcionalidades que cambiaron? |
| Términos y condiciones | ¿La versión en BD coincide con el archivo `terminos_condiciones_v1.0.html`? |

### Checklist de revisión por módulo

- [ ] **H1.** `/core/equipos/importar_excel/` — verificar que las instrucciones coinciden con las columnas del Excel generado
- [ ] **H2.** `/core/equipos/` — verificar que los tooltips de filtros aún son válidos
- [ ] **H3.** `/core/confirmaciones/` — verificar textos de ayuda del formulario multi-magnitud
- [ ] **H4.** `docs/PLAN_TRIAL_ONBOARDING_PAGOS.md` — ¿el flujo descrito coincide con el código actual?
- [ ] **H5.** `scripts/` — ¿los scripts de diagnóstico aún corren sin errores?
- [ ] **H6.** `management/commands/` — verificar que todos los comandos de gestión documentados siguen funcionando
- [ ] **H7.** Emails de notificación — leer las plantillas de email y verificar que los datos enviados existen en el modelo

---

## DIMENSIÓN 9: TEMPLATES HUÉRFANOS Y URLs ROTAS (nuevo)
**Objetivo:** Detectar código muerto que no lanza error pero tampoco sirve para nada

### Qué revisar

- [ ] **I1.** Listar todos los templates en `core/templates/` y verificar que cada uno es usado en al menos una vista
  ```bash
  # Buscar templates no referenciados en vistas ni otros templates
  find core/templates -name "*.html" | while read f; do
    base=$(basename $f);
    grep -r "$base" core/views/ core/templates/ --include="*.py" --include="*.html" -l 2>/dev/null | grep -v "$f"
  done
  ```
- [ ] **I2.** Verificar que todas las URLs en `core/urls.py` apuntan a vistas que existen y están importadas
- [ ] **I3.** Verificar que todos los `{% url 'core:xxx' %}` en templates resuelven correctamente (correr `python manage.py check` con `--deploy`)
- [ ] **I4.** Revisar los 3 archivos marcados como posiblemente obsoletos: `views_optimized.py`, `zip_optimizer.py`, `async_zip_improved.py` — ¿son importados activamente?
- [ ] **I5.** Revisar si hay vistas en `views/` que no tienen URL asignada en `urls.py`

---

## DIMENSIÓN 10: PERFORMANCE (nuevo)
**Objetivo:** Detectar páginas lentas antes de que un cliente lo reporte

### Qué revisar

- [ ] **J1.** Instalar `django-debug-toolbar` en dev y abrir las páginas de mayor tráfico:
  - Dashboard principal
  - Listado de equipos (home)
  - Panel de Decisiones
  - Reportes / Hoja de Vida PDF
- [ ] **J2.** Verificar queries N+1 en dashboard:
  - `dashboard.py` — ¿usa `select_related` y `prefetch_related`?
  - `prestamos/dashboard.html` — la vista agrupa en Python, no en SQL
- [ ] **J3.** Verificar índices en modelos de alta consulta:
  ```python
  # Verificar que estos campos tienen db_index=True o están en Meta.indexes:
  Equipo: empresa, estado, proxima_calibracion
  Calibracion: equipo, empresa, fecha_calibracion
  PrestamoEquipo: empresa, estado_prestamo, nombre_prestatario
  ```
- [ ] **J4.** Medir tiempo de generación de PDF Hoja de Vida con 10+ variables en multi-magnitud
- [ ] **J5.** Verificar que el cache del dashboard funciona: hacer 2 GETs seguidos y confirmar que el segundo no hace queries a la BD

---

## DIMENSIÓN 11: MIGRACIONES Y BASE DE DATOS (nuevo)
**Objetivo:** Garantizar que el esquema de BD es correcto y que las migraciones no tienen conflictos

### Qué revisar

- [ ] **K1.** Correr `python manage.py migrate --check` — debe retornar 0 (sin migraciones pendientes)
- [ ] **K2.** Correr `python manage.py showmigrations` — verificar que todas están marcadas como `[X]`
- [ ] **K3.** Verificar que no hay migraciones en conflicto (dos migraciones con el mismo número en la misma app)
- [ ] **K4.** Correr las migraciones desde cero en una BD limpia:
  ```bash
  python manage.py migrate --run-syncdb  # en SQLite vacío
  ```
- [ ] **K5.** Verificar que `python manage.py check --database default` pasa sin issues
- [ ] **K6.** Verificar que el paquete `core/models/` no rompió ninguna migración histórica — todas deben seguir resolviendo correctamente

---

## DIMENSIÓN 12: INTEGRACIONES EXTERNAS (nuevo)
**Objetivo:** Verificar que los servicios externos siguen funcionando

| Servicio | Verificación |
|----------|-------------|
| **Cloudflare R2** | Subir un archivo desde la plataforma y verificar que queda accesible. Revisar URL firmada. |
| **Wompi (pagos)** | Ejecutar un pago de prueba en sandbox. Verificar que el webhook firma correctamente. |
| **Gemini (Señor SAM)** | Enviar una pregunta al chatbot y verificar respuesta. Verificar comportamiento si `GEMINI_API_KEY` no está. |
| **GitHub Actions** | Verificar que los 13 workflows corrieron exitosamente en el último mes. |
| **Emails (SMTP)** | Enviar un email de prueba desde `python manage.py shell` con `send_mail()`. |
| **Redis (cache)** | En producción: verificar que el cache Redis está activo con `redis-cli ping`. |

- [ ] **L1.** R2: verificar upload y URL firmada
- [ ] **L2.** Wompi: test de webhook con firma SHA-256
- [ ] **L3.** Gemini: test del chatbot y fallback si API key falta
- [ ] **L4.** GitHub Actions: revisar historial de runs de los 13 workflows
- [ ] **L5.** Email: test de notificación manual

---

## MÓDULOS ISO/IEC 17020:2012 PENDIENTES (largo plazo)

Funcionalidades que exige la norma pero SAM aún no implementa:

| Módulo | Cláusula ISO 17020 | Prioridad |
|--------|-------------------|-----------|
| Quejas de clientes | 7.9 | ALTA |
| No conformidades + acciones correctivas | 8.7 | ALTA |
| Declaración de imparcialidad | 4.1 | MEDIA |
| Riesgos y oportunidades | 8.5 | MEDIA |
| Control de documentos externos | 8.3 | BAJA |

Implementar estos módulos llevaría el sistema a **plena conformidad ISO 17020** y podría elevar el score a 9.5/10.

---

*Plan elaborado por: Claude Sonnet 4.6 — 24 de Abril de 2026*
*Siguiente auditoría sugerida: Mayo 2026 o al completar ≥6 de las 10 tareas prioritarias*
