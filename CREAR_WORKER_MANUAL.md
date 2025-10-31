# 🛠️ Crear Background Worker Manualmente en Render

**Fecha**: 31 de Octubre, 2025
**Razón**: `render.yaml` no se está aplicando automáticamente

---

## 🎯 Objetivo

Crear un **Background Worker separado** para procesar ZIPs, independiente del servicio web (Gunicorn).

---

## 📋 Pasos Detallados

### **Paso 1: Ir al Dashboard de Render**

1. Abre [https://dashboard.render.com](https://dashboard.render.com)
2. Login con tu cuenta
3. Ve al proyecto/servicio **sam-metrologia** o **sam-9o6o**

---

### **Paso 2: Crear Nuevo Background Worker**

1. Click en **"New"** (botón azul arriba a la derecha)
2. Selecciona **"Background Worker"**
3. **NO** selecciones "Web Service" - debe ser "Background Worker"

---

### **Paso 3: Configurar Repositorio**

1. **Repository**: Selecciona `Sam-Metrologia/sam-2` (tu repo de GitHub)
2. **Branch**: `main`
3. Click **"Connect"**

---

### **Paso 4: Configuración Básica del Worker**

| Campo | Valor |
|-------|-------|
| **Name** | `sam-zip-processor` |
| **Region** | `Oregon` (misma que el web service) |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `./build.sh` |
| **Start Command** | `python manage.py process_zip_queue --check-interval 3 --cleanup-old` |

**⚠️ IMPORTANTE**: El **Start Command** es la parte más crítica. Cópialo exactamente:
```bash
python manage.py process_zip_queue --check-interval 3 --cleanup-old
```

---

### **Paso 5: Variables de Entorno (Environment Variables)**

**CRÍTICO**: El worker necesita las MISMAS variables que el web service.

**Opción A - Copiar del Web Service:**
1. Abre el web service `sam-metrologia` en otra pestaña
2. Ve a **Environment** tab
3. **Copia** cada variable a mano

**Opción B - Agregar manualmente:**

| Variable | Valor | Notas |
|----------|-------|-------|
| `SECRET_KEY` | (copiar del web service) | Debe ser el MISMO |
| `DATABASE_URL` | (copiar del web service) | Conexión PostgreSQL |
| `AWS_ACCESS_KEY_ID` | (copiar del web service) | Acceso a S3 |
| `AWS_SECRET_ACCESS_KEY` | (copiar del web service) | Secret de S3 |
| `AWS_STORAGE_BUCKET_NAME` | `sam-plataforma-media` | Bucket de S3 |
| `AWS_S3_REGION_NAME` | `us-east-2` | Región S3 |
| `DEBUG_VALUE` | `False` | Desactivar debug |
| `RENDER_EXTERNAL_HOSTNAME` | `sam-9o6o.onrender.com` | Tu dominio Render |
| `PYTHON_VERSION` | `3.11.9` | (opcional) |

**⚠️ IMPORTANTE**:
- `DATABASE_URL` debe ser EXACTAMENTE el mismo que el web service
- Si usas variables "fromDatabase" en el web service, aquí debes pegar el valor completo

---

### **Paso 6: Plan Selection**

1. **Plan**: Selecciona **"Free"** (o el plan que prefieras)
2. **Disk**: No necesario para worker

---

### **Paso 7: Crear Worker**

1. Revisa toda la configuración
2. Click **"Create Background Worker"**
3. Render comenzará a hacer build y deploy

---

### **Paso 8: Verificar Logs**

Cuando el worker esté **"Live"**, verifica los logs:

**Debes ver:**
```
[INICIO] Procesador de cola ZIP iniciado (intervalo: 3s)
[LIMPIEZA] Limpiando solicitudes antiguas...
[LIMPIEZA] Eliminadas X solicitudes antiguas
[ESPERANDO] Iteración 1: Cola vacía, esperando...
[ESPERANDO] Iteración 2: Cola vacía, esperando...
```

**Cuando procese un ZIP:**
```
[PROCESANDO] Solicitud #XX de CERTIBOY
[GENERANDO] Iniciando ZIP para empresa CERTIBOY S.A.S. (69 equipos)
[COMPRESIÓN] Usando nivel 2 para 35 equipos
[EXCEL] Generando Excel consolidado...
[EQUIPO] Procesando 1/35 (15%): EQ-001
...
[EXITOSO] ZIP completado: ruta (15234567 bytes)
```

---

## ✅ Verificación Final

### **Debes tener 2 servicios corriendo:**

```
✅ sam-metrologia (Web Service)     - Running
✅ sam-zip-processor (Worker)       - Running
```

### **Probar descarga ZIP:**

1. Login como CERTIBOY
2. Solicitar descarga ZIP
3. **Ahora debería ser MUCHO MÁS RÁPIDO:**
   - Parte 1 (35 equipos): ~60-90 segundos
   - Parte 2 (34 equipos): ~60-90 segundos
   - Total: 2-3 minutos para 69 equipos

---

## 🔍 Troubleshooting

### **Si el worker no inicia:**

**Error común**: `gunicorn not found` o `port already in use`
- **Causa**: Start Command incorrecto
- **Solución**: Verificar que el Start Command sea:
  ```
  python manage.py process_zip_queue --check-interval 3 --cleanup-old
  ```
  NO uses `./start.sh` - eso es solo para el web service

### **Si dice "Database connection error":**

- **Causa**: `DATABASE_URL` no configurada o incorrecta
- **Solución**: Copiar EXACTAMENTE el `DATABASE_URL` del web service

### **Si el worker corre pero no procesa:**

En Render Shell del WORKER, ejecutar:
```bash
ps aux | grep process_zip_queue
```

Debe mostrar:
```
python manage.py process_zip_queue --check-interval 3 --cleanup-old
```

Si NO aparece, el Start Command está mal.

---

## 💰 Costos

**Free Tier de Render:**
- Web Service: 512 MB RAM
- Background Worker: 512 MB RAM adicional
- **Total**: 1 GB RAM

**⚠️ Límite de horas:**
- Free tier: 750 horas/mes
- 2 servicios: 2 × 730 horas = 1460 horas/mes

**Opciones:**
1. Worker solo consume horas cuando hay carga
2. Render auto-escala basado en actividad
3. Si excedes, considera Starter plan ($7/mes por servicio)

---

## 🎯 Resultado Esperado

**Antes (con thread worker):**
- ❌ 9 segundos por equipo
- ❌ 5+ minutos para parte de 34 equipos
- ❌ Worker compite con requests HTTP

**Después (con background worker):**
- ✅ ~2 segundos por equipo
- ✅ 60-90 segundos para parte de 35 equipos
- ✅ Worker independiente, sin competencia

---

## 📚 Documentación Relacionada

- `SOLUCIÓN_FINAL_ZIP.md` - Arquitectura completa
- `FIX_ZIP_DUPLICADOS.md` - Problemas y soluciones
- `render.yaml` - Configuración Blueprint (no aplicada automáticamente)

---

## ✨ Próximo Paso

Después de crear el worker:
1. **Espera** 5-10 minutos para el build
2. **Verifica** logs del worker
3. **Prueba** descarga ZIP
4. **Reporta** si funciona correctamente

**Si todo va bien, deberías ver ZIPs listos en 2-3 minutos total.** 🚀
