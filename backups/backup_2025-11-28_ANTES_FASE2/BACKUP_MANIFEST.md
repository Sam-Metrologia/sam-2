# BACKUP COMPLETO - SAM METROLOGÍA
## Fecha: 28 de Noviembre de 2025
## Propósito: Backup pre-implementación FASE 2 - Templates Metrológicos

---

## INFORMACIÓN DEL BACKUP

**Fecha de Creación**: 2025-11-28 19:22
**Hora**: Pre-implementación Fase 2 (Templates Confirmación, Comprobación, Mantenimiento)
**Motivo**: Implementación de templates metrológicos avanzados con cálculos automáticos
**Responsable**: Claude Code - Desarrollo FASE 2

---

## ARCHIVOS RESPALDADOS

### Base de Datos
- ✅ `db.sqlite3.backup` - Base de datos completa SQLite (todos los datos post-FASE 1)

### Código Crítico
- ✅ `models.py.backup` - Todos los modelos de datos (incluye cambios FASE 1)
- ✅ `settings.py.backup` - Configuración completa de Django
- ✅ `forms.py.backup` - Formularios actuales
- ✅ `template_confirmacion_v1.html.backup` - Prototipo template confirmación metrológica

---

## ESTADO DEL SISTEMA PRE-FASE 2

### ✅ FASE 1 COMPLETADA (27 Nov 2025)
- ✅ Formato de fechas YYYY-MM-DD globalizado
- ✅ Nuevos campos documentos: externo, interno, general
- ✅ Sistema ZIP con subcarpetas organizadas
- ✅ 9 índices de performance en BD
- ✅ 3 Hotfixes aplicados (archivos Excel guardando correctamente)

### 🆕 FASE 2 A IMPLEMENTAR
1. **Template Confirmación Metrológica**
   - Reglas de decisión ILAC G8 en español
   - Gráfica con EMP ± (límites visuales)
   - Método 1: Índice de calibración (escalera ILAC G-24)
   - Método 2: Deriva automática con puntos comunes (±5%)
   - EMP variable por punto
   - Cálculo automático de próxima calibración

2. **Template Comprobaciones** (Pendiente diseño)

3. **Template Mantenimientos** (Pendiente diseño)

### Funcionalidades Confirmadas (Funcionando)
- ✅ Sistema multi-tenant operativo
- ✅ Gestión de equipos, calibraciones, mantenimientos, comprobaciones
- ✅ Dashboard analítico
- ✅ Generación de reportes PDF
- ✅ Sistema de notificaciones
- ✅ Sistema ZIP asíncrono optimizado
- ✅ Subida de archivos propios del cliente (Excel, PDF)

---

## PLAN DE IMPLEMENTACIÓN FASE 2

### ESTRATEGIA: Convivencia sin Romper
```
OPCIÓN A (Actual - Mantener 100%):
✅ Cliente sube sus archivos propios
✅ Excel, PDF, cualquier formato
✅ Sin cambios en funcionalidad

OPCIÓN B (Nueva - Agregar):
🆕 Templates SAM optimizados
🆕 Confirmación Metrológica avanzada
🆕 Comprobaciones estructuradas
🆕 Mantenimientos estandarizados

OBJETIVO: Fidelización por VALOR
"Cliente elige templates SAM por superioridad técnica"
```

### FASE 2A - Template Confirmación Metrológica (Próximo)
**Características técnicas:**
- Normativa: Compatible ISO/IEC 17020 (Organismos de Inspección)
- Ideal para: ISO/IEC 17025 (Laboratorios de Calibración)
- ILAC G8:09/2019 - Reglas de decisión en español
- ILAC G-24 - Métodos de intervalos de calibración

**Impacto esperado**: CERO en funcionalidad actual
**Downtime esperado**: 0 minutos
**Riesgo**: 1/10 (solo agregar, no modificar)

---

## ESPECIFICACIONES TÉCNICAS FASE 2

### 1. Reglas de Decisión (ILAC G8)
- Traducción al español técnico
- Explicaciones cortas y contundentes
- 5 reglas implementadas con cálculos automáticos

### 2. Gráfica de Comportamiento Histórico
- Líneas EMP+ y EMP- (límites permitidos)
- Errores por calibración con barras de incertidumbre
- Visualización multi-anual (2023, 2024, 2025...)

### 3. Método 1 - Índice de Calibración (ILAC G-24)
- Aplicación: Calibración inicial O recurrente
- Fórmula: IC = E + F + U
- Tabla escalera: IC 3→36m, 4→24m, 5→12m, 6→6m

### 4. Método 2 - Deriva Temporal (Avanzado)
**Configuración:**
- Intervalo máximo configurable por cliente (36, 60, etc.)

**Análisis de puntos comunes:**
- Tolerancia: ±5% del nominal
- Solo puntos coincidentes entre calibraciones
- Cálculo de deriva por punto
- Criterio conservador: menor intervalo calculado

**Lógica:**
```python
Si deriva = 0 (error estable):
    → Intervalo = Intervalo_Máximo_Cliente

Si deriva > 0 (error cambiando):
    → Intervalo = EMP / Deriva
    Si resultado > Máximo: usar Máximo
    Si resultado < 6 meses: alerta técnica

Si NO hay puntos comunes:
    → Usar Método 1 (Índice Calibración)
    → Mensaje en conclusiones
```

### 5. EMP Variable por Punto
- Soportar diferentes EMP según rango de medición
- Ejemplo: 100mm → ±0.10mm, 1000mm → ±0.50mm

---

## INSTRUCCIONES DE RESTAURACIÓN

### Si algo sale mal en FASE 2, ejecutar:

```bash
# 1. Navegar al directorio del proyecto
cd C:\Users\LENOVO\OneDrive\Escritorio\sam-2

# 2. Detener la aplicación (si está corriendo)
# Ctrl+C en el servidor de desarrollo

# 3. Restaurar base de datos
cp "backups/backup_2025-11-28_ANTES_FASE2/db.sqlite3.backup" db.sqlite3

# 4. Restaurar models.py
cp "backups/backup_2025-11-28_ANTES_FASE2/models.py.backup" core/models.py

# 5. Restaurar settings.py
cp "backups/backup_2025-11-28_ANTES_FASE2/settings.py.backup" proyecto_c/settings.py

# 6. Restaurar forms.py
cp "backups/backup_2025-11-28_ANTES_FASE2/forms.py.backup" core/forms.py

# 7. Reiniciar aplicación
python manage.py runserver
```

### Verificación Post-Restauración
```bash
# Verificar que la aplicación arranca
python manage.py check

# Verificar migraciones
python manage.py showmigrations

# Verificar tests
pytest tests/ -x

# Verificar login funciona
# Navegar a http://localhost:8000/core/login/
```

---

## CHECKSUMS (Integridad)

### Archivos Respaldados:
- db.sqlite3.backup (~684 KB) - Post-FASE 1 con datos de prueba
- models.py.backup (128 KB aprox) - 25+ modelos
- settings.py.backup (21 KB aprox)
- forms.py.backup
- template_confirmacion_v1.html.backup (56 KB) - Prototipo inicial

---

## DIFERENCIAS vs BACKUP ANTERIOR (24 Oct 2025)

### Cambios Aplicados entre Backups:
1. ✅ Sistema de fechas YYYY-MM-DD
2. ✅ Campos documento_externo, analisis_interno
3. ✅ Estructura ZIP mejorada con subcarpetas
4. ✅ Índices de performance en BD
5. ✅ Corrección guardado de archivos Excel
6. ✅ Visualización mejorada en detalle_equipo.html
7. 🆕 Template confirmación metrológica (prototipo)

---

## CONTACTO EN CASO DE EMERGENCIA

**Si necesitas revertir cambios FASE 2:**
1. Sigue las instrucciones de restauración arriba
2. Ejecuta tests: `pytest`
3. Verifica funcionalidad básica
4. Compara con backup 24-Oct si es necesario

**Tiempo estimado de recuperación**: 5-10 minutos

---

## NOTAS ADICIONALES

- Este backup es PREVIO a integración de templates FASE 2
- Los archivos originales están preservados exactamente post-FASE 1
- Se recomienda mantener este backup por al menos 60 días
- Backup anterior (24-Oct) debe mantenerse como referencia histórica
- Template de confirmación es PROTOTIPO, no integrado a Django aún

---

## COMPATIBILIDAD

- ✅ Django 5.2.4
- ✅ Python 3.11+
- ✅ PostgreSQL 15 (producción) / SQLite (desarrollo)
- ✅ AWS S3 Storage configurado
- ✅ WhiteNoise para estáticos

---

**Backup completado exitosamente ✅**
**Listo para proceder con Fase 2 - Templates Metrológicos Avanzados**
**Fecha:** 2025-11-28 19:22
**Próximo paso:** Investigación normativa ILAC + Ajustes template
