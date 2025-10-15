# Instrucciones de Testing - Sistema Multi-Partes ZIP

**Fecha:** 14 de octubre de 2025
**Estado:** ✅ IMPLEMENTACIÓN COMPLETA - Listo para testing
**URL de Testing:** http://127.0.0.1:8000/core/informes/

---

## ✅ IMPLEMENTACIÓN COMPLETADA

### Backend (100% Completo)
- ✅ Límite de 35 equipos por parte
- ✅ División automática en múltiples partes
- ✅ README.txt en cada parte
- ✅ Excel consolidado en TODAS las partes
- ✅ Procedimientos solo en última parte
- ✅ Nombres de archivo con rangos (EQ001-035)
- ✅ Orden optimizado (Parte 3 primero)
- ✅ Migraciones aplicadas

### Frontend (100% Completo)
- ✅ Modal de descarga automática
- ✅ Polling cada 3 segundos
- ✅ Descarga automática secuencial
- ✅ Indicadores visuales de progreso
- ✅ Notificación de completado
- ✅ Integrado en `/core/informes/`

---

## 🧪 PLAN DE TESTING

### Test 1: Empresa Pequeña (≤35 equipos) - SIN CAMBIOS

**Objetivo:** Verificar que empresas pequeñas siguen funcionando igual

**Pasos:**
1. Ir a http://127.0.0.1:8000/core/informes/
2. Seleccionar empresa con 10-20 equipos
3. Hacer clic en "Solicitar ZIP Completo"

**Resultado Esperado:**
- ✅ Descarga directa e inmediata (1 solo ZIP)
- ✅ NO aparece modal multi-partes
- ✅ Archivo descargado: `SAM_Equipos_EmpresaX_YYYYMMDD_HHMM.zip`
- ✅ Estructura normal con todos los equipos

---

### Test 2: Empresa Mediana (36-70 equipos) - SISTEMA MULTI-PARTES

**Objetivo:** Verificar sistema multi-partes con 2 ZIPs

**Pasos:**
1. Ir a http://127.0.0.1:8000/core/informes/
2. Seleccionar empresa con 50 equipos (crear si no existe)
3. Hacer clic en "Solicitar ZIP Completo"

**Resultado Esperado:**

**a) Modal aparece automáticamente:**
```
╔═══════════════════════════════════════════════════════════╗
║    📦 Descarga Automática en Progreso                     ║
╟───────────────────────────────────────────────────────────╢
║  Su empresa tiene 50 equipos                              ║
║  Se dividió en 2 partes de máximo 35 equipos             ║
╟───────────────────────────────────────────────────────────╢
║  ⏳ Parte 1/2: Equipos 1-35         | Pendiente          ║
║  ⏳ Parte 2/2: Equipos 36-50        | Pendiente          ║
║      + Procedimientos                                      ║
╟───────────────────────────────────────────────────────────╢
║  Progreso general: ▓▓▓▓▓░░░░░░░  0%                      ║
║  Iniciando descarga automática...                         ║
╟───────────────────────────────────────────────────────────╢
║  ⚠️ No cierre esta ventana hasta completar               ║
╚═══════════════════════════════════════════════════════════╝
```

**b) Proceso de descarga:**
1. Parte 2 se genera PRIMERO (orden optimizado)
2. Luego Parte 1
3. Cada parte se descarga automáticamente al completarse
4. Modal se cierra automáticamente después de 5 segundos
5. Alert confirma: "✅ Descarga completada: 2 archivos ZIP descargados"

**c) Archivos descargados (en carpeta Descargas):**
```
📥 SAM_Equipos_EmpresaX_P1de2_EQ001-035_20251014_1530.zip
📥 SAM_Equipos_EmpresaX_P2de2_EQ036-050_COMPLETO_20251014_1532.zip
```

**d) Contenido Parte 1:**
```
SAM_Equipos_EmpresaX_P1de2_EQ001-035_20251014_1530.zip
├── EmpresaX/
│   ├── LEEME.txt  ← Explica que es Parte 1 de 2
│   ├── Informe_Consolidado.xlsx  ← TODOS los 50 equipos
│   └── Equipos/
│       ├── Equipo_001/ (completo con hojas de vida, actividades, documentos)
│       ├── Equipo_002/
│       └── ... (hasta Equipo_035)
```

**e) Contenido Parte 2 (COMPLETO):**
```
SAM_Equipos_EmpresaX_P2de2_EQ036-050_COMPLETO_20251014_1532.zip
├── EmpresaX/
│   ├── LEEME.txt  ← Indica que es la última parte
│   ├── Informe_Consolidado.xlsx  ← TODOS los 50 equipos (repetido)
│   ├── Procedimientos/  ← SOLO EN ÚLTIMA PARTE
│   │   ├── PROC-001_Calibracion.pdf
│   │   └── PROC-002_Mantenimiento.pdf
│   └── Equipos/
│       ├── Equipo_036/
│       └── ... (hasta Equipo_050)
```

**f) Verificar README.txt:**
Abrir `LEEME.txt` y verificar que contiene:
- Número de parte correcta
- Rango de equipos correcto
- Información sobre Excel y procedimientos
- Fecha y empresa

---

### Test 3: Empresa Grande (71-105 equipos) - 3 PARTES

**Objetivo:** Verificar sistema multi-partes con 3 ZIPs

**Pasos:**
1. Crear empresa con 80 equipos (si no existe)
2. Ir a http://127.0.0.1:8000/core/informes/
3. Seleccionar la empresa
4. Hacer clic en "Solicitar ZIP Completo"

**Resultado Esperado:**

**a) Modal muestra 3 partes:**
- Parte 1/3: Equipos 1-35
- Parte 2/3: Equipos 36-70
- Parte 3/3: Equipos 71-80 + Procedimientos

**b) Orden de generación:**
1. Parte 3 se genera PRIMERO (tiene procedimientos)
2. Luego Parte 1
3. Finalmente Parte 2

**c) Archivos descargados:**
```
📥 SAM_Equipos_EmpresaX_P1de3_EQ001-035_20251014_1530.zip
📥 SAM_Equipos_EmpresaX_P2de3_EQ036-070_20251014_1532.zip
📥 SAM_Equipos_EmpresaX_P3de3_EQ071-080_COMPLETO_20251014_1534.zip
```

**d) Verificar cada archivo:**
- ✅ Parte 1: 35 equipos + Excel (80 equipos)
- ✅ Parte 2: 35 equipos + Excel (80 equipos)
- ✅ Parte 3: 10 equipos + Excel (80 equipos) + Procedimientos

---

### Test 4: Empresa Muy Grande (106+ equipos) - 4+ PARTES

**Objetivo:** Verificar límite máximo y múltiples partes

**Pasos:**
1. Crear empresa con 120 equipos
2. Ir a http://127.0.0.1:8000/core/informes/
3. Seleccionar la empresa
4. Hacer clic en "Solicitar ZIP Completo"

**Resultado Esperado:**
- ✅ 4 partes generadas automáticamente
- ✅ Parte 1: Equipos 1-35
- ✅ Parte 2: Equipos 36-70
- ✅ Parte 3: Equipos 71-105
- ✅ Parte 4: Equipos 106-120 + Procedimientos (COMPLETO)
- ✅ Excel con 120 equipos en TODAS las partes

---

## 🔍 PUNTOS DE VERIFICACIÓN CRÍTICOS

### 1. Límite de 35 Equipos
**Verificar:**
- ❌ NO debe permitir más de 35 equipos por ZIP
- ✅ Empresa con 36 equipos debe crear 2 ZIPs
- ✅ Empresa con 35 equipos debe crear 1 ZIP

### 2. Excel Consolidado
**Verificar:**
- ✅ Debe estar en TODAS las partes
- ✅ Debe contener TODOS los equipos (no solo los de la parte)
- ✅ Ejemplo: 80 equipos → Excel con 80 equipos en Parte 1, 2 y 3

### 3. Procedimientos
**Verificar:**
- ✅ Deben estar SOLO en la última parte
- ❌ NO deben estar en Parte 1 o 2
- ✅ Carpeta `/Procedimientos/` solo en `_COMPLETO.zip`

### 4. README.txt
**Verificar:**
- ✅ Debe existir en todas las partes
- ✅ Debe tener información correcta de rango de equipos
- ✅ Debe indicar en qué parte están los procedimientos

### 5. Nombres de Archivo
**Verificar formato:**
```
SAM_Equipos_EmpresaX_P[N]de[T]_EQ[inicio]-[fin]_[timestamp].zip
                    ↑     ↑      ↑        ↑         ↑
               Parte    Total   Inicio    Fin    Fecha/hora
```

**Ejemplos válidos:**
- ✅ `SAM_Equipos_MiEmpresa_P1de3_EQ001-035_20251014_1530.zip`
- ✅ `SAM_Equipos_MiEmpresa_P2de3_EQ036-070_20251014_1532.zip`
- ✅ `SAM_Equipos_MiEmpresa_P3de3_EQ071-080_COMPLETO_20251014_1534.zip`

### 6. Modal de Descarga
**Verificar:**
- ✅ Aparece automáticamente al detectar >35 equipos
- ✅ Muestra progreso en tiempo real
- ✅ Descarga automáticamente cada parte
- ✅ No requiere clics adicionales del usuario
- ✅ Se cierra automáticamente al finalizar

### 7. Orden de Generación
**Verificar:**
- ✅ Última parte (con procedimientos) se genera PRIMERO
- ✅ Luego se generan las demás en orden
- ✅ Usuario recibe Excel y procedimientos primero

---

## 🐛 PROBLEMAS COMUNES Y SOLUCIONES

### Problema 1: Modal no aparece
**Síntomas:** Al hacer clic, descarga normal sin modal

**Causa:** Empresa tiene ≤35 equipos

**Solución:** Verificar que la empresa tenga >35 equipos

---

### Problema 2: Descarga no inicia
**Síntomas:** Modal aparece pero no progresa

**Causa:** Procesador asíncrono no está corriendo

**Solución:**
```bash
# Verificar logs
tail -f logs/sam_info.log | grep "ZIP"

# Debería ver líneas como:
# "🚀 AsyncZipProcessor iniciado"
# "📦 Solicitud ZIP agregada a cola"
```

---

### Problema 3: Solo se descarga una parte
**Síntomas:** Modal muestra 3 partes pero solo descarga 1

**Causa:** Error en polling o generación

**Solución:**
1. Abrir consola del navegador (F12)
2. Ver si hay errores JavaScript
3. Verificar que procesador asíncrono está corriendo
4. Revisar logs: `logs/sam_info.log`

---

### Problema 4: Excel no tiene todos los equipos
**Síntomas:** Excel solo tiene equipos de esa parte

**Causa:** Error en la consulta de equipos para Excel

**Solución:**
Verificar en `async_zip_improved.py` línea 224-231:
```python
# Debe obtener TODOS los equipos
todos_equipos_empresa = Equipo.objects.filter(empresa=empresa).order_by('codigo_interno')
```

---

### Problema 5: Procedimientos en todas las partes
**Síntomas:** Procedimientos aparecen en Parte 1, 2, etc.

**Causa:** Falta validación `if parte_numero == total_partes`

**Solución:**
Verificar en `async_zip_improved.py` línea 243:
```python
if parte_numero == total_partes:
    # Solo agregar procedimientos aquí
```

---

## 📊 MÉTRICAS DE ÉXITO

### Test Exitoso si:
- ✅ Empresas ≤35 equipos: 1 ZIP, descarga normal
- ✅ Empresas >35 equipos: Múltiples ZIPs, modal aparece
- ✅ Excel consolidado en TODAS las partes
- ✅ Procedimientos SOLO en última parte
- ✅ README.txt en todas las partes con info correcta
- ✅ Nombres de archivo con formato correcto
- ✅ Descarga automática sin intervención del usuario
- ✅ Modal muestra progreso en tiempo real
- ✅ Todas las partes se descargan completamente

---

## 🚀 COMANDO PARA CREAR EMPRESA DE PRUEBA

Si necesitas crear una empresa con muchos equipos para testing:

```bash
cd "C:\Users\LENOVO\OneDrive\Escritorio\sam-2"
python manage.py shell

# Dentro del shell:
from core.models import Empresa, Equipo, CustomUser
from django.contrib.auth import get_user_model

# Crear empresa de prueba
empresa_test = Empresa.objects.create(
    nombre="Empresa Test 80 Equipos",
    nit="123456789-0",
    email="test@empresa.com"
)

# Crear usuario para la empresa
user = CustomUser.objects.filter(empresa=empresa_test).first()
if not user:
    user = CustomUser.objects.create_user(
        username="test_80equipos",
        email="test@empresa.com",
        password="test123",
        empresa=empresa_test,
        rol_usuario="ADMINISTRADOR"
    )

# Crear 80 equipos
for i in range(1, 81):
    Equipo.objects.create(
        codigo_interno=f"EQ-{i:03d}",
        nombre=f"Equipo Test {i}",
        marca=f"Marca {i}",
        modelo=f"Modelo {i}",
        numero_serie=f"SN{i:05d}",
        estado="Activo",
        empresa=empresa_test,
        created_by=user
    )

print("✅ Empresa creada con 80 equipos")
print(f"Usuario: test_80equipos")
print(f"Password: test123")
exit()
```

---

## 📝 CHECKLIST DE TESTING

### Pre-Testing
- [ ] Servidor corriendo: `python manage.py runserver`
- [ ] Migraciones aplicadas: `python manage.py migrate`
- [ ] Empresa de prueba creada con >35 equipos
- [ ] Usuario con permisos ADMINISTRADOR o GERENCIA

### During Testing
- [ ] Test 1: Empresa ≤35 equipos (descarga normal)
- [ ] Test 2: Empresa 36-70 equipos (2 partes)
- [ ] Test 3: Empresa 71-105 equipos (3 partes)
- [ ] Test 4: Empresa 106+ equipos (4+ partes)

### Post-Testing
- [ ] Verificar archivos descargados existen
- [ ] Abrir cada ZIP y verificar estructura
- [ ] Verificar Excel tiene todos los equipos
- [ ] Verificar README.txt en cada parte
- [ ] Verificar Procedimientos solo en última parte
- [ ] Verificar nombres de archivo correctos

---

## 🎯 SIGUIENTE PASO: TESTING

**Acción inmediata:**
1. Abrir navegador
2. Ir a http://127.0.0.1:8000/core/informes/
3. Crear empresa con 50 equipos (usar script arriba)
4. Iniciar sesión con usuario de esa empresa
5. Hacer clic en "Solicitar ZIP Completo"
6. ¡Observar el sistema multi-partes en acción! 🚀

---

**Creado por:** Claude Code (Anthropic)
**Fecha:** 14 de octubre de 2025
**Estado:** ✅ LISTO PARA TESTING
**Implementación:** 100% Completa (Backend + Frontend)
