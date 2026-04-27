# SAM Metrología

Sistema de gestión metrológica para organismos de inspección bajo **ISO/IEC 17020:2012**.

Maneja equipos, calibraciones, mantenimientos, verificaciones intermedias y confirmación metrológica con análisis de intervalos (ILAC G-24:2022). Soporta múltiples empresas con planes de suscripción.

---

## Estado actual (Abril 2026)

| Indicador | Valor |
|-----------|-------|
| Score auditado | **8.3 / 10** |
| Tests | **1,883 pasando** — 0 fallando |
| Cobertura | **70%** |
| Última auditoría | `auditorias/AUDITORIA_INTEGRAL_2026-03-15.md` |
| Plan hacia 9/10 | `auditorias/PLAN_AUDITORIA_2026-04.md` |
| Versión | 2.0.0 |

---

## Documentación

Toda la documentación está en la carpeta [`📚-LEER-PRIMERO-DOCS/`](./📚-LEER-PRIMERO-DOCS/README.md).

| Si necesitas... | Abre... |
|-----------------|---------|
| Empezar en el proyecto | [`00-START-HERE.md`](./📚-LEER-PRIMERO-DOCS/00-START-HERE.md) |
| Instalación local | [`INICIO-AQUI.md`](./📚-LEER-PRIMERO-DOCS/INICIO-AQUI.md) |
| Entender la arquitectura | [`DEVELOPER-GUIDE.md`](./📚-LEER-PRIMERO-DOCS/DEVELOPER-GUIDE.md) |
| Ver cambios recientes | [`CHANGELOG.md`](./📚-LEER-PRIMERO-DOCS/CHANGELOG.md) |
| Hacer deploy en Render | [`DESPLEGAR-EN-RENDER.md`](./📚-LEER-PRIMERO-DOCS/DESPLEGAR-EN-RENDER.md) |
| Instrucciones para Claude Code | [`CLAUDE.md`](./CLAUDE.md) |

---

## Arranque rápido (desarrollo local)

```bash
# 1. Clonar y crear entorno virtual
git clone <repo>
cd sam-2
python -m venv venv
source venv/Scripts/activate   # Windows
# source venv/bin/activate     # Mac/Linux

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar base de datos
python manage.py migrate

# 4. Crear usuario administrador
python manage.py createsuperuser

# 5. Arrancar servidor
python manage.py runserver
```

La plataforma queda disponible en `http://127.0.0.1:8000`.

---

## Correr tests

```bash
# Todos los tests
python -m pytest

# Con reporte de cobertura
python -m pytest --cov=core --cov-report=term-missing

# Solo un módulo
python -m pytest tests/test_views/test_equipment.py -v
```

---

## Tecnologías

- **Backend:** Django 5.2 · Python 3.13
- **Base de datos:** PostgreSQL (producción) · SQLite (desarrollo)
- **Almacenamiento:** Cloudflare R2
- **Cache:** Redis (producción) · Memoria (desarrollo)
- **PDF:** WeasyPrint · ReportLab
- **Deploy:** Render.com

---

## Variables de entorno requeridas (producción)

```
SECRET_KEY
DATABASE_URL
AWS_ACCESS_KEY_ID          # Credenciales Cloudflare R2
AWS_SECRET_ACCESS_KEY
AWS_STORAGE_BUCKET_NAME
AWS_S3_REGION_NAME
RENDER_EXTERNAL_HOSTNAME
```

Ver guía completa en [`DESPLEGAR-EN-RENDER.md`](./📚-LEER-PRIMERO-DOCS/DESPLEGAR-EN-RENDER.md).

---

**Producción:** https://app.sammetrologia.com
**Soporte:** metrologiasam@gmail.com
