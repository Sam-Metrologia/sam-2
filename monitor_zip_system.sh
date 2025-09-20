#!/bin/bash

# Script para monitorear el sistema de cola ZIP
# Uso: ./monitor_zip_system.sh

echo "📊 Monitor del Sistema de Cola ZIP"
echo "=================================="

# Verificar si el procesador está ejecutándose
if [ -f logs/zip_processor.pid ]; then
    PID=$(cat logs/zip_processor.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "✅ Procesador ZIP ejecutándose (PID: $PID)"

        # Mostrar uso de memoria del procesador
        MEMORY=$(ps -p $PID -o rss= 2>/dev/null)
        if [ ! -z "$MEMORY" ]; then
            MEMORY_MB=$((MEMORY / 1024))
            echo "📊 Uso de memoria del procesador: ${MEMORY_MB} MB"
        fi
    else
        echo "❌ Procesador ZIP NO está ejecutándose"
        rm logs/zip_processor.pid
    fi
else
    echo "❌ Procesador ZIP NO está ejecutándose"
fi

echo ""

# Mostrar estadísticas de la cola
echo "📋 Estadísticas de la Cola ZIP:"
python manage.py shell -c "
from core.models import ZipRequest
from django.db.models import Count, Sum
from django.utils import timezone

# Contar por estado
stats = ZipRequest.objects.values('status').annotate(count=Count('id')).order_by('status')
print('Estado de solicitudes:')
for stat in stats:
    print(f'  {stat[\"status\"]}: {stat[\"count\"]}')

# Solicitudes pendientes
pending = ZipRequest.objects.filter(status='pending').count()
processing = ZipRequest.objects.filter(status='processing').count()
print(f'\\nCola activa: {pending} pendientes, {processing} procesando')

# Tamaño total de archivos
total_size = ZipRequest.objects.filter(status='completed', file_size__isnull=False).aggregate(
    total=Sum('file_size')
)['total'] or 0
total_mb = total_size / (1024 * 1024)
print(f'Almacenamiento usado: {total_mb:.2f} MB')

# Solicitudes recientes
recent = ZipRequest.objects.filter(
    created_at__gte=timezone.now() - timezone.timedelta(hours=24)
).count()
print(f'Solicitudes últimas 24h: {recent}')
"

echo ""

# Mostrar uso general del sistema
echo "💾 Uso del Sistema:"
echo "RAM total: $(free -h | awk '/^Mem:/ {print $2}' 2>/dev/null || echo 'N/A')"
echo "RAM usada: $(free -h | awk '/^Mem:/ {print $3}' 2>/dev/null || echo 'N/A')"
echo "RAM libre: $(free -h | awk '/^Mem:/ {print $7}' 2>/dev/null || echo 'N/A')"

echo ""

# Últimas líneas del log
if [ -f logs/zip_processor.log ]; then
    echo "📄 Últimas líneas del log:"
    tail -5 logs/zip_processor.log
else
    echo "📄 No hay logs disponibles"
fi

echo ""
echo "Para más detalles del log: tail -f logs/zip_processor.log"