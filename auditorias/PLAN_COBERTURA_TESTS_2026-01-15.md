# PLAN DE COBERTURA DE TESTS - MÓDULOS CRÍTICOS
**Fecha:** 15 de Enero de 2026
**Cobertura Actual:** 54.30%
**Objetivo:** 65%+ (incremento de ~11%)

---

## 📊 ESTADO ACTUAL (Post-Fix de Tests)

**Tests:**
- ✅ 778 tests pasando (100%)
- ❌ 0 tests fallando
- ⏭️ 1 test skipped

**Cobertura:**
- Total statements: 12,457
- Covered: 6,764
- Missing: 5,693
- **Coverage: 54.30%**

---

## 🎯 FILOSOFÍA DE TESTING

**NO hacer tests por hacer:**
- ❌ NO testear líneas de código solo para subir el número
- ❌ NO crear tests triviales sin valor
- ❌ NO testear getters/setters simples
- ❌ NO testear código autogenerado (migrations, admin auto-registrations)

**SÍ hacer tests funcionales y críticos:**
- ✅ Testear flujos de negocio críticos
- ✅ Testear edge cases y errores
- ✅ Testear integraciones entre módulos
- ✅ Testear validaciones de seguridad
- ✅ Testear cálculos financieros/métricos

---

## 🔴 PRIORIDAD CRÍTICA (Impacto Alto + Cobertura Baja)

### 1. confirmacion.py - 22.28% (543 statements)
**Impacto:** CRÍTICO - Confirmación metrológica, cálculos, PDFs
**Missing:** 422 statements

**Tests a crear:**
```
✓ Flujo completo de confirmación metrológica
✓ Validación de puntos de calibración
✓ Cálculos de incertidumbre y errores
✓ Generación de PDFs con datos correctos
✓ Manejo de formatos JSON de datos metrológicos
✓ Validaciones de rangos y unidades
✓ Edge cases: datos faltantes, valores extremos
```

**Valor agregado:**
- Garantiza precisión metrológica (ISO 17020)
- Previene errores en certificados
- Valida cálculos críticos

**Esfuerzo estimado:** ALTO (módulo complejo)
**Tests estimados:** 25-30 tests
**Cobertura objetivo:** 60%+

---

### 2. notifications.py - 43.28% (268 statements)
**Impacto:** ALTO - Sistema de notificaciones y alertas
**Missing:** 152 statements

**Tests a crear:**
```
✓ Envío de notificaciones de calibración vencida
✓ Recordatorios de mantenimiento programado
✓ Resumen semanal de actividades
✓ Notificaciones ZIP completado/fallido
✓ Configuración de email settings
✓ Manejo de errores de SMTP
✓ Rate limiting de notificaciones
✓ Templates de email correctos
```

**Valor agregado:**
- Previene pérdida de notificaciones críticas
- Valida configuración de email
- Garantiza cumplimiento de alertas

**Esfuerzo estimado:** MEDIO
**Tests estimados:** 15-20 tests
**Cobertura objetivo:** 70%+

---

### 3. comprobacion.py - 41.54% (195 statements)
**Impacto:** MEDIO-ALTO - Comprobaciones intermedias
**Missing:** 114 statements

**Tests a crear:**
```
✓ Vista de comprobación con equipo existente
✓ Guardado de datos JSON de comprobación
✓ Generación de PDF de comprobación
✓ Validación de datos numéricos
✓ Multitenancy en comprobaciones
✓ Manejo de errores en cálculos
```

**Valor agregado:**
- Complementa sistema de confirmación
- Valida trazabilidad de comprobaciones

**Esfuerzo estimado:** MEDIO
**Tests estimados:** 10-15 tests
**Cobertura objetivo:** 65%+

---

## 🟡 PRIORIDAD MEDIA (Funcionalidad Importante)

### 4. companies.py - 46.64% (298 statements)
**Impacto:** MEDIO - Gestión de empresas multi-tenant
**Missing:** 159 statements

**Tests a crear:**
```
✓ CRUD completo de empresas
✓ Validaciones de límites de equipos
✓ Soft delete y restauración
✓ Gestión de usuarios por empresa
✓ Planes y suscripciones
✓ Multitenancy estricto
✓ Configuración de formatos
✓ Upload de logos
```

**Valor agregado:**
- Core del sistema multi-tenant
- Previene fugas de datos entre empresas

**Esfuerzo estimado:** MEDIO
**Tests estimados:** 15-20 tests
**Cobertura objetivo:** 70%+

---

### 5. decision_intelligence.py - 50.51% (196 statements)
**Impacto:** MEDIO - Análisis y recomendaciones
**Missing:** 97 statements

**Tests a crear:**
```
✓ Cálculo de métricas de decisión
✓ Recomendaciones basadas en datos
✓ Análisis de tendencias
✓ Proyecciones de actividades
✓ Edge cases con datos incompletos
```

**Valor agregado:**
- Valida lógica de negocio de recomendaciones
- Garantiza precisión de análisis

**Esfuerzo estimado:** MEDIO
**Tests estimados:** 10-12 tests
**Cobertura objetivo:** 70%+

---

### 6. optimizations.py - 44.95% (109 statements)
**Impacto:** MEDIO - Performance y cache
**Missing:** 60 statements

**Tests a crear:**
```
✓ Optimizaciones de queries
✓ Cache de datos frecuentes
✓ Invalidación de cache
✓ Batch operations
```

**Valor agregado:**
- Garantiza performance
- Valida estrategias de cache

**Esfuerzo estimado:** BAJO
**Tests estimados:** 8-10 tests
**Cobertura objetivo:** 65%+

---

## 🟢 PRIORIDAD BAJA (Funcional pero menos crítico)

### 7. admin_views.py - 11.85% (557 statements)
**Decisión:** POSPONER
**Razón:**
- Vistas de administración Django
- Baja criticidad para usuarios finales
- Alto esfuerzo, bajo valor
- Django admin ya está testeado por framework

---

### 8. admin_services.py - 16.43% (280 statements)
**Decisión:** POSPONER
**Razón:**
- Servicios de administración
- Solo para superusuarios
- Funcionalidad secundaria

---

### 9. scheduled_tasks_api.py - 27.93% (111 statements)
**Decisión:** TESTEAR SELECTIVAMENTE
**Tests críticos:**
```
✓ Autenticación de endpoints API
✓ Validación de tokens
✓ Ejecución de tareas programadas críticas
```

**Valor agregado:**
- Solo testear seguridad y tasks críticos
- No testear tasks triviales

**Esfuerzo estimado:** BAJO
**Tests estimados:** 5-8 tests
**Cobertura objetivo:** 50%+

---

## 📋 PLAN DE EJECUCIÓN PROPUESTO

### FASE 1: Módulos Críticos (Días 7-10)
**Objetivo:** +8% cobertura (54.3% → 62%+)

1. **Día 7:** confirmacion.py (25-30 tests) - Target: 60%
2. **Día 8:** notifications.py (15-20 tests) - Target: 70%
3. **Día 9:** comprobacion.py (10-15 tests) - Target: 65%
4. **Día 10:** Revisión y ajustes

**Resultado esperado:** 62-63% cobertura total

---

### FASE 2: Módulos Importantes (Días 11-13)
**Objetivo:** +3% cobertura (62% → 65%+)

5. **Día 11:** companies.py (15-20 tests) - Target: 70%
6. **Día 12:** decision_intelligence.py (10-12 tests) - Target: 70%
7. **Día 13:** optimizations.py (8-10 tests) - Target: 65%

**Resultado esperado:** 65-66% cobertura total

---

### FASE 3: Selectivo (Día 14)
**Objetivo:** +1% cobertura (65% → 66%+)

8. **Día 14:** scheduled_tasks_api.py (5-8 tests críticos) - Target: 50%

**Resultado esperado:** 66%+ cobertura total

---

## 🎯 MÉTRICAS DE ÉXITO

**Cuantitativas:**
- Cobertura total: 54.30% → 66%+ (+11.7%)
- Tests nuevos: ~100-120 tests
- 0 tests fallando (mantener)

**Cualitativas:**
- ✅ Tests funcionales, no triviales
- ✅ Cubren edge cases críticos
- ✅ Validan seguridad y multitenancy
- ✅ Garantizan cálculos precisos
- ✅ Previenen regresiones

---

## ⚠️ PRINCIPIOS A SEGUIR

### DO's ✅
1. **Testear flujos de negocio completos**
   - Ejemplo: Crear equipo → Calibrar → Generar PDF
2. **Testear edge cases**
   - Datos faltantes, valores extremos, formatos incorrectos
3. **Testear seguridad**
   - Multitenancy, permisos, validaciones
4. **Testear cálculos**
   - Fórmulas, conversiones, agregaciones
5. **Usar mocks solo para I/O externo**
   - Storage, email, cache, APIs externas

### DON'Ts ❌
1. **NO testear por cobertura**
   - No crear tests solo para subir el %
2. **NO testear getters triviales**
   - `def get_name(): return self.name` → NO TESTEAR
3. **NO duplicar tests**
   - Si hay test de integración, no repetir en unitario
4. **NO testear Django framework**
   - ORM, forms validation básica, admin → Ya está testeado
5. **NO testear código legacy/obsoleto**
   - Si está marcado para eliminar, no testear

---

## 📊 ESTIMACIONES

**Total tests a crear:** 100-120 tests
**Tiempo estimado:** 8-10 días de trabajo
**Cobertura final esperada:** 66-68%
**ROI:** ALTO - Módulos críticos con impacto directo

---

## 🚀 PRÓXIMO PASO

**Iniciar Fase 1 - Día 7:**
Crear tests para `confirmacion.py`
- Enfoque en validaciones metrológicas
- Cálculos de incertidumbre
- Generación de PDFs
- Edge cases críticos

**¿Proceder con Fase 1?**
