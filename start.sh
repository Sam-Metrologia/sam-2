#!/bin/bash

# Start script para Render - Solo inicia la aplicacion

echo "Iniciando servidor Gunicorn..."

# Inicia la aplicación con Gunicorn
# --workers: Numero de workers (recomendado 2-4 para Render free tier)
# --bind: Render usa la variable PORT automaticamente
# --timeout: Tiempo de espera para requests largos
gunicorn proyecto_c.wsgi:application \
    --workers 2 \
    --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --log-level info 
