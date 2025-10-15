# 🔬 SAM - Sistema de Administración Metrológica

[![Tests](https://github.com/tu-usuario/sam/actions/workflows/tests.yml/badge.svg)](https://github.com/tu-usuario/sam/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen.svg)](https://github.com/tu-usuario/sam)
[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-5.2.4-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)

Sistema integral de gestión de equipos de metrología, calibraciones, mantenimientos y certificados para empresas multi-tenant.

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

### Producción con Render/Railway/Heroku

1. **Configurar variables de entorno:**
   ```
   SECRET_KEY=production-secret-key
   DEBUG_VALUE=False
   DATABASE_URL=postgresql://...
   AWS_ACCESS_KEY_ID=...
   AWS_SECRET_ACCESS_KEY=...
   AWS_STORAGE_BUCKET_NAME=...
   ```

2. **Build command:**
   ```bash
   pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput
   ```

3. **Start command:**
   ```bash
   gunicorn proyecto_c.wsgi:application
   ```

### CI/CD con GitHub Actions

El proyecto incluye workflow de GitHub Actions (`.github/workflows/tests.yml`) que ejecuta automáticamente:

- ✅ Tests completos con PostgreSQL
- ✅ Verificación de cobertura
- ✅ Lint y formateo
- ✅ Análisis de seguridad
- ✅ Upload de reportes a Codecov

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

## Getting started

To make it easy for you to get started with GitLab, here's a list of recommended next steps.

Already a pro? Just edit this README.md and make it your own. Want to make it easy? [Use the template at the bottom](#editing-this-readme)!

## Add your files

- [ ] [Create](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#create-a-file) or [upload](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#upload-a-file) files
- [ ] [Add files using the command line](https://docs.gitlab.com/topics/git/add_files/#add-files-to-a-git-repository) or push an existing Git repository with the following command:

```
cd existing_repo
git remote add origin https://gitlab.com/metrologiasam-group/SAM.git
git branch -M main
git push -uf origin main
```

## Integrate with your tools

- [ ] [Set up project integrations](https://gitlab.com/metrologiasam-group/SAM/-/settings/integrations)

## Collaborate with your team

- [ ] [Invite team members and collaborators](https://docs.gitlab.com/ee/user/project/members/)
- [ ] [Create a new merge request](https://docs.gitlab.com/ee/user/project/merge_requests/creating_merge_requests.html)
- [ ] [Automatically close issues from merge requests](https://docs.gitlab.com/ee/user/project/issues/managing_issues.html#closing-issues-automatically)
- [ ] [Enable merge request approvals](https://docs.gitlab.com/ee/user/project/merge_requests/approvals/)
- [ ] [Set auto-merge](https://docs.gitlab.com/user/project/merge_requests/auto_merge/)

## Test and Deploy

Use the built-in continuous integration in GitLab.

- [ ] [Get started with GitLab CI/CD](https://docs.gitlab.com/ee/ci/quick_start/)
- [ ] [Analyze your code for known vulnerabilities with Static Application Security Testing (SAST)](https://docs.gitlab.com/ee/user/application_security/sast/)
- [ ] [Deploy to Kubernetes, Amazon EC2, or Amazon ECS using Auto Deploy](https://docs.gitlab.com/ee/topics/autodevops/requirements.html)
- [ ] [Use pull-based deployments for improved Kubernetes management](https://docs.gitlab.com/ee/user/clusters/agent/)
- [ ] [Set up protected environments](https://docs.gitlab.com/ee/ci/environments/protected_environments.html)

***

# Editing this README

When you're ready to make this README your own, just edit this file and use the handy template below (or feel free to structure it however you want - this is just a starting point!). Thanks to [makeareadme.com](https://www.makeareadme.com/) for this template.

## Suggestions for a good README

Every project is different, so consider which of these sections apply to yours. The sections used in the template are suggestions for most open source projects. Also keep in mind that while a README can be too long and detailed, too long is better than too short. If you think your README is too long, consider utilizing another form of documentation rather than cutting out information.

## Name
Choose a self-explaining name for your project.

## Description
Let people know what your project can do specifically. Provide context and add a link to any reference visitors might be unfamiliar with. A list of Features or a Background subsection can also be added here. If there are alternatives to your project, this is a good place to list differentiating factors.

## Badges
On some READMEs, you may see small images that convey metadata, such as whether or not all the tests are passing for the project. You can use Shields to add some to your README. Many services also have instructions for adding a badge.

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation
Within a particular ecosystem, there may be a common way of installing things, such as using Yarn, NuGet, or Homebrew. However, consider the possibility that whoever is reading your README is a novice and would like more guidance. Listing specific steps helps remove ambiguity and gets people to using your project as quickly as possible. If it only runs in a specific context like a particular programming language version or operating system or has dependencies that have to be installed manually, also add a Requirements subsection.

## Usage
Use examples liberally, and show the expected output if you can. It's helpful to have inline the smallest example of usage that you can demonstrate, while providing links to more sophisticated examples if they are too long to reasonably include in the README.

## Support
Tell people where they can go to for help. It can be any combination of an issue tracker, a chat room, an email address, etc.

## Roadmap
If you have ideas for releases in the future, it is a good idea to list them in the README.

## Contributing
State if you are open to contributions and what your requirements are for accepting them.

For people who want to make changes to your project, it's helpful to have some documentation on how to get started. Perhaps there is a script that they should run or some environment variables that they need to set. Make these steps explicit. These instructions could also be useful to your future self.

You can also document commands to lint the code or run tests. These steps help to ensure high code quality and reduce the likelihood that the changes inadvertently break something. Having instructions for running tests is especially helpful if it requires external setup, such as starting a Selenium server for testing in a browser.

## Authors and acknowledgment
Show your appreciation to those who have contributed to the project.

## License
For open source projects, say how it is licensed.

## Project status
If you have run out of energy or time for your project, put a note at the top of the README saying that development has slowed down or stopped completely. Someone may choose to fork your project or volunteer to step in as a maintainer or owner, allowing your project to keep going. You can also make an explicit request for maintainers.
