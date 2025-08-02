#!/bin/bash

# Este script se ejecuta al iniciar la aplicación en Render

# Ejecuta las migraciones de la base de datos (opcional, pero recomendado)
# Esto aplica cualquier cambio en el modelo de la base de datos
python manage.py migrate

# Recoge los archivos estáticos para la producción
python manage.py collectstatic --no-input

# Inicia la aplicación con Gunicorn, apuntando al archivo wsgi correcto
gunicorn proyecto_c.wsgi 
