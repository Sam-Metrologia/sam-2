# FIX: Problema de Duplicados en Descarga de ZIPs

**Fecha**: 30 de Octubre, 2025
**Problema**: Los usuarios no podían descargar ZIPs porque se generaban solicitudes duplicadas
**Error**: `get() returned more than one ZipRequest -- it returned 3!`

## Causa Raíz

Cuando un usuario hacía múltiples clicks en "Descargar ZIP" (especialmente en empresas con >35 equipos que usan multi-partes):

1. Se creaban múltiples solicitudes `ZipRequest` con los mismos parámetros
2. El código intentaba recuperarlas con `.get()` que espera **exactamente 1 resultado**
3. Al encontrar múltiples, lanzaba excepción `MultipleObjectsReturned`
4. El procesamiento asíncrono fallaba y los ZIPs nunca se generaban

## Solución Implementada

### 1. Limpieza Preventiva de Duplicados (Líneas 401-411)

Antes de crear nuevas solicitudes, limpiamos las antiguas pendientes del mismo usuario y empresa:

```python
# ✅ LIMPIAR solicitudes pendientes anteriores del usuario para esta empresa
# Esto evita duplicados si el usuario hace múltiples clicks
solicitudes_antiguas = ZipRequest.objects.filter(
    user=request.user,
    empresa=empresa,
    status__in=['pending', 'queued']
)
count_antiguas = solicitudes_antiguas.count()
if count_antiguas > 0:
    logger.info(f"🧹 Limpiando {count_antiguas} solicitudes antiguas pendientes de {request.user.username}")
    solicitudes_antiguas.delete()
```

### 2. Cambio de `.get()` a `.filter().first()` (Líneas 461-474)

Para evitar errores si aún quedan duplicados, cambiamos a un método más robusto:

**ANTES:**
```python
zip_req = ZipRequest.objects.get(
    user=request.user,
    empresa=empresa,
    parte_numero=parte_num,
    status='pending'
)  # ❌ Falla si hay duplicados
```

**DESPUÉS:**
```python
zip_req = ZipRequest.objects.filter(
    user=request.user,
    empresa=empresa,
    parte_numero=parte_num,
    status='pending'
).order_by('-created_at').first()  # ✅ Toma la más reciente, nunca falla

if zip_req:
    add_zip_request_to_queue(zip_req)
    logger.info(f"📦 Parte {parte_num} agregada a cola asíncrona (ID: {zip_req.id})")
else:
    logger.warning(f"⚠️ No se encontró solicitud ZIP para parte {parte_num}")
```

## Beneficios

1. **Prevención**: Limpia duplicados ANTES de crear nuevas solicitudes
2. **Robustez**: `.filter().first()` nunca falla, incluso si hay duplicados residuales
3. **Logging mejorado**: Ahora se registra el ID de cada solicitud procesada
4. **Experiencia del usuario**: Los ZIPs se descargan correctamente, incluso con múltiples clicks

## Archivos Modificados

- `core/zip_functions.py`: Función `generar_descarga_multipartes()` (líneas 401-474)

## Testing

Para verificar el fix:

1. Como usuario normal, solicitar descarga de ZIP para empresa con >35 equipos
2. Hacer múltiples clicks rápidos en "Descargar ZIP"
3. Verificar en logs que:
   - Se limpian solicitudes antiguas: `🧹 Limpiando X solicitudes antiguas pendientes`
   - Se agregan a cola correctamente: `📦 Parte X agregada a cola asíncrona (ID: Y)`
4. Confirmar que los ZIPs se descargan exitosamente

## Prevención Futura

Considerar agregar:

1. **Constraint único** en el modelo ZipRequest para evitar duplicados a nivel de base de datos
2. **Rate limiting** en el frontend para prevenir múltiples clicks
3. **Estado de carga** en el botón de descarga para dar feedback visual al usuario

## Logs Esperados

```
INFO: 🧹 Limpiando 2 solicitudes antiguas pendientes de CERTIBOY
INFO: 🔄 Sistema multi-partes activado: 69 equipos → 2 partes
INFO: ✅ Creadas 2 solicitudes ZIP para empresa CERTIBOY S.A.S.
INFO: 📦 Parte 2 agregada a cola asíncrona (ID: 37)
INFO: 📦 Parte 1 agregada a cola asíncrona (ID: 36)
```
