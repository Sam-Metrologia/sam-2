# Usa una imagen base de Python oficial, no la versión 'slim'.
# Esto asegura que tengamos todas las herramientas necesarias.
FROM python:3.13

# Establece el directorio de trabajo dentro del contenedor.
WORKDIR /opt/render/project/src

# Actualiza la lista de paquetes e instala las dependencias del sistema operativo que necesita WeasyPrint.
# Esta lista es más completa para cubrir todas las posibles dependencias.
RUN apt-get update && apt-get install -y \
    python3-dev \
    build-essential \
    libcairo2 \
    libpango-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    shared-mime-info \
    fonts-dejavu-core \
    fonts-noto-cjk \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia los archivos de requisitos e instala las dependencias de Python.
# Esto optimiza el caché de Docker.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de tu código fuente al contenedor.
COPY . .

# Expone el puerto en el que la aplicación Gunicorn se ejecutará.
EXPOSE 10000

# Asegúrate de que el script start.sh sea ejecutable
RUN chmod +x start.sh

# El comando principal para ejecutar la aplicación.
# Usa CMD en lugar de ENTRYPOINT para que se pueda sobrescribir fácilmente.
CMD ["./start.sh"]

