# 📝 CHANGELOG - SAM Metrología

> **Registro Completo de Cambios** - Trazabilidad desde el inicio del proyecto

**Formato:** Basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/)
**Versionado:** Por fecha (YYYY-MM-DD)

---

## 🚨 IMPORTANTE: Cómo Mantener Este Documento

**TODOS LOS DESARROLLADORES** deben actualizar este archivo cuando:
- ✅ Agreguen una nueva funcionalidad
- ✅ Modifiquen una funcionalidad existente
- ✅ Eliminen código obsoleto
- ✅ Corrijan un bug
- ✅ Mejoren rendimiento
- ✅ Actualicen documentación importante

### Formato de Entrada

```markdown
## [YYYY-MM-DD] - Título Descriptivo del Cambio

### Agregado
- Nueva funcionalidad X que hace Y

### Modificado
- Función Z ahora soporta parámetro W
- Mejorado rendimiento de ABC en 30%

### Eliminado
- Código obsoleto de módulo antiguo
- Funcionalidad deprecada XYZ

### Corregido
- Bug #123: Error en validación de formulario
- Hotfix: TypeError en panel de decisiones

### Seguridad
- Vulnerabilidad corregida en endpoint /api/datos
```

---

## [2026-03-23] - Chatbot IA "Señor SAM", Perfil Empresa, Modo Oscuro y UX

### Agregado
- **Chatbot IA "Señor SAM"** (`core/views/chat.py`): asistente de soporte integrado como burbuja flotante en la plataforma. Usa Google Gemini 2.5 Flash. El contexto del sistema (`CONTEXTO_SAM`) documenta roles, módulos, flujos y preguntas frecuentes de la plataforma. Requiere variable de entorno `GEMINI_API_KEY`.
  - Historial de conversación persiste en `localStorage` por usuario (clave `sam_chat_{user_id}`)
  - Se envían los últimos 6 mensajes a Gemini para mantener contexto dentro de la sesión
  - El historial se borra automáticamente al cerrar sesión
  - Avatar personalizado SVG "Señor SAM" en `core/static/core/images/senor_sam.svg`
  - URL: `POST /core/chat/ayuda/` → `core:chat_ayuda`
  - Tests: `tests/test_views/test_chat.py` (8 tests)
- **Vista `editar_perfil_empresa`** (`core/views/companies.py`): permite a Admin/Gerencia completar teléfono, dirección, correos de facturación, correos de notificaciones y logo sin entrar al panel de superusuario. Template: `core/templates/core/editar_perfil_empresa.html`.
- **Validación en pagos**: `iniciar_pago()` bloquea si la empresa no tiene `correos_facturacion` y redirige a completar perfil.
- **Banner "perfil incompleto"** en `base.html`: visible solo para Admin/Gerencia cuando falta `correos_facturacion`.
- **Enlace "Perfil de Empresa"** en sidebar (solo Admin/Gerencia) con indicador ámbar si hay campos faltantes.
- **Formulario trial simplificado**: 3 campos requeridos (nombre, NIT, email) + sección colapsable con campos opcionales.
- **CTA en `trial_exitoso.html`**: bloque ámbar motivando a completar perfil (logo, correos).
- **Paquete `google-genai`** en `requirements.txt` (reemplaza `google-generativeai` que usaba API v1beta sin soporte).

### Modificado
- **Toggle modo oscuro**: movido de burbuja flotante fija a inline junto al username en el navbar. CSS: clase `.theme-toggle-navbar` en `themes.css`.
- **`themes.css`**: reglas dark mode para clases Tailwind amber, orange, blue, green que no tenían override.
- **`chart-theme.js`**: fix timing — `applyChartDefaults()` se llama inmediatamente al cargar, no con `setTimeout`. Resuelve colores incorrectos en gráficas al cargar la página en modo oscuro.
- **`dashboard.html`**: fix títulos de gráficas de torta invisibles en modo oscuro (override de gradiente con colores más claros `#60a5fa → #a78bfa`).
- **`manage.py`**: re-habilitado `python-dotenv` para cargar `.env` en desarrollo.
- **`tests/factories.py`**: `EmpresaFactory` ahora genera `correos_facturacion` por defecto (necesario para tests de pagos que requieren validación).

### Seguridad
- Validación de perfil antes de redirigir a pasarela de pago (Wompi): empresa debe tener NIT y correos de facturación.

---

## [2026-03-16] - Refactoring de Modelos, Permisos y Correcciones

### Modificado
- **`core/models/` (paquete)**: `core/models.py` (4,600 líneas, 28 modelos) dividido en 12 archivos temáticos: `common.py`, `empresa.py`, `users.py`, `catalogs.py`, `equipment.py`, `activities.py`, `loans.py`, `documents.py`, `payments.py`, `system.py`, `_signals.py`, `__init__.py`. Todos los imports existentes siguen funcionando sin cambios (re-exportación en `__init__.py`).
- **`core/views/registro.py` — Permisos TÉCNICO ampliados**: Añadidos `can_view_calibracion`, `can_change_calibracion` (permisos de confirmación metrológica), `add_equipo`, `change_equipo`, `can_view_prestamo`, `can_add_prestamo`, `can_change_prestamo`. El técnico puede ahora crear/editar equipos, abrir y corregir confirmaciones metrológicas y gestionar préstamos.
- **`core/signals.py` — Signal para préstamos**: Añadidos `@receiver(post_save/post_delete)` para `PrestamoEquipo`. Resuelve bug donde el contador "préstamos activos" en el dashboard mostraba 0 tras crear un préstamo.
- **`.github/workflows/tests.yml` — CI/CD bloquea en vulnerabilidades**: Removido `|| true` de los pasos `safety check` y `bandit -r core/ -ll`. El CI ahora falla si hay CVEs en dependencias o vulnerabilidades HIGH/CRITICAL en código.

### Eliminado
- **Código muerto en `Empresa.esta_al_dia_con_pagos()`**: Líneas inalcanzables después del `return dias >= -7` (fragmento de `soft_delete()` mal colocado). Eliminadas sin impacto funcional.
- **`📚-LEER-PRIMERO-DOCS/`**: Eliminados 3 archivos redundantes y desactualizados: `00-START-HERE.md`, `INICIO-AQUI.md`, `CONSOLIDATION.md`. Información consolidada en `README.md` (reescrito).

### Documentación
- **`📚-LEER-PRIMERO-DOCS/README.md`**: Reescrito con estado actual real (1,804 tests, 8.3/10), estructura `core/models/` y comandos corregidos.
- **`📚-LEER-PRIMERO-DOCS/DEVELOPER-GUIDE.md`**: Referencias a `core/models.py` actualizadas a `core/models/`. AWS S3 corregido a Cloudflare R2.
- **`📚-LEER-PRIMERO-DOCS/DESPLEGAR-EN-RENDER.md`**: Sección de almacenamiento corregida (Cloudflare R2).

### Notas operativas
- **Producción**: Tras el deploy, ejecutar `python manage.py setup_permissions` en Render Shell para actualizar permisos de usuarios existentes.
- **Tests**: 1,804 pasando · 0 fallando · Cobertura 70% · Score 8.3/10

---

## [5 Diciembre 2025] - Centralización de Documentación en Carpeta Dedicada

### Agregado
- **📚-LEER-PRIMERO-DOCS/**: Nueva carpeta centralizada para TODA la documentación
- **📚-LEER-PRIMERO-DOCS/00-START-HERE.md**: Punto de entrada prominente para nuevos desarrolladores
- **📚-LEER-PRIMERO-DOCS/README.md**: Índice de la carpeta de documentación
- Sección destacada en README.md raíz apuntando a la carpeta de documentación
- Emoji 📚 en nombre de carpeta para máxima visibilidad

### Modificado
- README.md raíz ahora tiene sección "¿ERES NUEVO? EMPIEZA AQUÍ" prominente
- Sección "Enlaces Importantes" reorganizada con subsecciones (Documentación, Sistema, Estado)
- Todos los archivos de documentación principales copiados a la nueva carpeta centralizada
- Referencias actualizadas para apuntar a la nueva ubicación de documentación

### Beneficios
- ✅ Documentación imposible de ignorar para nuevos desarrolladores
- ✅ Todo en un solo lugar - no más búsqueda de archivos .md dispersos
- ✅ Flujo claro de onboarding: 00-START-HERE.md → INICIO-AQUI.md → DEVELOPER-GUIDE.md
- ✅ Trazabilidad completa con CHANGELOG.md centralizado
- ✅ Índice maestro (CONSOLIDATION.md) accesible desde un solo lugar

---

## [5 Diciembre 2025] - Reorganización Completa de Documentación y Mejoras Estéticas

### Agregado
- **CONSOLIDATION.md**: Master index de toda la documentación del proyecto
- **CHANGELOG.md**: Este archivo - Sistema de trazabilidad completo
- **documentacion/README.md**: Explicación de reorganización de documentación
- **Dashboard**: Diseño moderno y elegante con gradientes y sombras
- **Dashboard**: Gráficas de torta con diseño responsivo mejorado
- **Dashboard**: Tablas de resumen con efectos hover y mejor tipografía
- **Dashboard**: Botones con gradientes y efectos de elevación
- Badges de puntuación y tests en README.md
- Sección "Estado del Proyecto" en README.md con métricas actuales
- Sección "Cambios Recientes" en README.md

### Modificado
- **README.md**: Actualizado con puntuación 7.8/10 y cambios de diciembre
- **INICIO-AQUI.md**: Actualizado con referencias a auditorías de diciembre 2025
- **INICIO-AQUI.md**: Estructura de carpetas actualizada
- **Dashboard**: CSS mejorado con media queries para responsive design
- **Dashboard**: Chart containers con mejor altura y padding
- **Dashboard**: Summary tables con diseño modernizado
- Cobertura de tests actualizada: 254/268 pasando (94.8%)

### Eliminado
- **Documentación duplicada**: 6 archivos eliminados de /documentacion/ (~96 KB)
  - README.md (duplicado)
  - DEVELOPER-GUIDE.md (duplicado)
  - DESPLEGAR-EN-RENDER.md (duplicado)
  - CLAUDE.md (duplicado)
  - CHECKLIST_SISTEMA_PAGOS.md (duplicado)
  - FIX_ZIP_DUPLICADOS.md (duplicado)

### Documentación
- Consolidada toda la documentación en ubicación única
- Creado sistema de trazabilidad con CHANGELOG.md
- Establecidas políticas de mantenimiento de documentación
- Definidas responsabilidades por rol

### Notas
- **Puntuación:** 7.8/10 (+0.6 desde noviembre)
- **Responsable:** Tech Lead
- **Backup:** backups/backup_documentacion_2025-12-05/

---

## [5 Diciembre 2025] - Limpieza Masiva de Código y Optimización

### Eliminado
- **dashboard_gerencia.py**: 1,134 líneas de código obsoleto removidas
- **Código DEBUG**: 15 prints en producción eliminados de múltiples archivos
- **Imports no utilizados**: Limpiados en 8 archivos
- **__pycache__**: 179 directorios limpiados
- Código inalcanzable en Empresa.esta_al_dia_con_pagos
- Imports duplicados en confirmacion.py

### Modificado
- **models.py**: Reorganizado con tabla de contenidos clara (líneas 1-50)
- **models.py**: Secciones bien definidas y navegables
- **confirmacion.py**: Imports movidos a nivel de módulo para mejor rendimiento

### Agregado
- Tabla de contenidos en models.py con 9 secciones principales
- Documentación de estructura en models.py

### Métricas
- **Líneas eliminadas:** 1,149
- **Directorios limpiados:** 179
- **Archivos afectados:** 12+
- **Puntuación:** +0.6 puntos (7.2 → 7.8)

### Notas
- **Responsable:** QA/Tech Lead
- **Auditoría:** auditorias/LIMPIEZA_COMPLETADA_2025-12-05.md
- **Impacto:** Mejora en mantenibilidad y claridad del código

---

## [5 Diciembre 2025] - Estandarización de Permisos y Migraciones

### Agregado
- **Grupo "empresa"**: Creado para estandarizar permisos
- **Permisos estándar**: add, change, delete, view para modelos core
- **Migration 0042**: Agregados campos documento_externo y documento_interno
  - En modelo Comprobacion
  - En modelo Mantenimiento
- **Migration 0043**: Sincronización de JSONFields con base de datos
  - confirmacion_metrologica_datos en Calibracion
  - datos_comprobacion en Comprobacion
  - actividades_realizadas en Mantenimiento

### Modificado
- Sistema de permisos ahora usa grupo "empresa" consistentemente
- Templates actualizados para usar nuevos permisos

### Corregido
- Inconsistencias entre modelo y base de datos en JSONFields
- Permisos faltantes en templates de comprobaciones

### Notas
- **Responsable:** Backend Dev
- **Migración:** 0042, 0043
- **Impacto:** Mejora en seguridad y consistencia

---

## [5 Diciembre 2025] - Sistema de Comprobaciones Metrológicas Completado

### Agregado
- **comprobacion_pdf**: Campo FileField para PDF de comprobación
- **datos_comprobacion**: JSONField para almacenar datos estructurados
- **documento_externo**: Campo para documentos de proveedor
- Validación de documentos externos e internos
- Generación automática de PDF de comprobación
- Gráficas SVG en reportes de comprobación

### Modificado
- **comprobacion.py**: Agregadas validaciones hasattr() para prevenir AttributeError
- Sistema de comprobaciones ahora genera PDFs automáticamente
- Gráficas de comprobación integradas en hoja de vida

### Corregido
- **Bug**: AttributeError al acceder a confirmacion_metrologica_datos (línea 57)
- **Bug**: AttributeError al acceder a datos_comprobacion (línea 301)
- Gráficas no se mostraban en PDF de hoja de vida
- Gráficas no se mostraban en detalle de equipos

### Seguridad
- Validación de tipos de archivo en uploads
- Sanitización de datos JSON

### Notas
- **Responsable:** Backend Dev
- **Archivos modificados:** comprobacion.py, models.py, reports.py
- **Impacto:** Funcionalidad completa de comprobaciones

---

## [19 Noviembre 2025] - Mejoras de UX y Sistema de Presupuestos

### Agregado
- **Sistema de presupuestos financieros**: Gestión de costos de actividades
- **Dashboard con justificaciones**: Explicaciones de incumplimientos
- **Exportación Excel mejorada**: Más datos y mejor formato
- Notificaciones globales que persisten al navegar

### Modificado
- **Dashboard**: Rediseñado para mejor UX
- **Interfaz**: Mejoras visuales en múltiples vistas
- Sistema ZIP optimizado para usar <50% RAM (máx 35 equipos)

### Documentación
- **PLAN_MEJORAS_UX_2025-11-19.md**: Plan completo de mejoras UX
- **INSTRUCCIONES_FINALES_UX_2025-11-19.md**: Guía de implementación
- **PROGRESO_MEJORAS_UX_2025-11-19.md**: Reporte de progreso

### Notas
- **Puntuación:** 7.2/10 (mantenida)
- **Responsable:** Frontend Dev / UX
- **Período:** Semana del 18-22 Nov

---

## [16 Noviembre 2025] - Hotfix Crítico: Panel de Decisiones

### Corregido
- **Bug Crítico**: TypeError en Panel de Decisiones
  - Error: "unsupported operand type(s) for -: 'Decimal' and 'float'"
  - Ubicación: panel_decisiones.py
  - Causa: Mezcla de tipos Decimal y float en cálculos

### Modificado
- Conversiones explícitas Decimal() agregadas
- Validación de tipos mejorada en cálculos financieros

### Seguridad
- Validación de entrada de datos numéricos reforzada

### Notas
- **Responsable:** Backend Dev
- **Auditoría:** auditorias/HOTFIX_APLICADO_2025-11-16.md
- **Bug Report:** auditorias/BUG_PANEL_DECISIONES_2025-11-16.md
- **Prioridad:** 🔴 CRÍTICA
- **Tiempo de resolución:** < 4 horas

---

## [13 Noviembre 2025] - Primera Auditoría Completa del Sistema

### Agregado
- **Sistema de testing robusto**: 158 tests implementados
  - 23 tests de modelos
  - 60 tests de vistas
  - 85 tests de servicios
  - 10 tests de integración
- **Cobertura de tests**: 94% alcanzada
- **Scripts de testing**: run_tests.sh y run_tests.bat

### Documentación
- **AUDITORIA_COMPLETA_2025-11-13.md**: Primera auditoría completa
- **PLAN_IMPLEMENTACION_2025-11-13.md**: Plan de 8-10 semanas
- Secciones detalladas de fortalezas y debilidades
- Roadmap claro de mejoras

### Métricas
- **Puntuación inicial:** 7.2/10
- **Fortalezas identificadas:** Documentación (9/10), Seguridad (8/10)
- **Áreas de mejora:** models.py (3,142 líneas), reports.py (137 KB)

### Notas
- **Responsable:** QA Lead
- **Baseline establecido:** 7.2/10
- **Próximo objetivo:** 8.0/10

---

## [24 Octubre 2024] - Corrección de Vulnerabilidades Críticas de Seguridad

### Seguridad - CRÍTICO
- **Vulnerabilidad #1**: SECRET_KEY expuesto en código
  - Severidad: 🔴 CRÍTICA
  - Movido SECRET_KEY a variables de entorno
  - Rotado SECRET_KEY en producción

- **Vulnerabilidad #2**: SQL Injection en búsquedas
  - Severidad: 🔴 CRÍTICA
  - Reemplazadas queries raw SQL con ORM de Django
  - Sanitización de entrada de usuario agregada

- **Vulnerabilidad #3**: Command Injection en procesamiento de archivos
  - Severidad: 🔴 CRÍTICA
  - Validación estricta de nombres de archivo
  - Sanitización de rutas de archivo

### Agregado
- **file_validators.py**: Validación multicapa de archivos
- **storage_validators.py**: Validación de límites de almacenamiento
- Rate limiting en endpoints críticos
- Validación de tipos MIME

### Modificado
- settings.py ahora carga SECRET_KEY desde entorno
- Todas las queries SQL convertidas a ORM
- Procesamiento de archivos refactorizado

### Métricas
- **Vulnerabilidades corregidas:** 3 críticas
- **Puntuación de seguridad:** 5.0 → 8.5 (+3.5)
- **Puntuación global:** 6.8 → 7.0 (+0.2)

### Notas
- **Responsable:** Security Team
- **Auditoría:** CAMBIOS_CRITICOS_2025-10-24.md
- **Deploy:** Inmediato a producción
- **Prioridad:** 🔴 CRÍTICA

---

## [Antes de Octubre 2024] - Estado Inicial del Proyecto

### Funcionalidades Base Implementadas
- Multi-tenancy con modelo Empresa y CustomUser
- CRUD completo de equipos de metrología
- Sistema de calibraciones
- Sistema de mantenimientos (preventivos y correctivos)
- Generación de certificados PDF
- Dashboard básico con métricas
- Almacenamiento en AWS S3
- Deployment en Render con PostgreSQL

### Características Principales
- Django 5.2.4 + Python 3.13
- PostgreSQL 15 en producción
- SQLite en desarrollo
- Sistema de roles y permisos
- Notificaciones de vencimientos
- Exportación a ZIP de documentos

### Estado Inicial
- **Puntuación estimada:** ~6.0-6.5/10
- Sin tests automatizados
- Documentación básica
- 3 vulnerabilidades críticas sin corregir
- Código con DEBUG prints en producción
- models.py monolítico (3,142 líneas)

---

## 📊 Resumen de Evolución del Proyecto

### Métricas Globales

| Fecha | Puntuación | Δ | Tests | Cobertura | Vulnerabilidades |
|-------|-----------|---|-------|-----------|-----------------|
| Pre-Oct 2024 | ~6.5/10 | - | 0 | 0% | 3 críticas |
| 24 Oct 2024 | 7.0/10 | +0.5 | 0 | 0% | 0 ✅ |
| 13 Nov 2025 | 7.2/10 | +0.2 | 158 | 94% | 0 ✅ |
| 16 Nov 2025 | 7.2/10 | 0 | 158 | 94% | 0 ✅ |
| 19 Nov 2025 | 7.2/10 | 0 | 158 | 94% | 0 ✅ |
| 5 Dic 2025 | 7.8/10 | +0.6 | 268 | 94.8% | 0 ✅ |
| 15 Mar 2026 | 8.3/10 | +0.5 | 1,804 | 70% | 0 ✅ |
| **16 Mar 2026** | **8.3/10** | 0 | **1,804** | **70%** | **0** ✅ |

**Mejora Total:** +1.8 puntos (desde ~6.5 hasta 8.3)
**Próximo Objetivo:** 9.0/10

### Líneas de Código

| Métrica | Inicial | Actual | Cambio |
|---------|---------|--------|--------|
| **Código Total** | ~15,000 | ~14,000 | -1,000 (limpieza) |
| **models.py** | 3,142 | 3,142 | 0 (reorganizado) |
| **reports.py** | ~3,000 | 3,154 | +154 |
| **Tests** | 0 | 268 | +268 |
| **Documentación** | ~5 archivos | 20+ archivos | +15 |

### Funcionalidades

| Funcionalidad | Estado Inicial | Estado Actual |
|--------------|---------------|---------------|
| Multi-tenancy | ✅ Básico | ✅ Completo |
| Calibraciones | ✅ Funcional | ✅ Con confirmación metrológica |
| Mantenimientos | ✅ Funcional | ✅ Con documentos externos/internos |
| **Comprobaciones** | ❌ No existía | ✅ **Completamente funcional** |
| Presupuestos | ❌ No existía | ✅ **Sistema completo** |
| Dashboard | ✅ Básico | ✅ **Modernizado y elegante** |
| Tests | ❌ Sin tests | ✅ **268 tests, 94.8% pasando** |
| Documentación | ⚠️ Básica | ✅ **Excepcional (9/10)** |
| Seguridad | ⚠️ 3 vulnerabilidades | ✅ **8.5/10** |

---

## 🎯 Próximos Cambios Planificados

Ver roadmap completo en: [auditorias/PROGRESO_Y_ROADMAP_8.5_2025-12-05.md](./auditorias/PROGRESO_Y_ROADMAP_8.5_2025-12-05.md)

### Quick Wins Identificados

1. **Dividir reports.py** (3,154 líneas)
   - Separar en módulos: calibracion_reports.py, mantenimiento_reports.py, comprobacion_reports.py
   - Estimado: +0.2 puntos

2. **Optimizar queries N+1 en dashboard**
   - Agregar select_related() y prefetch_related()
   - Estimado: Mejora de 40% en rendimiento

3. **Eliminar código DEBUG restante**
   - 5 prints identificados
   - Estimado: +0.1 puntos

4. **Migrar campo deprecado es_periodo_prueba**
   - Crear migración
   - Estimado: +0.1 puntos

**Total estimado:** +0.4 puntos → **8.2/10**

---

## 📝 Notas Importantes

### Convenciones de Este Documento

- **[Fecha]** - Formato: YYYY-MM-DD (descendente, más reciente primero)
- **Secciones**: Agregado, Modificado, Eliminado, Corregido, Seguridad, Documentación
- **Prioridad**: 🔴 Crítica, 🟡 Alta, 🟢 Normal
- **Estado**: ✅ Completado, ⚠️ Advertencia, ❌ Pendiente

### Responsables

- **Tech Lead**: Coordinación general, documentación
- **Backend Dev**: Desarrollo de funcionalidades
- **Frontend Dev**: UI/UX
- **DevOps**: Deployment, infraestructura
- **QA Lead**: Testing, auditorías
- **Security Team**: Seguridad

### Proceso de Actualización

1. **Antes de commit**: Actualizar este archivo
2. **En el commit message**: Referenciar entrada de CHANGELOG
3. **En el PR**: Incluir resumen de cambios
4. **Después de merge**: Verificar que CHANGELOG esté actualizado

---

**Última Actualización:** 5 de Diciembre de 2025
**Mantenido por:** Todo el Equipo SAM Metrología
**Próxima Revisión:** Cada cambio de código

---

> ⚠️ **RECORDATORIO:** Este documento es la **fuente de verdad** para la trazabilidad del proyecto. Mantenerlo actualizado es responsabilidad de **TODOS** los desarrolladores.
