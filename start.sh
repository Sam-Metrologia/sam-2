#!/bin/bash

# Start script para Render - Servicio Web Principal
# NOTA: El procesador ZIP corre como worker separado definido en render.yaml

echo "🚀 Iniciando SAM Metrología..."

# PASO 1: Aplicar migraciones
echo "📦 Aplicando migraciones..."
python manage.py migrate --noinput

# PASO 2: Recolectar archivos estáticos
echo "📁 Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

# PASO 3: Iniciar servidor Gunicorn
echo "🌐 Iniciando servidor Gunicorn..."
# --workers: Numero de workers (recomendado 2-4 para Render free tier)
# --bind: Render usa la variable PORT automaticamente
# --timeout: Tiempo de espera para requests largos
gunicorn proyecto_c.wsgi:application \
    --workers 2 \
    --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --log-level info 
