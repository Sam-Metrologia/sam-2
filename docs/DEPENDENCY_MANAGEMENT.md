# Mantenimiento de Dependencias - SAM Metrologia

## OBLIGATORIO: Leer antes de cada sprint

Este documento es de cumplimiento obligatorio. Cada desarrollador debe verificar las fechas
de este documento al inicio de cada sprint y ejecutar las acciones correspondientes.

---

## Calendario de Mantenimiento

| Frecuencia | Accion | Responsable | Automatizado |
|---|---|---|---|
| **Semanal** | Escaneo CVEs (pip-audit) | GitHub Actions | Si - miercoles 9:00 AM COL |
| **Mensual** | Actualizar parches de seguridad | Desarrollador lider | No |
| **Trimestral** | Actualizar versiones menores | Equipo de desarrollo | No |
| **Anual** | Evaluar versiones mayores (Django, etc.) | Arquitecto / CTO | No |

---

## Registro de Actualizaciones

> **INSTRUCCION:** Cada vez que se actualicen dependencias, agregar una fila a esta tabla
> y actualizar la seccion "Proxima revision programada".

| Fecha | Paquetes actualizados | CVEs corregidos | Responsable | Tests OK |
|---|---|---|---|---|
| 2026-02-19 | Django 5.2.4->5.2.11, cryptography 45.0.5->46.0.5, Pillow 11.3.0->12.1.1, pypdf 5.8.0->6.7.1, urllib3 2.5.0->2.6.3, sqlparse 0.5.3->0.5.5, Werkzeug 3.1.3->3.1.6, weasyprint 66.0->68.1, fonttools 4.58.5->4.61.1, Brotli 1.1.0->1.2.0, cffi 1.17.1->2.0.0, tinycss2 1.4.0->1.5.1 | 32 CVEs | Claude Code | Si (1,023/1,023) |

---

## Proxima revision programada

- **Proxima revision mensual:** 2026-03-19
- **Proxima revision trimestral:** 2026-05-19
- **Ultima actualizacion de este documento:** 2026-02-19

> **INSTRUCCION:** Actualizar estas fechas cada vez que se complete una revision.

---

## Procedimiento de Actualizacion (paso a paso)

### 1. Escanear vulnerabilidades

```bash
pip install pip-audit
pip-audit
```

Si no hay CVEs, registrar en la tabla de arriba con "0 CVEs" y actualizar la fecha.

### 2. Actualizar paquetes con CVEs (si los hay)

```bash
# Ver que paquetes tienen CVEs
pip-audit

# Actualizar paquete especifico
pip install --upgrade <paquete>

# Ejemplo:
pip install --upgrade Django cryptography Pillow
```

### 3. Correr tests completos

```bash
python -m pytest
```

**TODOS los tests deben pasar (1,023+). Si algun test falla, NO proceder al paso 4.**

### 4. Actualizar requirements.txt

```bash
# Verificar version instalada
pip show <paquete> | grep Version

# Editar requirements.txt con la nueva version
# Ejemplo: Django==5.2.4 -> Django==5.2.11
```

### 5. Actualizar ESTE documento

- Agregar fila a la tabla "Registro de Actualizaciones"
- Actualizar "Proxima revision programada"
- Actualizar "Ultima actualizacion de este documento"

### 6. Commit y push

```bash
git add requirements.txt docs/DEPENDENCY_MANAGEMENT.md
git commit -m "security: actualizar dependencias - X CVEs corregidos"
git push
```

---

## Reglas criticas

1. **Nunca dejar pasar mas de 30 dias con un CVE critico (CVSS >= 9.0)**
2. **Nunca actualizar sin correr tests**
3. **Nunca actualizar requirements.txt sin haber instalado y probado primero**
4. **Siempre actualizar este documento despues de cada actualizacion**
5. **Si un test falla despues de actualizar, hacer rollback del paquete especifico**

---

## Automatizacion con GitHub Actions

El workflow `weekly-dependency-audit.yml` se ejecuta automaticamente:

- **Cuando:** Cada miercoles a las 9:00 AM (Colombia)
- **Que hace:** Ejecuta `pip-audit` sobre todas las dependencias
- **Si encuentra CVEs:** Crea un issue automatico con etiqueta `security`
- **Si esta limpio:** Solo registra en el log del workflow

Tambien se puede ejecutar manualmente desde GitHub > Actions > "Auditoria Semanal de Dependencias" > Run workflow.

---

## Paquetes criticos a monitorear

Estos paquetes son los mas importantes por impacto de seguridad:

| Paquete | Por que es critico | Version actual |
|---|---|---|
| Django | Framework principal, CVEs frecuentes | 5.2.11 |
| cryptography | Firma digital, certificados | 46.0.5 |
| Pillow | Procesamiento de imagenes, historial de CVEs | 12.1.1 |
| urllib3 | HTTP client, SSRF potencial | 2.6.3 |
| Werkzeug | Debug/dev server | 3.1.6 |
| psycopg2-binary | Driver PostgreSQL | 2.9.10 |
| gunicorn | Servidor WSGI produccion | 23.0.0 |

> **INSTRUCCION:** Actualizar la columna "Version actual" cada vez que se actualice un paquete.

---

**Ultima actualizacion de este documento:** 2026-02-19
