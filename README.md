# 🔬 SAM - Sistema de Administración Metrológica

> **⚠️ SISTEMA EN PRODUCCIÓN** - Este sistema está activamente desplegado y en uso en producción en **Render**. Cualquier cambio debe ser probado exhaustivamente en desarrollo antes de hacer push a `main`. Ver [DEVELOPER-GUIDE.md](./DEVELOPER-GUIDE.md) para guía detallada.

> **✅ ACTUALIZACIÓN 19 NOV 2025** - Hotfix crítico aplicado: Panel de Decisiones - TypeError Decimal/Float corregido. Sistema estable y verificado. Ver `auditorias/HOTFIX_APLICADO_2025-11-16.md` para detalles.

[![Python](https://img.shields.io/badge/python-3.11.11-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-5.2.4-green.svg)](https://www.djangoproject.com/)
[![Production](https://img.shields.io/badge/status-PRODUCTION-success.svg)](https://app.sammetrologia.com)
[![Deploy](https://img.shields.io/badge/platform-Render-blueviolet.svg)](https://render.com)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)

Sistema integral de gestión de equipos de metrología, calibraciones, mantenimientos y certificados para empresas multi-tenant.

## 🚨 Enlaces Importantes

- **Producción**: https://app.sammetrologia.com
- **Dashboard Render**: [Render Dashboard](https://dashboard.render.com)
- **Repositorio**: https://github.com/Sam-Metrologia/sam-2
- **Guía de Desarrollo**: [DEVELOPER-GUIDE.md](./DEVELOPER-GUIDE.md) ⭐ **LEER PRIMERO**
- **Guía de Despliegue**: [DESPLEGAR-EN-RENDER.md](./DESPLEGAR-EN-RENDER.md)

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Requisitos](#-requisitos)
- [Instalación](#-instalación)
- [Testing](#-testing)
- [Desarrollo](#-desarrollo)
- [Despliegue](#-despliegue)
- [Arquitectura](#-arquitectura)

## ✨ Características

- 🏢 **Multi-tenancy** - Soporte para múltiples empresas con aislamiento de datos
- 📊 **Gestión de Equipos** - CRUD completo de equipos de metrología
- 🔧 **Calibraciones y Mantenimientos** - Programación y seguimiento automático
- 📄 **Generación de Certificados** - PDFs automáticos con plantillas personalizables
- 📦 **Exportación Masiva** - ZIPs con certificados y documentos
- 🔔 **Notificaciones** - Alertas automáticas de vencimientos
- 📈 **Dashboard Analítico** - Métricas y gráficas en tiempo real
- 👥 **Gestión de Usuarios** - Roles y permisos granulares
- ☁️ **Almacenamiento S3** - Archivos en la nube (desarrollo y producción)
- 🔒 **Seguridad Avanzada** - Validación de archivos, autenticación robusta

## 🛠️ Requisitos

- Python 3.13+
- PostgreSQL 15+ (producción) o SQLite (desarrollo)
- Redis (opcional, para caché)
- AWS S3 (para archivos en producción)

## 📦 Instalación

### 1. Clonar repositorio

```bash
git clone https://gitlab.com/metrologiasam-group/SAM.git
cd SAM
```

### 2. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Crear archivo `.env` en la raíz:

```env
# Desarrollo
SECRET_KEY=your-secret-key-here
DEBUG_VALUE=True
DATABASE_URL=sqlite:///db.sqlite3

# Producción (ejemplo)
# DATABASE_URL=postgresql://user:pass@localhost:5432/sam_db
# AWS_ACCESS_KEY_ID=your-aws-key
# AWS_SECRET_ACCESS_KEY=your-aws-secret
# AWS_STORAGE_BUCKET_NAME=your-bucket-name
```

### 5. Aplicar migraciones

```bash
python manage.py migrate
```

### 6. Crear superusuario

```bash
python manage.py createsuperuser
```

### 7. Ejecutar servidor

```bash
python manage.py runserver
```

Visitar: http://localhost:8000

## 🧪 Testing

SAM cuenta con un sistema de testing robusto con **94% de cobertura** (158/168 tests pasando).

### Ejecutar todos los tests

```bash
# Linux/Mac
./run_tests.sh

# Windows
run_tests.bat

# O directamente con pytest
pytest
```

### Opciones avanzadas

```bash
# Solo tests rápidos
./run_tests.sh --fast

# Solo tests unitarios
./run_tests.sh --unit

# Tests en paralelo
./run_tests.sh --parallel

# Con reporte HTML
./run_tests.sh --html

# Tests de servicios solamente
./run_tests.sh --services
```

### Estructura de Tests

```
tests/
├── conftest.py                    # Fixtures globales
├── factories.py                   # Factory Boy para datos de prueba
├── test_models/                   # Tests de modelos (23 tests)
├── test_views/                    # Tests de vistas (60 tests)
├── test_integration/              # Tests de integración (10 tests)
└── test_services/                 # Tests de servicios (85 tests)
    ├── test_storage_validators.py
    ├── test_file_validators.py
    └── test_equipment_services.py
```

### Cobertura de Tests

| Categoría | Tests | Cobertura |
|-----------|-------|-----------|
| Modelos | 23 | ~80% |
| Vistas | 60 | ~60% |
| Servicios | 85 | ~72% |
| Integración | 10 | ~40% |
| **TOTAL** | **168** | **~70%** |

## 💻 Desarrollo

### Pre-commit Hooks

Instalar hooks para validación automática antes de commits:

```bash
pip install pre-commit
pre-commit install
```

Los hooks ejecutan:
- ✅ Formateo con Black
- ✅ Ordenamiento de imports (isort)
- ✅ Lint con flake8
- ✅ Validaciones de seguridad (Bandit)
- ✅ Django checks
- ✅ Tests rápidos

### Comandos útiles

```bash
# Crear migración
python manage.py makemigrations

# Ver SQL de migración
python manage.py sqlmigrate core 0001

# Verificar proyecto
python manage.py check

# Colectar estáticos
python manage.py collectstatic

# Shell de Django
python manage.py shell

# Crear datos de prueba
python manage.py generar_datos_prueba
```

## 🚀 Despliegue

> **⚠️ IMPORTANTE**: El sistema YA ESTÁ DESPLEGADO en producción en **Render**. Ver [DESPLEGAR-EN-RENDER.md](./DESPLEGAR-EN-RENDER.md) para detalles completos del deployment.

### Estado Actual de Producción

- **Plataforma**: Render (https://app.sammetrologia.com)
- **Auto-Deploy**: ✅ Habilitado desde rama `main`
- **Base de Datos**: PostgreSQL 15 (Render Managed)
- **Storage**: AWS S3 (archivos y estáticos)
- **Worker**: Background worker para procesamiento de ZIPs
- **Cron Jobs**: 6 tareas programadas activas

### Proceso de Deploy Automático

Cada vez que haces `git push` a la rama `main`, Render automáticamente:

1. Detecta el cambio en GitHub
2. Ejecuta `./build.sh` (instala dependencias, migra DB, collectstatic)
3. Inicia servidor con `./start.sh` (Gunicorn)
4. Monitorea salud del servicio

**⚠️ PRECAUCIÓN**: Todo cambio en `main` se despliega automáticamente a producción. Prueba exhaustivamente en desarrollo primero.

### Variables de Entorno en Producción

Configuradas en Render Dashboard:

```env
# Seguridad
SECRET_KEY=***
DEBUG_VALUE=False

# Base de Datos
DATABASE_URL=postgresql://***  (Generado por Render)

# AWS S3 (REQUERIDO)
AWS_ACCESS_KEY_ID=***
AWS_SECRET_ACCESS_KEY=***
AWS_STORAGE_BUCKET_NAME=sam-metrologia-files
AWS_S3_REGION_NAME=us-east-2

# Email (Opcional)
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=metrologiasam@gmail.com
EMAIL_HOST_PASSWORD=***
```

Ver [DESPLEGAR-EN-RENDER.md](./DESPLEGAR-EN-RENDER.md) para guía completa de deployment y troubleshooting.

## 🏗️ Arquitectura

### Stack Tecnológico

- **Backend**: Django 5.2.4 + Python 3.13
- **Base de Datos**: PostgreSQL 15 (producción) / SQLite (desarrollo)
- **Caché**: Redis (opcional)
- **Storage**: AWS S3
- **Servidor**: Gunicorn + WhiteNoise
- **Testing**: Pytest + Factory Boy
- **CI/CD**: GitHub Actions

### Estructura del Proyecto

```
sam-2/
├── core/                          # App principal
│   ├── models.py                  # Modelos de datos
│   ├── views/                     # Vistas organizadas por función
│   ├── services.py                # Lógica de negocio
│   ├── file_validators.py         # Validación de archivos
│   ├── storage_validators.py      # Validación de límites
│   └── forms.py                   # Formularios Django
├── proyecto_c/                    # Configuración Django
│   ├── settings.py                # Settings con detección de entorno
│   ├── urls.py                    # URLs principales
│   └── wsgi.py                    # WSGI para producción
├── tests/                         # Suite de testing
├── templates/                     # Templates globales
├── static/                        # Archivos estáticos
├── media/                         # Uploads (solo desarrollo)
└── logs/                          # Logs de aplicación
```

## 📞 Soporte y Contacto

- **Email**: metrologiasam@gmail.com
- **Documentación Técnica**: Ver [DEVELOPER-GUIDE.md](./DEVELOPER-GUIDE.md)
- **Guía de Despliegue**: Ver [DESPLEGAR-EN-RENDER.md](./DESPLEGAR-EN-RENDER.md)

---

**Desarrollado por SAM Metrología** - Sistema Propietario © 2024-2025
