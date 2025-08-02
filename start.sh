#!/bin/bash
export PYTHONPATH=/opt/render/project/src/
gunicorn proyecto_c.wsgi:application --log-file -