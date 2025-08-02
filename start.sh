#!/bin/bash

# Exporta el PYTHONPATH para que Python pueda encontrar los módulos de tu proyecto.
export PYTHONPATH=/opt/render/project/src/

# Inicia Gunicorn usando el módulo de Python.
# Esto asegura que el comando 'gunicorn' se encuentre, sin importar la configuración del PATH.
python -m gunicorn proyecto_c.wsgi:application --log-file -
