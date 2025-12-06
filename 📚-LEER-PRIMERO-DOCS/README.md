# 📚 Documentación Central - SAM Metrología

> **Esta carpeta contiene TODA la documentación que necesitas para trabajar en el proyecto.**

---

## 🎯 Punto de Partida

### **[📖 00-START-HERE.md](./00-START-HERE.md)** ⭐ **EMPIEZA AQUÍ**

Si es tu primera vez en el proyecto, abre ese archivo primero. Te guiará paso a paso.

---

## 📂 Contenido de Esta Carpeta

### Documentación Principal

| Archivo | Descripción | ¿Cuándo leerlo? |
|---------|-------------|-----------------|
| **[00-START-HERE.md](./00-START-HERE.md)** | Punto de partida para TODOS los desarrolladores | **PRIMERO** - Siempre |
| **[INICIO-AQUI.md](./INICIO-AQUI.md)** | Guía de inicio rápido con checklist | Después de START-HERE |
| **[DEVELOPER-GUIDE.md](./DEVELOPER-GUIDE.md)** | Guía técnica completa del sistema | **OBLIGATORIO** antes de tocar código |
| **[CONSOLIDATION.md](./CONSOLIDATION.md)** | Índice maestro de toda la documentación | Cuando busques algo específico |
| **[CHANGELOG.md](./CHANGELOG.md)** | Historial completo de cambios | **Antes y después de CADA cambio** |
| **[DESPLEGAR-EN-RENDER.md](./DESPLEGAR-EN-RENDER.md)** | Guía de deployment en producción | Cuando vayas a hacer deploy |
| **[CLAUDE.md](./CLAUDE.md)** | Instrucciones para Claude Code | Si usas Claude Code como asistente |

---

## 🚀 Orden de Lectura Recomendado

### Para Nuevos Desarrolladores (Día 1-2)

1. ✅ **[00-START-HERE.md](./00-START-HERE.md)** (10 min)
2. ✅ **[INICIO-AQUI.md](./INICIO-AQUI.md)** (10 min)
3. ✅ **[DEVELOPER-GUIDE.md](./DEVELOPER-GUIDE.md)** (40 min) ⭐ **CRÍTICO**
4. ✅ **[CONSOLIDATION.md](./CONSOLIDATION.md)** (10 min)
5. ✅ **[CHANGELOG.md](./CHANGELOG.md)** (5 min)

**Total:** ~75 minutos de lectura

### Para Hacer un Cambio

1. ✅ Leer [DEVELOPER-GUIDE.md](./DEVELOPER-GUIDE.md) → Sección "Áreas Críticas"
2. ✅ Consultar [CHANGELOG.md](./CHANGELOG.md) → Ver cambios recientes relacionados
3. ✅ Hacer tu cambio
4. ✅ **Actualizar [CHANGELOG.md](./CHANGELOG.md)** con tu cambio ← **OBLIGATORIO**
5. ✅ Ejecutar tests: `pytest`
6. ✅ Commit y push

### Para Hacer Deploy

1. ✅ Leer [DESPLEGAR-EN-RENDER.md](./DESPLEGAR-EN-RENDER.md)
2. ✅ Verificar checklist pre-deploy
3. ✅ Ejecutar tests
4. ✅ Push a `main` (auto-deploy activo)

---

## 📊 Documentación Adicional

### Auditorías y Reportes de Progreso

**Ubicación:** `../auditorias/`

- **[PROGRESO_Y_ROADMAP_8.5_2025-12-05.md](../auditorias/PROGRESO_Y_ROADMAP_8.5_2025-12-05.md)** - Estado actual y roadmap
- **[AUDITORIA_COMPLETA_2025-12-05.md](../auditorias/AUDITORIA_COMPLETA_2025-12-05.md)** - Última auditoría completa
- **[LIMPIEZA_COMPLETADA_2025-12-05.md](../auditorias/LIMPIEZA_COMPLETADA_2025-12-05.md)** - Optimizaciones realizadas

Ver índice completo en [CONSOLIDATION.md](./CONSOLIDATION.md)

---

## ⚠️ Reglas Importantes

### 1. Actualiza el CHANGELOG

**SIEMPRE actualiza [CHANGELOG.md](./CHANGELOG.md) cuando:**
- ✅ Agregues una nueva funcionalidad
- ✅ Modifiques una funcionalidad existente
- ✅ Elimines código obsoleto
- ✅ Corrijas un bug
- ✅ Hagas cambios de seguridad

**Sin excepciones.** Es tu responsabilidad mantener la trazabilidad.

### 2. Lee Antes de Tocar

**NO toques código sin leer:**
- [DEVELOPER-GUIDE.md](./DEVELOPER-GUIDE.md) - Especialmente la sección "Áreas Críticas"

### 3. Tests Antes de Commit

**SIEMPRE ejecuta:**
```bash
pytest
```

254/268 tests deben pasar (94.8%). Si rompes tests, arréglalo antes de commit.

### 4. Auto-Deploy Activo

**CUIDADO:** Cada push a `main` se despliega automáticamente a producción.

---

## 🔍 ¿Qué Archivo Necesito?

| Necesito... | Ver... |
|-------------|--------|
| Empezar en el proyecto | [00-START-HERE.md](./00-START-HERE.md) |
| Setup inicial | [INICIO-AQUI.md](./INICIO-AQUI.md) |
| Entender arquitectura | [DEVELOPER-GUIDE.md](./DEVELOPER-GUIDE.md) |
| Buscar documentación específica | [CONSOLIDATION.md](./CONSOLIDATION.md) |
| Ver cambios recientes | [CHANGELOG.md](./CHANGELOG.md) |
| Hacer deploy | [DESPLEGAR-EN-RENDER.md](./DESPLEGAR-EN-RENDER.md) |
| Usar Claude Code | [CLAUDE.md](./CLAUDE.md) |
| Estado del proyecto | [../auditorias/PROGRESO_Y_ROADMAP_8.5_2025-12-05.md](../auditorias/PROGRESO_Y_ROADMAP_8.5_2025-12-05.md) |

---

## 📞 Soporte

**Email:** metrologiasam@gmail.com

**Producción:** https://app.sammetrologia.com

**Render Dashboard:** https://dashboard.render.com

---

## 📈 Estado del Proyecto

**Puntuación:** 7.8/10 (+0.6 desde Nov 2025)

**Tests:** 254/268 pasando (94.8%)

**Próximo Objetivo:** 8.5/10

Ver detalles en [CONSOLIDATION.md](./CONSOLIDATION.md)

---

**Última Actualización:** 5 de Diciembre de 2025

**¡Bienvenido al equipo SAM Metrología!** 🚀
