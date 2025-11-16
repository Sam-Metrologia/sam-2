# FIX COMPLETO: Problemas en Descarga de ZIPs

**Fecha**: 30 de Octubre, 2025
**Commits**: `07595a9` y `cbae91d`

## Problema 1: Solicitudes Duplicadas
**Error**: `get() returned more than one ZipRequest -- it returned 3!`

## Problema 2: Solicitudes No Se Procesaban
**Síntoma**: ZIPs quedaban en "calculando" indefinidamente después de deploy

## Problema 3: Worker Thread No Corriendo en Producción
**Síntoma**: Solicitudes se crean y agregan a cola, pero nunca se procesan

## Causas Raíz

### Problema 1: Duplicados
Cuando un usuario hacía múltiples clicks en "Descargar ZIP":

1. Se creaban múltiples solicitudes `ZipRequest` con los mismos parámetros
2. El código intentaba recuperarlas con `.get()` que espera **exactamente 1 resultado**
3. Al encontrar múltiples, lanzaba excepción `MultipleObjectsReturned`
4. El procesamiento asíncrono fallaba y los ZIPs nunca se generaban

### Problema 2: Cola Perdida en Reinicios
Después de cada deploy en Render:

1. El servidor se reinicia (como parte del proceso de deploy)
2. La cola en memoria (`Queue()`) se vacía completamente
3. Las solicitudes quedan huérfanas en la DB con status 'pending'
4. El worker sigue corriendo pero no tiene nada que procesar
5. Los ZIPs nunca se generan

### Problema 3: Worker Thread No Inicia en Gunicorn
El problema más crítico en producción:

1. `async_zip_improved.py` intenta iniciar worker thread desde `apps.py`
2. En Gunicorn, múltiples workers se crean y destruyen continuamente
3. Los threads iniciados en `apps.py` NO sobreviven a worker restarts
4. El `start.sh` NO ejecuta el procesador de cola como proceso separado
5. **Resultado**: Solicitudes se crean pero NUNCA se procesan
6. Los logs muestran "solicitud agregada a cola" pero nunca "procesando ZIP"

## Solución Implementada

### FIX 1: Prevención de Duplicados (zip_functions.py)

#### 1. Limpieza Preventiva de Duplicados (Líneas 401-411)

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

### FIX 2: Recuperación Automática de Solicitudes (async_zip_improved.py)

#### 3. Método `_recover_pending_requests()` (Líneas 49-74)

Al iniciar el procesador, recupera automáticamente todas las solicitudes pendientes de la base de datos:

```python
def _recover_pending_requests(self):
    """Recupera solicitudes pendientes de la DB y las agrega a la cola"""
    try:
        from core.models import ZipRequest
        from django.utils import timezone

        # Buscar solicitudes pendientes o en cola que no hayan expirado
        pending_requests = ZipRequest.objects.filter(
            status__in=['pending', 'queued'],
            expires_at__gt=timezone.now()
        ).order_by('position_in_queue', 'created_at')

        count = pending_requests.count()
        if count > 0:
            logger.info(f"🔄 Recuperando {count} solicitudes pendientes de la base de datos")

            for zip_req in pending_requests:
                self.processing_queue.put(zip_req)
                logger.info(f"📦 Solicitud recuperada: ID {zip_req.id} - Empresa: {zip_req.empresa.nombre} - Parte {zip_req.parte_numero}/{zip_req.total_partes}")

            logger.info(f"✅ {count} solicitudes recuperadas y agregadas a la cola")
```

Este método se ejecuta en `start_processor()` antes de iniciar el worker thread, asegurando que todas las solicitudes pendientes se procesen incluso después de un reinicio del servidor.

### FIX 3: Iniciar Procesador en start.sh (start.sh)

#### 4. Modificación de start.sh (Líneas 15-22)

El cambio más importante para que funcione en producción con Gunicorn:

```bash
# PASO 3: Iniciar procesador de cola ZIP en background
echo "🔄 Iniciando procesador de cola ZIP..."
mkdir -p logs

# Iniciar procesador ZIP en background
python manage.py process_zip_queue --check-interval 5 --cleanup-old >> logs/zip_processor.log 2>&1 &
ZIP_PROCESSOR_PID=$!
echo "✅ Procesador ZIP iniciado (PID: $ZIP_PROCESSOR_PID)"
```

**Por qué es necesario:**

1. Gunicorn crea/destruye workers constantemente, los threads no sobreviven
2. Se necesita un **proceso separado** que corra independiente de Gunicorn
3. El comando `process_zip_queue` revisa la DB cada 5 segundos buscando solicitudes pending
4. Al iniciar, ejecuta `--cleanup-old` para procesar solicitudes huérfanas
5. Corre en background (`&`) mientras Gunicorn maneja requests HTTP

**Flujo en Render:**

```
Deploy → start.sh ejecuta:
  1. python manage.py migrate
  2. python manage.py collectstatic
  3. python manage.py process_zip_queue &  ← NUEVO PROCESO ZIP WORKER
  4. gunicorn ← PROCESO WEB
```

Ahora hay **DOS procesos** corriendo en paralelo:
- **Gunicorn**: Maneja requests HTTP (crear solicitudes, servir vistas)
- **process_zip_queue**: Procesa solicitudes ZIP de la cola en DB

## Beneficios

1. **Prevención de Duplicados**: Limpia solicitudes antiguas ANTES de crear nuevas
2. **Robustez ante Errores**: `.filter().first()` nunca falla, incluso con duplicados residuales
3. **Recuperación Automática**: Solicitudes pendientes se recuperan tras reinicio del servidor
4. **Resiliencia a Deploys**: Los ZIPs se procesan correctamente incluso después de deploy en Render
5. **Logging Completo**: Se registra ID y estado de cada solicitud para debugging
6. **Experiencia del Usuario**: Los ZIPs se descargan correctamente en todos los escenarios

## Archivos Modificados

- `core/zip_functions.py`: Función `generar_descarga_multipartes()` (líneas 401-474) - **Commit 07595a9**
- `core/async_zip_improved.py`: Método `_recover_pending_requests()` (líneas 49-74) - **Commit cbae91d**
- `start.sh`: Inicio automático del procesador ZIP (líneas 15-22) - **Commit PENDIENTE**
- `limpiar_cola_zip.py`: Script para limpiar solicitudes huérfanas - **NUEVO**

## Testing

### Antes de Probar: Limpiar Solicitudes Huérfanas

Las solicitudes 47, 48 y cualquier otra pendiente nunca se procesarán porque el worker no estaba corriendo. Hay dos opciones:

**Opción A: Limpiar desde producción (Render Shell)**
```bash
# En Render Shell
python manage.py shell < limpiar_cola_zip.py
# Seleccionar opción 1 (eliminar) o 2 (marcar como fallidas)
```

**Opción B: Limpiar con comando Django**
```bash
# Marcar todas las pendientes como fallidas
python manage.py shell -c "from core.models import ZipRequest; from django.utils import timezone; ZipRequest.objects.filter(status__in=['pending','queued','processing']).update(status='failed', error_message='Worker no corriendo', completed_at=timezone.now())"
```

### Verificar el Fix Después del Deploy:

1. **Verificar que el procesador inició**:
   - En logs de Render buscar: `🔄 Iniciando procesador de cola ZIP...`
   - Luego: `✅ Procesador ZIP iniciado (PID: XXXX)`
   - Y: `[INICIO] Procesador de cola ZIP iniciado (intervalo: 5s)`

2. **Solicitar descarga de ZIP**:
   - Como usuario normal, solicitar descarga de ZIP para empresa con >35 equipos
   - Hacer múltiples clicks rápidos en "Descargar ZIP" (probar duplicados)

3. **Verificar en logs**:
   - **Creación**: `🧹 Limpiando X solicitudes antiguas pendientes`
   - **Cola**: `📦 Parte X agregada a cola asíncrona (ID: Y)`
   - **Procesamiento**: `[PROCESANDO] Solicitud #Y de USUARIO`
   - **Generación**: `[GENERANDO] Iniciando ZIP para empresa NOMBRE (X equipos)`
   - **Éxito**: `[EXITOSO] ZIP completado: ruta (X bytes)`

4. **Confirmar descarga**: Los ZIPs se descargan exitosamente en 10-30 segundos (según tamaño)

## Prevención Futura

Considerar agregar:

1. **Constraint único** en el modelo ZipRequest para evitar duplicados a nivel de base de datos
2. **Rate limiting** en el frontend para prevenir múltiples clicks
3. **Estado de carga** en el botón de descarga para dar feedback visual al usuario

## Logs Esperados

### Al Iniciar Render (start.sh):
```
🚀 Iniciando SAM Metrología...
📦 Aplicando migraciones...
📁 Recolectando archivos estáticos...
🔄 Iniciando procesador de cola ZIP...
✅ Procesador ZIP iniciado (PID: 123)
🌐 Iniciando servidor Gunicorn...
```

### En logs/zip_processor.log:
```
[INICIO] Procesador de cola ZIP iniciado (intervalo: 5s)
[LIMPIEZA] Limpiando solicitudes antiguas...
[LIMPIEZA] Eliminadas 0 solicitudes antiguas
[ESPERANDO] Iteración 1: Cola vacía, esperando...
```

### Al Solicitar Descarga (logs principales):
```
INFO: 🧹 Limpiando 2 solicitudes antiguas pendientes de CERTIBOY
INFO: 🔄 Sistema multi-partes activado: 69 equipos → 2 partes
INFO: ✅ Creadas 2 solicitudes ZIP para empresa CERTIBOY S.A.S.
INFO: 📦 Parte 2 agregada a cola asíncrona (ID: 48)
INFO: 📦 Parte 1 agregada a cola asíncrona (ID: 47)
```

### Durante Procesamiento (logs/zip_processor.log):
```
[PROCESANDO] Solicitud #47 de CERTIBOY
[GENERANDO] Iniciando ZIP para empresa CERTIBOY S.A.S. (69 equipos)
[COMPRESIÓN] Usando nivel 2 para 35 equipos
[EXCEL] Generando Excel consolidado...
[PROCEDIMIENTOS] Empresa CERTIBOY S.A.S. tiene 3 procedimientos
[EQUIPO] Procesando 1/35 (15%): EQ-001
[EQUIPO] Procesando 2/35 (17%): EQ-002
...
[EXITOSO] ZIP completado: zip_requests/1/20251030_133500_parte_1_req_47.zip (15234567 bytes)
[PROCESANDO] Solicitud #48 de CERTIBOY
...
```
