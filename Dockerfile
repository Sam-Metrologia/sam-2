# Usa una imagen base de Python oficial.
# Te recomiendo usar una versión específica para asegurar la estabilidad.
FROM python:3.13.4-slim

# Instala las dependencias del sistema operativo que necesita WeasyPrint.
# Esto se hace con permisos de root dentro del contenedor de Docker.
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    python3-dev \
    build-essential \
    libglib2.0-0 \
    libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Establece el directorio de trabajo dentro del contenedor.
WORKDIR /opt/render/project/src

# Copia los archivos de requisitos e instala las dependencias de Python.
# Esto optimiza el caché de Docker para que no tenga que reinstalar todo en cada cambio de código.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copia el resto de tu código fuente al contenedor.
COPY . .

# Expone el puerto en el que la aplicación Gunicorn se ejecutará.
EXPOSE 10000

# Asegúrate de que el script start.sh sea ejecutable
RUN chmod +x start.sh

# El comando principal para ejecutar la aplicación.
# Usa CMD en lugar de ENTRYPOINT para que se pueda sobrescribir fácilmente.
CMD ["./start.sh"]
