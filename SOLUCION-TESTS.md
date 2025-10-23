# Solución: Tests no se ejecutan en Render

## Problema Identificado

### 1. Tests Configurados con Pytest (No Django Test)
- Los tests están en la carpeta `tests/` con **268 tests** escritos para **pytest**
- Pytest configurado en `pytest.ini` con fixtures en `tests/conftest.py`
- Comando incorrecto ejecutado: `python manage.py test` (Django unittest) ❌
- Comando correcto: `pytest` ✅

### 2. Importación Circular en zip_functions.py (ARREGLADO)
**ERROR:**
```
WARNING: cannot import name 'solicitar_zip' from partially initialized module 'core.zip_functions'
(most likely due to a circular import)
```

**CAUSA:**
- `views/__init__.py` importaba `solicitar_zip` desde `zip_functions.py`
- `zip_functions.py` importaba `access_check` desde `views/base.py`
- Ciclo de importación circular durante la inicialización de Django

**SOLUCIÓN APLICADA:**
- Implementado lazy import wrapper para `access_check` en `zip_functions.py:20-28`
- El decorador `@access_check` ahora importa la función real solo al ejecutarse, no al cargarse el módulo
- ✅ Import exitoso verificado sin warnings

---

## Cómo Ejecutar Tests

### Localmente (Windows)
```bash
cd "C:\Users\LENOVO\OneDrive\Escritorio\sam-2"

# Ejecutar todos los tests
pytest

# Ejecutar con cobertura
pytest --cov=core --cov-report=html

# Ejecutar tests específicos
pytest tests/test_models/           # Solo tests de modelos
pytest tests/test_views/            # Solo tests de views
pytest tests/test_integration/      # Solo tests de integración

# Ejecutar en paralelo (más rápido)
pytest -n auto
```

### En GitHub Actions (Automático)
Los tests se ejecutan automáticamente en **cada push** y **pull request** a las ramas `main` y `develop`:

1. Ve a GitHub: https://github.com/Sam-Metrologia/sam-2
2. Pestaña **"Actions"**
3. Verás el workflow **"Tests y Cobertura"**
4. Se ejecuta automáticamente con **pytest** (configurado correctamente)

**Archivo:** `.github/workflows/tests.yml`
```yaml
- name: 🧪 Ejecutar tests
  run: |
    pytest \
      --cov=core \
      --cov-report=xml \
      --cov-report=term-missing \
      --verbose \
      -n auto
```

### En Render (Manual)
Si necesitas ejecutar tests en Render manualmente:

**❌ INCORRECTO:**
```bash
python manage.py test  # Encuentra 0 tests (usa unittest, no pytest)
```

**✅ CORRECTO:**
```bash
pytest                 # Encuentra 268 tests
```

---

## Estado Actual

### ✅ RESUELTO
- [x] Importación circular en `zip_functions.py` arreglada
- [x] Tests locales funcionan correctamente (268 tests encontrados)
- [x] GitHub Actions configurado correctamente con pytest
- [x] Workflow de tests se ejecuta automáticamente

### 📋 Tests Disponibles
```
268 tests totales distribuidos en:

tests/test_models/          # Tests de modelos (Empresa, Equipo, Usuario)
tests/test_views/           # Tests de vistas (dashboard, equipment, companies)
tests/test_services/        # Tests de servicios (storage, validators)
tests/test_integration/     # Tests de integración (workflows completos)
```

### 🔧 Configuración
- **pytest.ini**: Configuración de pytest con opciones de cobertura
- **tests/conftest.py**: Fixtures globales (authenticated_client, factories, etc.)
- **tests/factories.py**: Factory Boy para crear objetos de test
- **.github/workflows/tests.yml**: CI/CD con GitHub Actions

---

## Verificación de la Corrección

### Test de Importación Circular (Arreglado)
```bash
python -c "import django; django.setup(); from core.zip_functions import solicitar_zip; print('OK')"
```
**Resultado:** ✅ Import successful - No circular import error

### Test de Pytest (Funciona)
```bash
pytest --collect-only
```
**Resultado:** ✅ collected 268 items

---

## Comando de GitHub Actions

El workflow de tests en GitHub está correctamente configurado y se ejecuta automáticamente.

**NO es necesario** ejecutar tests manualmente en Render porque:
1. GitHub Actions ejecuta los tests en cada push
2. Render solo necesita ejecutar la aplicación, no los tests
3. Los tests se verifican ANTES del deploy

---

## Resumen

| Aspecto | Estado | Notas |
|---------|--------|-------|
| Tests locales | ✅ Funciona | 268 tests con pytest |
| GitHub Actions | ✅ Funciona | Workflow automático configurado |
| Importación circular | ✅ Arreglado | Lazy import implementado |
| Comando correcto | ✅ Documentado | Usar `pytest`, no `manage.py test` |

---

**Fecha de resolución:** 23 de Octubre de 2025
**Problemas resueltos:** 2 (Importación circular + Comando de tests incorrecto)
