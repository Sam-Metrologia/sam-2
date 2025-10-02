# 🔍 DEBUG FORMULARIOS DE ACTIVIDADES

## Logging Detallado Implementado

He agregado logging detallado en **todos los formularios de actividades** para identificar rápidamente los errores. Los logs aparecen automáticamente en la consola del servidor Django.

## 📍 Dónde Ver los Logs

### 1. En el servidor Django (recomendado)
```bash
python manage.py runserver
```
Los logs aparecen directamente en la consola con emojis y colores para facilitar identificación.

### 2. En archivos de log (producción)
- `logs/sam_info.log` - Logs generales
- `logs/sam_errors.log` - Solo errores
- `logs/sam_security.log` - Eventos de seguridad

## 🔎 Tipos de Logs Implementados

### ✅ **LOGS DE ÉXITO**
```
✅ ÉXITO: Calibración creada ID: 123 para equipo Balanza Digital
✅ ÉXITO: Mantenimiento creado ID: 456 para equipo Termómetro
✅ ÉXITO: Comprobación creada ID: 789 para equipo Multímetro
```

### ❌ **LOGS DE ERROR DETALLADOS**

#### 1. **Formulario Inválido**
```
❌ FORMULARIO INVÁLIDO
Errores del formulario: {'proveedor': ['Este campo es obligatorio.']}
Errores no de campo: ['Debe seleccionar un proveedor o ingresar el nombre del proveedor.']
Proveedores disponibles para Empresa XYZ: 0
```

#### 2. **Errores de Validación**
```
❌ ERROR DE VALIDACIÓN: Debe seleccionar un proveedor o ingresar el nombre del proveedor.
```

#### 3. **Errores Generales con Traceback**
```
❌ ERROR GENERAL al guardar calibración: 'NoneType' object has no attribute 'save'
Tipo de error: AttributeError
Traceback: File "/path/to/views.py", line 123, in create_calibration...
```

### 📊 **LOGS INFORMATIVOS**

#### 1. **GET Requests**
```
GET request - mostrando formulario vacío
Proveedores disponibles para Empresa XYZ: 3
```

#### 2. **POST Requests Detallados**
```
=== POST CALIBRACIÓN - Datos recibidos ===
POST data: {'fecha_calibracion': '25/09/2025', 'proveedor': '15', 'resultado': 'Aprobado'}
FILES data: ['documento_calibracion']
Empresa del equipo: Empresa XYZ
Formulario inicializado para empresa: Empresa XYZ
Formulario es VÁLIDO - procesando...
```

## 🚨 Cómo Identificar Problemas Rápidamente

### **Problema 1: No hay proveedores disponibles**
```
❌ FORMULARIO INVÁLIDO
Proveedores disponibles para Empresa ABC: 0
```
**Solución**: Crear proveedores para esa empresa en el admin.

### **Problema 2: Validación de proveedor falla**
```
Errores no de campo: ['Debe seleccionar un proveedor o ingresar el nombre del proveedor.']
```
**Solución**: Usuario debe seleccionar un proveedor O escribir un nombre manualmente.

### **Problema 3: Error de almacenamiento**
```
❌ ERROR DE VALIDACIÓN: Límite de almacenamiento excedido
```
**Solución**: Archivo demasiado grande o empresa sin espacio.

### **Problema 4: Error de archivos**
```
❌ ERROR GENERAL: 'str' object has no attribute 'read'
```
**Solución**: Problema con el procesamiento de archivos PDF.

## 📋 Checklist para Debug

Cuando un formulario no funciona:

1. **✅ Verificar logs de POST**
   - ¿Se reciben los datos correctos?
   - ¿Se inicializa el formulario?

2. **✅ Verificar validación**
   - ¿El formulario es válido?
   - ¿Qué errores específicos hay?

3. **✅ Verificar proveedores**
   - ¿Hay proveedores disponibles para esa empresa?
   - ¿Son del tipo de servicio correcto?

4. **✅ Verificar archivos**
   - ¿Los archivos se están subiendo correctamente?
   - ¿Son PDFs válidos?

5. **✅ Verificar permisos**
   - ¿El usuario pertenece a la empresa del equipo?
   - ¿Tiene permisos para crear actividades?

## 🔧 Soluciones Comunes

### **Crear proveedores de prueba rápidamente**
```python
# Ejecutar en shell: python manage.py shell
from core.models import Proveedor, Empresa

empresa = Empresa.objects.get(nombre="Tu Empresa")

# Crear proveedores básicos
Proveedor.objects.create(
    nombre_empresa="Proveedor Calibraciones S.A.",
    empresa=empresa,
    tipo_servicio='Calibración'
)

Proveedor.objects.create(
    nombre_empresa="Mantenimientos Técnicos Ltda.",
    empresa=empresa,
    tipo_servicio='Mantenimiento'
)

Proveedor.objects.create(
    nombre_empresa="Comprobaciones Especializadas",
    empresa=empresa,
    tipo_servicio='Comprobación'
)
```

## 📞 Monitoreo en Tiempo Real

Para monitorear los logs en tiempo real:

```bash
# En Windows
python manage.py runserver

# En Linux/Mac (si usas archivos de log)
tail -f logs/sam_errors.log
```

Los logs están configurados con **emojis y formato claro** para identificar problemas rápidamente:
- ✅ = Éxito
- ❌ = Error
- 📊 = Información
- 🔍 = Debug

Ahora podrás identificar exactamente qué está fallando en los formularios sin tener que adivinar.