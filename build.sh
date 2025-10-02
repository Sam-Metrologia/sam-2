#!/bin/bash

# Build script para Render - Ejecuta tareas de construccion

echo "Iniciando build..."

# Instalar dependencias (Render hace esto automaticamente, pero lo dejamos por claridad)
# pip install -r requirements.txt

# Ejecutar migraciones de base de datos
echo "Aplicando migraciones..."
python manage.py migrate --noinput

# Recoger archivos estaticos
echo "Recolectando archivos estaticos..."
python manage.py collectstatic --noinput

# Crear tabla de cache si no existe
echo "Verificando tabla de cache..."
python manage.py createcachetable sam_cache_table --noinput || true

echo "Build completado!"
