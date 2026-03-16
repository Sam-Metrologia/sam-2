# Documentación para Desarrolladores — SAM Metrología

Esta carpeta es el punto de entrada para cualquier desarrollador que trabaje en el proyecto.

---

## Orden de lectura

Lee los archivos en este orden:

| # | Archivo | Qué encontrarás | Tiempo |
|---|---------|-----------------|--------|
| 1 | **[DEVELOPER-GUIDE.md](./DEVELOPER-GUIDE.md)** | Arquitectura, áreas críticas, convenciones, checklist pre-commit | 40 min |
| 2 | **[DESPLEGAR-EN-RENDER.md](./DESPLEGAR-EN-RENDER.md)** | Cómo desplegar a producción paso a paso | 15 min |
| 3 | **[CHANGELOG.md](./CHANGELOG.md)** | Historial de cambios — leer antes de tocar algo, actualizar después de cada cambio | 5 min |

La documentación técnica general del proyecto está en **[CLAUDE.md](../CLAUDE.md)** (raíz del repositorio).

---

## Arranque rápido

```bash
# 1. Entorno virtual
python -m venv venv
source venv/Scripts/activate      # Windows
# source venv/bin/activate        # Mac/Linux

# 2. Dependencias
pip install -r requirements.txt

# 3. Base de datos
python manage.py migrate

# 4. Superusuario
python manage.py createsuperuser

# 5. Servidor
python manage.py runserver
```

---

## Comandos esenciales

```bash
# Tests (deben pasar siempre antes de hacer commit)
python -m pytest
python -m pytest --cov=core --cov-report=term-missing

# Verificar sistema
python manage.py check

# Migraciones
python manage.py makemigrations
python manage.py migrate

# Resincronizar permisos de usuarios (tras cambios en roles)
python manage.py setup_permissions

# Recalcular stats del dashboard
python manage.py recalcular_stats_empresas
```

---

## Estado actual

| Indicador | Valor |
|-----------|-------|
| Score auditado | **8.3 / 10** |
| Tests | **1,804 pasando** — 0 fallando |
| Cobertura | **70%** |
| Última auditoría | `../auditorias/AUDITORIA_INTEGRAL_2026-03-15.md` |
| Versión | 2.0.0 |

---

## Reglas que no se negocian

1. **Nunca hacer push directo a `main`** — hay auto-deploy activo a producción
2. **Siempre correr `python -m pytest` antes de commit** — los 1,804 tests deben pasar
3. **Actualizar CHANGELOG.md** con cada cambio que hagas
4. **No hardcodear `DEBUG=True`** ni exponer `SECRET_KEY`

---

## Estructura del proyecto

```
sam-2/
├── 📚-LEER-PRIMERO-DOCS/     ← ESTÁS AQUÍ
│   ├── README.md              (este archivo)
│   ├── DEVELOPER-GUIDE.md     (guía técnica completa)
│   ├── DESPLEGAR-EN-RENDER.md (guía de deploy)
│   └── CHANGELOG.md           (historial de cambios)
│
├── core/                      ← Código principal
│   ├── models/                (paquete de modelos — 28 modelos)
│   │   ├── __init__.py        (re-exporta todo)
│   │   ├── empresa.py
│   │   ├── equipment.py
│   │   ├── activities.py
│   │   └── ...
│   ├── views/                 (vistas organizadas por dominio)
│   ├── constants.py           (todas las constantes centralizadas)
│   ├── signals.py             (invalidación de caché)
│   └── ...
│
├── tests/                     ← Tests (pytest)
├── auditorias/                ← Auditorías y reportes históricos
├── docs/                      ← Documentación técnica adicional
├── CLAUDE.md                  ← Instrucciones para Claude Code
└── README.md                  ← Descripción pública del proyecto
```

---

**Producción:** https://app.sammetrologia.com
**Soporte:** metrologiasam@gmail.com
