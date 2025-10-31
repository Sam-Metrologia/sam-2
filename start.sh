#!/bin/bash

# Start script para Render - Inicia aplicacion Y procesador de cola ZIP

echo "🚀 Iniciando SAM Metrología..."

# PASO 1: Aplicar migraciones
echo "📦 Aplicando migraciones..."
python manage.py migrate --noinput

# PASO 2: Recolectar archivos estáticos
echo "📁 Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

# PASO 3: Iniciar procesador de cola ZIP en background
echo "🔄 Iniciando procesador de cola ZIP..."
mkdir -p logs

# Iniciar procesador ZIP en background
python manage.py process_zip_queue --check-interval 5 --cleanup-old >> logs/zip_processor.log 2>&1 &
ZIP_PROCESSOR_PID=$!
echo "✅ Procesador ZIP iniciado (PID: $ZIP_PROCESSOR_PID)"

# PASO 4: Iniciar servidor Gunicorn
echo "🌐 Iniciando servidor Gunicorn..."
# --workers: Numero de workers (recomendado 2-4 para Render free tier)
# --bind: Render usa la variable PORT automaticamente
# --timeout: Tiempo de espera para requests largos
gunicorn proyecto_c.wsgi:application \
    --workers 2 \
    --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --log-level info 
