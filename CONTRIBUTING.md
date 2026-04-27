# Guía de Contribución — SAM Metrología

Gracias por contribuir a SAM Metrología. Este documento explica cómo trabajar en el proyecto de forma ordenada.

---

## Requisitos previos

- Python 3.13+
- Git
- Acceso al repositorio en GitHub

## Configuración del entorno local

```bash
git clone https://github.com/Sam-Metrologia/sam-2.git
cd sam-2
python -m venv venv
source venv/Scripts/activate   # Windows
pip install -r requirements.txt
pip install -r requirements_test.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

## Flujo de trabajo

### 1. Crear una rama

```bash
git checkout -b tipo/descripcion-corta
# Ejemplos:
# feat/intervalos-ilac-metodo-c
# fix/confirmacion-grafica-vacia
# refactor/forms-split-por-dominio
```

### 2. Hacer cambios

- Un cambio por rama — no mezcles features con fixes
- Seguir los patrones existentes del módulo que tocás
- No romper multi-tenancy: todo filtrado por `empresa`

### 3. Correr tests antes de hacer commit

```bash
python -m pytest                          # todos los tests
python -m pytest tests/test_views/ -v    # solo vistas
python -m pytest --cov=core --cov-report=term-missing  # con cobertura
```

Los tests deben pasar al 100%. Cobertura mínima: **70%**.

### 4. Commit

```bash
git add archivo1.py archivo2.html
git commit -m "tipo(módulo): descripción en español"
```

**Tipos de commit:**
| Tipo | Cuándo usarlo |
|------|--------------|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de bug |
| `refactor` | Reestructura sin cambio de comportamiento |
| `test` | Solo tests |
| `docs` | Solo documentación |
| `perf` | Mejora de rendimiento |

**Ejemplos:**
```
feat(confirmacion): soporte multi-magnitud con tabs
fix(equipos): fecha próxima calibración no se recalculaba al editar
test(prestamos): tests de aislamiento multi-tenant en dashboard
```

### 5. Pull Request

- Título corto (< 70 caracteres)
- Describe qué cambiaste y por qué
- Referencia el issue si aplica: `Closes #42`
- Asegúrate de que los tests pasen en CI

---

## Convenciones de código

### Python / Django

- Líneas máximo 120 caracteres
- Variables y funciones en `snake_case`, clases en `PascalCase`
- Sin comentarios obvios — solo documenta el **por qué**, no el qué
- Toda query filtrada por empresa: `Equipo.objects.filter(empresa=request.user.empresa)`
- Usar `get_object_or_404` con filtro de empresa para no-superusuarios

### Templates (HTML/Jinja)

- Tailwind CSS para estilos inline
- No JS inline en templates — mover a bloques `{% block scripts %}`
- Nombres de template: `core/modulo/accion.html`

### Tests

```python
@pytest.mark.django_db
class TestNombreClaro:
    def test_descripcion_del_caso(self, authenticated_client, equipo_factory):
        # Arrange
        ...
        # Act
        r = authenticated_client.get(url)
        # Assert
        assert r.status_code == 200
```

- Usar factories (`equipo_factory`, `user_factory`, `empresa_factory`) — no crear objetos a mano
- Mocks solo para I/O externo (storage, email, Redis)
- No tests con `return` en vez de `assert`

---

## Estructura del proyecto

Ver [`CLAUDE.md`](./CLAUDE.md) para la estructura completa y decisiones de arquitectura.

---

## Contacto

- **Soporte técnico:** metrologiasam@gmail.com
- **Issues:** [GitHub Issues](https://github.com/Sam-Metrologia/sam-2/issues)
