#!/bin/bash

# Script para iniciar el procesador de cola ZIP en producción
# Uso: ./start_zip_processor.sh

echo "🚀 Iniciando procesador de cola ZIP para SAM..."

# Crear directorio de logs si no existe
mkdir -p logs

# Verificar que Django esté disponible
python manage.py check --quiet
if [ $? -ne 0 ]; then
    echo "❌ Error: Django no está configurado correctamente"
    exit 1
fi

# Limpiar solicitudes antiguas al iniciar
echo "🧹 Limpiando solicitudes ZIP antiguas..."
python manage.py cleanup_zip_files --older-than-hours 24

# Iniciar procesador en background
echo "📦 Iniciando procesador de cola ZIP..."
nohup python manage.py process_zip_queue \
    --check-interval 30 \
    --cleanup-old \
    >> logs/zip_processor.log 2>&1 &

# Guardar PID para poder detenerlo después
echo $! > logs/zip_processor.pid

echo "✅ Procesador de cola ZIP iniciado"
echo "📋 PID: $(cat logs/zip_processor.pid)"
echo "📄 Logs: logs/zip_processor.log"
echo ""
echo "Para detener el procesador:"
echo "  kill \$(cat logs/zip_processor.pid)"
echo ""
echo "Para ver logs en tiempo real:"
echo "  tail -f logs/zip_processor.log"