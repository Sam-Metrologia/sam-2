# Sistema de Auto-actualización de Documentación

## 📋 Descripción

Este sistema mantiene la documentación del proyecto actualizada automáticamente con datos reales del código (tests, coverage, auditorías, etc.)

## 🎯 Problema que Resuelve

Antes de este sistema, la documentación contenía datos desactualizados:
- ❌ "254/268 tests pasan" cuando realmente eran 738/738
- ❌ Referencias a auditorías antiguas
- ❌ Estadísticas de coverage incorrectas
- ❌ Fechas de actualización obsoletas

## ✅ Solución

Sistema de 2 componentes:

### 1. Script de Actualización (`update_documentation.py`)

Script Python que:
1. Ejecuta `pytest` para obtener conteo real de tests
2. Ejecuta `coverage` para obtener porcentaje real
3. Busca la auditoría más reciente
4. Actualiza archivos de documentación con datos reales

**Uso manual:**
```bash
python update_documentation.py
```

**Archivos que actualiza:**
- `📚-LEER-PRIMERO-DOCS/00-START-HERE.md`
- `📚-LEER-PRIMERO-DOCS/CLAUDE.md`
- `📚-LEER-PRIMERO-DOCS/DEVELOPER-GUIDE.md`
- `CLAUDE.md` (raíz)

### 2. Hook de Pre-commit (`.git/hooks/pre-commit`)

Hook de Git que ejecuta automáticamente el script antes de cada commit.

**Qué hace:**
1. Se activa automáticamente al hacer `git commit`
2. Ejecuta `update_documentation.py`
3. Agrega cambios de documentación al commit actual
4. Permite que el commit continúe

## 🚀 Instalación

El sistema ya está instalado y activo. No requiere configuración adicional.

## 🔧 Mantenimiento

### Actualizar manualmente

```bash
python update_documentation.py
```

### Deshabilitar temporalmente el hook

```bash
# Opción 1: Usar --no-verify
git commit --no-verify -m "mensaje"

# Opción 2: Renombrar el hook
mv .git/hooks/pre-commit .git/hooks/pre-commit.bak

# Para reactivarlo
mv .git/hooks/pre-commit.bak .git/hooks/pre-commit
```

### Agregar nuevos archivos al sistema

Editar `update_documentation.py` y agregar nuevos métodos:

```python
def update_my_new_file(self):
    """Actualizar mi nuevo archivo"""
    file_path = self.docs_dir / "MI_ARCHIVO.md"
    # ... lógica de actualización
```

## 📊 Datos que se Actualizan

| Dato | Fuente | Ejemplo |
|------|--------|---------|
| Total tests | `pytest --collect-only` | 738 tests |
| Tests pasando | `pytest -v` | 738 passed |
| Coverage | `pytest --cov` | 54.66% |
| Auditoría más reciente | `auditorias/*.md` | AUDITORIA_2026-01-10.md |
| Puntuación | Contenido de auditoría | 7.5/10 |
| Fecha actualización | Timestamp actual | 10 de Enero de 2026 |

## ⚠️ Notas Importantes

1. **El hook se ejecuta automáticamente** - No olvides que tus commits pueden tardar un poco más

2. **Coverage requiere tests** - Si los tests fallan, el coverage no se calculará

3. **Los cambios se agregan al commit** - Si la documentación se actualiza, los cambios se incluyen automáticamente

4. **No usar en CI/CD** - Este sistema es solo para desarrollo local

## 🐛 Troubleshooting

### El hook no se ejecuta

Verificar que sea ejecutable:
```bash
chmod +x .git/hooks/pre-commit
```

### Error al ejecutar el script

Verificar dependencias:
```bash
pip install pytest pytest-cov
```

### Datos no se actualizan

Ejecutar manualmente para ver errores:
```bash
python update_documentation.py
```

## 📝 Changelog

### 2026-01-10 - Creación inicial
- ✅ Script `update_documentation.py` creado
- ✅ Hook de pre-commit instalado
- ✅ Documentación actualizada con datos reales
- ✅ Sistema funcional y probado

## 🔮 Mejoras Futuras

- [ ] Agregar verificación de estilo de documentación (linting)
- [ ] Generar reporte de cambios en documentación
- [ ] Integrar con CI/CD para validar documentación
- [ ] Notificar cuando documentación está muy desactualizada

---

**Última Actualización:** 10 de Enero de 2026
