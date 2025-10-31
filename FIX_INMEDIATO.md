# ⚡ FIX INMEDIATO - Ejecutar en Render Shell

## 🔥 PASO 1: Limpiar TODAS las solicitudes pendientes

```bash
python manage.py shell -c "from core.models import ZipRequest; from django.utils import timezone; count = ZipRequest.objects.filter(status__in=['pending','queued','processing']).count(); ZipRequest.objects.filter(status__in=['pending','queued','processing']).update(status='failed', error_message='Limpieza por conflicto de workers', completed_at=timezone.now()); print(f'{count} solicitudes limpiadas')"
```

## 🔍 PASO 2: Verificar estado de solicitud específica (52)

```bash
python manage.py shell -c "from core.models import ZipRequest; req = ZipRequest.objects.get(id=52); print('Status:', req.status, '| Progress:', req.progress_percentage, '| Error:', req.error_message)"
```

## 🚀 PASO 3: Reiniciar el servicio web

**En Render Dashboard:**
1. Ve a tu servicio web
2. Click "Manual Deploy" → "Deploy latest commit"
3. Esto reiniciará con el nuevo código (thread worker desactivado)

## ✅ PASO 4: Probar nueva descarga

1. Login como CERTIBOY
2. Solicitar nuevo ZIP
3. Ahora SOLO el thread worker debería estar procesando
4. Debe completar en 2-3 minutos

## 🔧 Si sigue fallando:

Ejecutar en Shell:
```bash
ps aux | grep python
```

Si ves MÚLTIPLES procesos `async_zip` o `process_zip`, hay conflicto.

**Solución:** Reiniciar completamente el servicio.
