# ✅ EMPRESAS DE TESTING CREADAS EXITOSAMENTE

**Fecha de Creación:** 15 de Octubre de 2025
**Script Utilizado:** `crear_empresas_testing.py`
**Base de Datos:** SQLite (db.sqlite3)

---

## 📊 RESUMEN DE EMPRESAS CREADAS

Se crearon **4 empresas de prueba** con diferentes cantidades de equipos para probar todas las funcionalidades del sistema multi-partes.

| # | Nombre de Empresa | Equipos | Resultado Esperado | Usuario |
|---|-------------------|---------|-------------------|---------|
| 1 | Empresa Test 20 Equipos | 20 | ✅ Descarga directa normal (1 ZIP) | `test_20equipos` |
| 2 | Empresa Test 50 Equipos | 50 | 📦 Sistema multi-partes (2 ZIPs) | `test_50equipos` |
| 3 | Empresa Test 80 Equipos | 80 | 📦 Sistema multi-partes (3 ZIPs) | `test_80equipos` |
| 4 | Empresa Test 120 Equipos | 120 | 📦 Sistema multi-partes (4 ZIPs) | `test_120equipos` |

---

## 🔑 CREDENCIALES DE ACCESO

Todas las empresas comparten la misma contraseña para facilitar el testing:

```
Contraseña: test123
```

### Usuarios Creados

1. **Test 1 - Sin Multi-Partes**
   - Usuario: `test_20equipos`
   - Password: `test123`
   - Empresa: Empresa Test 20 Equipos
   - Equipos: 20
   - Rol: ADMINISTRADOR

2. **Test 2 - 2 Partes**
   - Usuario: `test_50equipos`
   - Password: `test123`
   - Empresa: Empresa Test 50 Equipos
   - Equipos: 50
   - Rol: ADMINISTRADOR

3. **Test 3 - 3 Partes**
   - Usuario: `test_80equipos`
   - Password: `test123`
   - Empresa: Empresa Test 80 Equipos
   - Equipos: 80
   - Rol: ADMINISTRADOR

4. **Test 4 - 4 Partes**
   - Usuario: `test_120equipos`
   - Password: `test123`
   - Empresa: Empresa Test 120 Equipos
   - Equipos: 120
   - Rol: ADMINISTRADOR

---

## 🚀 CÓMO REALIZAR EL TESTING

### Paso 1: Iniciar el Servidor

```bash
cd "C:\Users\LENOVO\OneDrive\Escritorio\sam-2"
python manage.py runserver
```

### Paso 2: Acceder al Sistema

1. Abrir navegador en: `http://127.0.0.1:8000/`
2. Hacer login con cualquiera de los usuarios creados
3. Navegar a: `http://127.0.0.1:8000/core/informes/`

### Paso 3: Probar Cada Escenario

---

## 📝 PLAN DE TESTING DETALLADO

### Test 1: Empresa Pequeña (20 equipos) - Descarga Normal

**Usuario:** `test_20equipos` / `test123`

**Objetivo:** Verificar que empresas ≤35 equipos NO usan sistema multi-partes

**Pasos:**
1. Login con `test_20equipos`
2. Ir a `/core/informes/`
3. Hacer clic en "Solicitar ZIP Completo"

**Resultado Esperado:**
- ✅ Descarga INMEDIATA de 1 solo ZIP
- ✅ NO aparece modal multi-partes
- ✅ Archivo descargado: `SAM_Equipos_Empresa Test 20 Equipos_YYYYMMDD_HHMM.zip`
- ✅ Estructura normal con 20 equipos

**Contenido del ZIP:**
```
SAM_Equipos_Empresa Test 20 Equipos_20251015_0911.zip
├── Empresa Test 20 Equipos/
│   ├── Informe_Consolidado.xlsx (20 equipos)
│   ├── Procedimientos/
│   │   └── README.txt (sin procedimientos con PDF)
│   └── Equipos/
│       ├── EQ-001/ (con Hoja_de_vida.pdf)
│       ├── EQ-002/
│       └── ... (hasta EQ-020)
```

---

### Test 2: Empresa Mediana (50 equipos) - 2 Partes

**Usuario:** `test_50equipos` / `test123`

**Objetivo:** Verificar sistema multi-partes con 2 ZIPs

**Pasos:**
1. Login con `test_50equipos`
2. Ir a `/core/informes/`
3. Hacer clic en "Solicitar ZIP Completo"

**Resultado Esperado:**
- ✅ Modal de descarga automática aparece
- ✅ Muestra 2 partes con rangos:
  - Parte 1/2: Equipos 1-35
  - Parte 2/2: Equipos 36-50 + Procedimientos
- ✅ Descarga automática secuencial
- ✅ Polling cada 3 segundos
- ✅ Indicadores visuales (⏳ → 🔄 → ⬇️ → ✅)
- ✅ Modal se cierra automáticamente después de 5 segundos

**Archivos Descargados:**
```
📥 SAM_Equipos_Empresa Test 50 Equipos_P1de2_EQ001-035_20251015_0911.zip
📥 SAM_Equipos_Empresa Test 50 Equipos_P2de2_EQ036-050_COMPLETO_20251015_0913.zip
```

**Verificación:**
1. Abrir ambos ZIPs
2. Verificar que ambos tienen `LEEME.txt` con información correcta
3. Verificar que ambos tienen `Informe_Consolidado.xlsx` con **50 equipos**
4. Verificar que SOLO la Parte 2 tiene carpeta `/Procedimientos/`
5. Verificar rangos de equipos:
   - Parte 1: EQ-001 a EQ-035
   - Parte 2: EQ-036 a EQ-050

---

### Test 3: Empresa Grande (80 equipos) - 3 Partes

**Usuario:** `test_80equipos` / `test123`

**Objetivo:** Verificar sistema multi-partes con 3 ZIPs

**Pasos:**
1. Login con `test_80equipos`
2. Ir a `/core/informes/`
3. Hacer clic en "Solicitar ZIP Completo"

**Resultado Esperado:**
- ✅ Modal muestra 3 partes:
  - Parte 1/3: Equipos 1-35
  - Parte 2/3: Equipos 36-70
  - Parte 3/3: Equipos 71-80 + Procedimientos
- ✅ Orden de generación optimizado (Parte 3 primero)
- ✅ 3 descargas automáticas

**Archivos Descargados:**
```
📥 SAM_Equipos_Empresa Test 80 Equipos_P1de3_EQ001-035_20251015_0915.zip
📥 SAM_Equipos_Empresa Test 80 Equipos_P2de3_EQ036-070_20251015_0917.zip
📥 SAM_Equipos_Empresa Test 80 Equipos_P3de3_EQ071-080_COMPLETO_20251015_0919.zip
```

**Verificación:**
- ✅ Todas las partes tienen Excel con **80 equipos completos**
- ✅ Solo Parte 3 tiene `/Procedimientos/`
- ✅ Nombres de archivo incluyen "_COMPLETO" en la última parte

---

### Test 4: Empresa Muy Grande (120 equipos) - 4 Partes

**Usuario:** `test_120equipos` / `test123`

**Objetivo:** Verificar límite máximo y múltiples partes

**Pasos:**
1. Login con `test_120equipos`
2. Ir a `/core/informes/`
3. Hacer clic en "Solicitar ZIP Completo"

**Resultado Esperado:**
- ✅ Modal muestra 4 partes:
  - Parte 1/4: Equipos 1-35
  - Parte 2/4: Equipos 36-70
  - Parte 3/4: Equipos 71-105
  - Parte 4/4: Equipos 106-120 + Procedimientos
- ✅ 4 descargas automáticas
- ✅ Excel con **120 equipos** en TODAS las partes

**Archivos Descargados:**
```
📥 SAM_Equipos_Empresa Test 120 Equipos_P1de4_EQ001-035_...zip
📥 SAM_Equipos_Empresa Test 120 Equipos_P2de4_EQ036-070_...zip
📥 SAM_Equipos_Empresa Test 120 Equipos_P3de4_EQ071-105_...zip
📥 SAM_Equipos_Empresa Test 120 Equipos_P4de4_EQ106-120_COMPLETO_...zip
```

---

## 🔍 PUNTOS DE VERIFICACIÓN CRÍTICOS

### 1. Límite de 35 Equipos por Parte
- ❌ NO debe permitir más de 35 equipos por ZIP
- ✅ Verificar que ninguna parte tenga >35 equipos

### 2. Excel Consolidado
- ✅ Debe estar en TODAS las partes
- ✅ Debe contener TODOS los equipos de la empresa
- ✅ Ejemplo: 80 equipos → Excel con 80 equipos en Parte 1, 2 y 3

### 3. Procedimientos
- ✅ Deben estar SOLO en la última parte
- ❌ NO deben estar en Parte 1, 2, etc.
- ✅ Solo archivo `_COMPLETO.zip` tiene `/Procedimientos/`

### 4. README.txt (LEEME.txt)
- ✅ Debe existir en todas las partes
- ✅ Debe tener información correcta de rango de equipos
- ✅ Debe indicar en qué parte están los procedimientos

### 5. Nombres de Archivo
**Formato correcto:**
```
SAM_Equipos_[EmpresaX]_P[N]de[T]_EQ[inicio]-[fin]_[timestamp].zip
```

**Ejemplos válidos:**
- ✅ `SAM_Equipos_Empresa Test 50 Equipos_P1de2_EQ001-035_20251015_0911.zip`
- ✅ `SAM_Equipos_Empresa Test 50 Equipos_P2de2_EQ036-050_COMPLETO_20251015_0913.zip`

### 6. Modal de Descarga
- ✅ Aparece automáticamente cuando >35 equipos
- ✅ Muestra progreso en tiempo real
- ✅ Descarga automáticamente cada parte (sin clics adicionales)
- ✅ Se cierra automáticamente al finalizar

---

## 📦 CONTENIDO DE CADA EMPRESA

### Todas las empresas incluyen:
- ✅ 3 Proveedores de prueba
- ✅ 3 Procedimientos (sin PDFs para testing)
- ✅ Usuario ADMINISTRADOR con acceso completo
- ✅ Equipos con código interno secuencial (EQ-001, EQ-002, etc.)
- ✅ Equipos con datos básicos: marca, modelo, número de serie

### Estructura de cada equipo:
```
EQ-XXX/
├── Hoja_de_vida.pdf (generado automáticamente)
├── Calibraciones/
│   ├── Certificados_Calibracion/ (vacío en testing)
│   ├── Confirmacion_Metrologica/ (vacío en testing)
│   └── Intervalos_Calibracion/ (vacío en testing)
├── Mantenimientos/ (vacío en testing)
├── Comprobaciones/ (vacío en testing)
└── [documentos del equipo] (vacíos en testing)
```

---

## ⚠️ NOTAS IMPORTANTES

1. **Warning de Importación Circular:**
   - Durante el inicio verás un warning sobre `cannot import name 'solicitar_zip'`
   - Esto NO afecta la funcionalidad del sistema multi-partes
   - Es un problema menor de organización de imports

2. **Procedimientos sin PDFs:**
   - Las empresas de prueba tienen procedimientos registrados
   - NO tienen PDFs adjuntos (para simplificar testing)
   - La carpeta `/Procedimientos/` contendrá un README.txt indicando esto

3. **Tiempo de Generación:**
   - Empresas pequeñas (20 equipos): Descarga inmediata
   - Empresas medianas (50 equipos): ~2-3 minutos total
   - Empresas grandes (80 equipos): ~4-5 minutos total
   - Empresas muy grandes (120 equipos): ~6-8 minutos total

4. **Navegador Recomendado:**
   - Google Chrome o Microsoft Edge (mejor soporte para descargas automáticas)
   - Asegurarse que el navegador permita múltiples descargas automáticas

---

## 🎯 CHECKLIST DE TESTING COMPLETO

### Pre-Testing
- [x] Empresas creadas en base de datos
- [x] Script de creación ejecutado exitosamente
- [ ] Servidor Django iniciado (`python manage.py runserver`)
- [ ] Navegador abierto en `http://127.0.0.1:8000/`

### Durante Testing
- [ ] Test 1: Empresa 20 equipos (descarga directa)
- [ ] Test 2: Empresa 50 equipos (2 partes automáticas)
- [ ] Test 3: Empresa 80 equipos (3 partes automáticas)
- [ ] Test 4: Empresa 120 equipos (4 partes automáticas)

### Verificaciones Post-Testing
- [ ] Todos los ZIPs descargados correctamente
- [ ] Cada ZIP tiene estructura correcta
- [ ] Excel consolidado en todas las partes
- [ ] README.txt en cada parte
- [ ] Procedimientos solo en última parte
- [ ] Nombres de archivo con formato correcto
- [ ] Modal funcionó correctamente
- [ ] Descargas automáticas exitosas

---

## 🔄 RECREAR EMPRESAS

Si necesitas recrear las empresas de prueba:

```bash
cd "C:\Users\LENOVO\OneDrive\Escritorio\sam-2"
python crear_empresas_testing.py
```

El script automáticamente:
- ✅ Elimina empresas existentes con los mismos NITs
- ✅ Elimina usuarios asociados
- ✅ Crea empresas frescas con todos los datos

---

## 📞 SOPORTE

Si encuentras problemas durante el testing:

1. **Verificar logs del servidor Django** en la consola donde corre `runserver`
2. **Revisar consola del navegador** (F12) para errores JavaScript
3. **Verificar estado de la base de datos:**
   ```bash
   python manage.py shell -c "from core.models import Empresa, Equipo; print([f'{e.nombre}: {e.equipos.count()} equipos' for e in Empresa.objects.all()])"
   ```

---

**Documento generado automáticamente por el script de creación de empresas**
**Fecha:** 15 de Octubre de 2025, 09:11 AM
