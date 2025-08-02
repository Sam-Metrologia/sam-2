#!/bin/bash

# Este script instala las dependencias del sistema necesarias para WeasyPrint en el servidor de Render.
# Weasyprint requiere librerías como Pango, Cairo y GDK-Pixbuf, que no se instalan con pip.

# Actualizar la lista de paquetes
apt-get update

# Instalar las librerías de sistema necesarias para WeasyPrint
apt-get install -y \
    libpango-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    python3-dev \
    build-essential
