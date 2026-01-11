# 📘 Guía de Desarrollo - SAM Metrología

> **⚠️ LECTURA OBLIGATORIA PARA DESARROLLADORES**
>
> Este sistema está **ACTIVAMENTE EN PRODUCCIÓN** en https://app.sammetrologia.com. Cualquier cambio que hagas puede afectar a usuarios reales inmediatamente.

## 📁 IMPORTANTE: Carpetas de Organización

### 📂 `auditorias/` - Auditorías y Reportes de Progreso

**TODOS los documentos de auditorías, evaluaciones y reportes de progreso van aquí.**

```
auditorias/
├── README.md                                              # Guía de la carpeta
├── AUDITORIA_EXHAUSTIVA_NIVEL_9_2026-01-10.md            # Auditoría exhaustiva nivel 9
├── AUDITORIA_INTEGRAL_CERO_CONFIANZA_2026-01-10.md       # Auditoría cero confianza
├── LIMPIEZA_COMPLETADA_2025-12-05.md                      # Limpieza de código fase 1
├── CAMBIOS_CRITICOS_2025-10-24.md                         # Correcciones de seguridad
├── PROGRESO_FASE1_YYYYMMDD.md                             # Reportes de progreso semanales
├── PROGRESO_FASE2_YYYYMMDD.md
└── ... (análisis técnicos, métricas, etc.)
```

**¿Qué documentar aquí?**
- ✅ Auditorías de código completas
- ✅ Auditorías de seguridad
- ✅ Planes de implementación de mejoras
- ✅ Reportes de progreso semanales/mensuales
- ✅ Análisis de deuda técnica
- ✅ Métricas de performance
- ✅ Listas de TODOs, bugs encontrados

**Antes de iniciar cualquier mejora grande:** Leer `auditorias/AUDITORIA_EXHAUSTIVA_NIVEL_9_2026-01-10.md`

---

### 📚 `documentacion/` - Documentación Técnica

**TODA la documentación técnica del proyecto va aquí.**

```
documentacion/
├── README.md                              # Guía de documentación
├── DEVELOPER-GUIDE.md                     # Esta guía (copia)
├── README.md (proyecto)                   # Setup e instalación
├── DESPLEGAR-EN-RENDER.md                 # Guía de deployment
├── CLAUDE.md                              # Guía para Claude Code
├── CHECKLIST_SISTEMA_PAGOS.md             # Checklists
└── FIX_ZIP_DUPLICADOS.md                  # Fixes documentados
```

**¿Qué documentar aquí?**
- ✅ Guías de desarrollo y workflow
- ✅ Documentación de deployment
- ✅ Guías de instalación y setup
- ✅ Checklists de procedimientos
- ✅ Fixes y soluciones documentadas
- ✅ Documentación de APIs (cuando exista)

**Nota:** Los archivos originales en la raíz del proyecto se mantienen para compatibilidad, pero las copias en `documentacion/` son la fuente de verdad.

---

### 🔄 Relación entre Carpetas

```
┌─────────────────────────────────────────────────────┐
│  AUDITORÍAS identifican problemas y mejoras         │
│  ↓                                                   │
│  PLAN DE IMPLEMENTACIÓN detalla cómo solucionarlos │
│  ↓                                                   │
│  DESARROLLO implementa las soluciones               │
│  ↓                                                   │
│  DOCUMENTACIÓN se actualiza con los cambios         │
│  ↓                                                   │
│  REPORTES DE PROGRESO documentan avances            │
└─────────────────────────────────────────────────────┘
```

**Ejemplo de flujo:**
1. Auditoría detecta: "`models.py` de 3,142 líneas" → `auditorias/AUDITORIA_XXX.md`
2. Plan creado: "Dividir en 8 archivos" → `auditorias/PLAN_IMPLEMENTACION_XXX.md`
3. Refactorización implementada → Código en `core/models/`
4. Documentación actualizada → `documentacion/DEVELOPER-GUIDE.md`
5. Progreso reportado → `auditorias/PROGRESO_FASE1_XXX.md`

---

## 🚨 Avisos Críticos

### ⚡ Auto-Deploy Activo

```
┌─────────────────────────────────────────────────────┐
│  ⚠️  PELIGRO: AUTO-DEPLOY DESDE RAMA main         │
│                                                     │
│  git push origin main  →  Producción en 5-10 min  │
│                                                     │
│  NO HAGAS PUSH A main SIN PRUEBAS EXHAUSTIVAS     │
└─────────────────────────────────────────────────────┘
```

**Cada `git push` a `main` automáticamente**:
1. Dispara deploy en Render
2. Instala dependencias (`./build.sh`)
3. Aplica migraciones de DB (`python manage.py migrate`)
4. Colecta estáticos (`collectstatic`)
5. Reinicia servidor con nuevo código

**NO HAY APROBACIONES MANUALES. EL CÓDIGO VA DIRECTO A PRODUCCIÓN.**

### 🔴 Áreas Críticas - MÁXIMA PRECAUCIÓN

Estas áreas del código tienen impacto directo en funcionalidad crítica de producción:

#### 1. **Modelos Financieros** (`core/models.py`)
```python
# CRITICAL: Usar SIEMPRE Decimal para cálculos financieros
# ❌ MAL:  return float(self.valor) / 12
# ✅ BIEN: return self.valor / Decimal('12')

class Empresa(models.Model):
    def calcular_tarifa_mensual_equivalente(self):
        # Siempre retorna Decimal
        return self.valor_pago_acordado / Decimal(str(meses))
```

**Bug Histórico**: Uso de `float` causó errores de tipo en panel de decisiones (Nov 2024). Siempre usar `Decimal` en finanzas.

#### 2. **Cálculo de Fechas de Actividades** (`core/models.py`)
```python
# CRITICAL: Usar nombres correctos de campos
# ❌ MAL:  self.ima_comprobacion = today
# ✅ BIEN: self.proxima_comprobacion = today

class Equipo(models.Model):
    def calcular_proxima_comprobacion(self):
        # Usar relativedelta para meses exactos
        self.proxima_comprobacion = fecha_base + relativedelta(months=self.frecuencia_comprobacion)
```

**Bug Histórico**: Typos `ima_comprobacion` vs `proxima_comprobacion` causaron que fechas no se calcularan (Nov 2024).

#### 3. **Procesamiento de ZIPs** (`core/views/exportar_equipos_zip.py`)
```python
# CRITICAL: Sistema de cola implementado por límites de RAM
# - Máximo 35 equipos por ZIP
# - Procesamiento FIFO con modelo ZipRequest
# - NO generar ZIPs síncronos de >35 equipos
```

**Límite de RAM**: Render Free tier = 512MB. ZIPs grandes causan OOM kills.

#### 4. **Panel de Decisiones** (`core/views/panel_decisiones.py`)
```python
# CRITICAL: JSON serialization de Decimals
# ✅ Usar helper function para json.dumps()

def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    # ... recursivo para dicts/lists

# Siempre:
json.dumps(decimal_to_float(financial_data))
```

**Bug Histórico**: `TypeError: Object of type Decimal is not JSON serializable` (Nov 2024).

#### 5. **Configuración de Entorno** (`proyecto_c/settings.py`)
```python
# CRITICAL: Detección automática de entorno
IS_PRODUCTION = os.getenv('RENDER_EXTERNAL_HOSTNAME') is not None

# NO cambiar lógica de detección
# NO hardcodear DEBUG=True en producción
# NO exponer SECRET_KEY
```

---

## 🏗️ Arquitectura del Sistema

### Stack Tecnológico en Producción

```
┌─────────────────────────────────────────────────────────┐
│                  Usuario (Browser)                      │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS
┌────────────────────▼────────────────────────────────────┐
│              Render Web Service                         │
│  • Gunicorn (WSGI)                                      │
│  • Django 5.2.4 + Python 3.11.11                        │
│  • 512 MB RAM (Free Tier)                               │
└─────┬──────────────────────────────────┬────────────────┘
      │                                   │
      │ DATABASE_URL                      │ AWS SDK
      │                                   │
┌─────▼─────────────────┐     ┌──────────▼──────────────┐
│ PostgreSQL 15         │     │  AWS S3 Bucket          │
│ (Render Managed)      │     │  • Archivos estáticos   │
│ • Free tier: 1 GB     │     │  • Uploads de usuarios  │
└───────────────────────┘     │  • Certificados PDF     │
                              │  • ZIPs generados       │
┌─────────────────────────┐   └─────────────────────────┘
│ Render Background Worker│
│ • Procesador de ZIPs    │
│ • Usa misma imagen      │
└─────────────────────────┘

┌─────────────────────────┐
│ 6 Cron Jobs (Render)    │
│ • Notificaciones        │
│ • Limpieza              │
│ • Mantenimiento         │
└─────────────────────────┘
```

### Estructura de Código

```
sam-2/
├── 🔴 core/                        # App principal (CRÍTICO)
│   ├── 🔴 models.py                # Modelos de negocio (PELIGRO: Finanzas y fechas)
│   ├── views/
│   │   ├── 🔴 panel_decisiones.py  # Dashboard financiero (Decimals!)
│   │   ├── exportar_equipos_zip.py # Sistema de cola ZIP
│   │   ├── equipos.py              # CRUD equipos
│   │   ├── calibraciones.py        # Gestión calibraciones
│   │   └── ...
│   ├── services.py                 # Lógica de negocio
│   ├── file_validators.py          # Validación de uploads
│   ├── storage_validators.py       # Límites de storage
│   └── forms.py                    # Formularios
│
├── 🔴 proyecto_c/                  # Configuración Django (CRÍTICO)
│   ├── 🔴 settings.py              # Settings con detección de entorno
│   ├── urls.py
│   └── wsgi.py
│
├── templates/                      # Templates globales
├── static/                         # Assets frontend
├── media/                          # Uploads locales (solo dev)
├── logs/                           # Logs de aplicación
│   ├── sam_info.log               # Logs generales
│   ├── sam_errors.log             # Errores
│   ├── sam_security.log           # Eventos de seguridad
│   └── zip_processor.log          # Procesador de ZIPs
│
├── 🔴 build.sh                     # Script de build (Render)
├── 🔴 start.sh                     # Script de inicio (Render)
├── 🔴 render.yaml                  # Configuración de Render
├── requirements.txt                # Dependencias Python
├── manage.py                       # Django CLI
│
├── 📘 README.md                    # Overview del proyecto
├── 📘 DEVELOPER-GUIDE.md           # Esta guía (LEER PRIMERO)
├── 📘 CLAUDE.md                    # Guía para Claude Code
└── 📘 DESPLEGAR-EN-RENDER.md       # Guía de deployment
```

---

## 🛡️ Workflow Seguro de Desarrollo

### Flujo Recomendado (Sin Riesgos)

```bash
# 1. Asegúrate de estar en rama main actualizada
git checkout main
git pull origin main

# 2. Crea rama de feature
git checkout -b feature/mi-nueva-funcionalidad

# 3. Desarrolla y prueba LOCALMENTE
python manage.py runserver
# Prueba exhaustivamente: casos normales, edge cases, errores

# 4. Ejecuta tests (si existen)
pytest

# 5. Commit en tu rama
git add .
git commit -m "Descripción clara del cambio"

# 6. Push a tu rama (NO A main)
git push origin feature/mi-nueva-funcionalidad

# 7. Prueba tu rama en tu entorno local otra vez
# Simula condiciones de producción:
# - DEBUG_VALUE=False
# - DATABASE_URL=postgresql://...
# - Datos reales

# 8. Si todo funciona, merge a main
git checkout main
git merge feature/mi-nueva-funcionalidad

# 9. ⚠️ ÚLTIMO CHECK ANTES DE DEPLOY
# - ¿Probaste todas las funcionalidades afectadas?
# - ¿Verificaste que no rompiste nada existente?
# - ¿Revisaste logs de errores?
# - ¿Las migraciones están correctas?

# 10. Push a producción (AUTO-DEPLOY)
git push origin main

# 11. Monitorea el deploy en Render Dashboard
# - Ve a https://dashboard.render.com
# - Selecciona "sam-metrologia" service
# - Pestaña "Logs" - busca errores
# - Espera "Listening at: http://0.0.0.0:10000"

# 12. Verifica en producción
# - Accede a https://app.sammetrologia.com
# - Prueba la funcionalidad que cambiaste
# - Verifica logs en Render si hay errores
```

### ⚠️ Checklist Pre-Push a main

Antes de `git push origin main`, verifica:

- [ ] Probé el cambio localmente en modo DEBUG=False
- [ ] Probé todas las funcionalidades relacionadas
- [ ] No modifiqué áreas críticas sin entenderlas completamente
- [ ] Si toqué modelos financieros, usé `Decimal` consistentemente
- [ ] Si toqué cálculos de fechas, usé campos correctos
- [ ] Si toqué JSON serialization, manejé tipos Decimal
- [ ] Las migraciones (si hay) son reversibles
- [ ] No hardcodeé valores de desarrollo (IPs, URLs, keys)
- [ ] Revisé que no haya `print()` statements olvidados
- [ ] El código sigue el estilo del proyecto
- [ ] Documenté cambios complejos en comentarios

---

## 📦 Configuración de Entornos

### Desarrollo Local

```bash
# 1. Clonar repositorio
git clone https://github.com/Sam-Metrologia/sam-2.git
cd sam-2

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Crear archivo .env (opcional para desarrollo)
SECRET_KEY=dev-secret-key-change-me
DEBUG_VALUE=True
# DATABASE_URL no necesario (usa SQLite por defecto)

# 5. Aplicar migraciones
python manage.py migrate

# 6. Crear superusuario
python manage.py createsuperuser

# 7. Iniciar servidor
python manage.py runserver

# Acceder: http://localhost:8000
```

### Variables de Entorno por Ambiente

| Variable | Desarrollo | Producción (Render) |
|----------|-----------|-------------------|
| `DEBUG_VALUE` | `True` | `False` |
| `SECRET_KEY` | Cualquiera | Generado por Render |
| `DATABASE_URL` | (SQLite auto) | `postgresql://...` (auto) |
| `RENDER_EXTERNAL_HOSTNAME` | (no existe) | `app.sammetrologia.com` |
| `AWS_ACCESS_KEY_ID` | (opcional) | **REQUERIDO** |
| `AWS_SECRET_ACCESS_KEY` | (opcional) | **REQUERIDO** |
| `AWS_STORAGE_BUCKET_NAME` | (opcional) | **REQUERIDO** |
| `AWS_S3_REGION_NAME` | (opcional) | `us-east-2` |
| `EMAIL_HOST` | (opcional) | `smtp.gmail.com` |
| `EMAIL_HOST_USER` | (opcional) | `metrologiasam@gmail.com` |
| `EMAIL_HOST_PASSWORD` | (opcional) | App Password |

**Detección Automática de Ambiente**:
```python
# En settings.py
IS_PRODUCTION = os.getenv('RENDER_EXTERNAL_HOSTNAME') is not None

if IS_PRODUCTION:
    # PostgreSQL, S3, JSON logs, HTTPS enforcement
else:
    # SQLite, local storage, console logs
```

---

## 🔧 Tareas Comunes de Desarrollo

### Modificar Modelos

```bash
# 1. Edita core/models.py
# Ejemplo: Agregar campo a Equipo
class Equipo(models.Model):
    # ... campos existentes ...
    nuevo_campo = models.CharField(max_length=100, blank=True)

# 2. Crear migración
python manage.py makemigrations
# Output: core/migrations/0XXX_auto_YYYYMMDD_HHMM.py

# 3. Revisar migración generada
cat core/migrations/0XXX_auto_YYYYMMDD_HHMM.py

# 4. Aplicar localmente
python manage.py migrate

# 5. Probar con datos reales
python manage.py shell
>>> from core.models import Equipo
>>> e = Equipo.objects.first()
>>> e.nuevo_campo = "test"
>>> e.save()

# 6. Commit y push
git add core/models.py core/migrations/0XXX_*.py
git commit -m "Add: nuevo_campo to Equipo model"
git push origin main  # ⚠️ Deploy a producción
```

**⚠️ PRECAUCIONES con Migraciones**:
- **NO borres campos sin migración de datos**: perderás información
- **NO cambies tipos de campo directamente**: usa migrations con transformaciones
- **Migraciones en producción son IRREVERSIBLES**: Render aplica automáticamente

### Trabajar con Tipos Decimal

```python
# ❌ INCORRECTO - Mezclando tipos
from decimal import Decimal

precio = Decimal('100.00')
descuento = 0.10  # float
total = precio - descuento  # ⚠️ TypeError en runtime!

# ✅ CORRECTO - Consistencia de tipos
precio = Decimal('100.00')
descuento = Decimal('0.10')
total = precio - descuento  # Funciona: Decimal('90.00')

# ✅ CORRECTO - Conversión explícita
meses = 12
tarifa_mensual = precio / Decimal(str(meses))

# ✅ CORRECTO - Para JSON serialization
import json

def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    return obj

json.dumps(decimal_to_float(financial_data))
```

### Agregar Nueva Vista

```python
# 1. Crear vista en core/views/ (o nuevo archivo)
# core/views/mi_nueva_vista.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def mi_nueva_vista(request):
    context = {
        'titulo': 'Mi Nueva Funcionalidad'
    }
    return render(request, 'core/mi_nueva_vista.html', context)

# 2. Registrar URL en core/urls.py
# core/urls.py
from core.views.mi_nueva_vista import mi_nueva_vista

urlpatterns = [
    # ... rutas existentes ...
    path('mi-ruta/', mi_nueva_vista, name='mi_nueva_vista'),
]

# 3. Crear template
# templates/core/mi_nueva_vista.html
{% extends 'base.html' %}
{% block content %}
<h1>{{ titulo }}</h1>
{% endblock %}

# 4. Probar localmente
python manage.py runserver
# http://localhost:8000/core/mi-ruta/

# 5. Push cuando esté listo
git add core/views/mi_nueva_vista.py core/urls.py templates/core/mi_nueva_vista.html
git commit -m "Add: nueva vista para [funcionalidad]"
git push origin main
```

### Modificar Templates

```html
<!-- Templates heredan de base.html -->
<!-- templates/base.html contiene estructura global -->

<!-- Tu template: templates/core/equipos/listar.html -->
{% extends 'base.html' %}
{% load static %}

{% block title %}Listado de Equipos{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-6">
    <h1 class="text-2xl font-bold">Equipos</h1>
    <!-- ... contenido ... -->
</div>
{% endblock %}

<!-- PRECAUCIÓN: base.html incluye -->
<!-- - TailwindCSS para estilos -->
<!-- - Alpine.js para interactividad -->
<!-- - Menú de navegación global -->
<!-- NO modifiques base.html sin consultar -->
```

### Trabajar con Archivos S3

```python
# El sistema automáticamente usa S3 en producción

# En desarrollo (local storage)
IS_PRODUCTION = False  # → media/ folder

# En producción (S3)
IS_PRODUCTION = True   # → AWS S3 bucket

# Para subir archivo en código:
from django.core.files.storage import default_storage

def mi_vista_upload(request):
    if request.method == 'POST' and request.FILES.get('archivo'):
        archivo = request.FILES['archivo']

        # Validar (importante!)
        from core.file_validators import validate_image_file
        validate_image_file(archivo)

        # Guardar (automáticamente va a S3 en prod)
        path = default_storage.save(f'uploads/{archivo.name}', archivo)
        url = default_storage.url(path)

        # url será:
        # - Desarrollo: /media/uploads/archivo.jpg
        # - Producción: https://sam-bucket.s3.amazonaws.com/uploads/archivo.jpg

# Límites configurados en SAM_CONFIG:
# - MAX_FILE_SIZE_MB = 10
# - Formatos permitidos: jpg, jpeg, png, pdf, xlsx, docx
```

---

## 🐛 Debugging y Troubleshooting

### Ver Logs en Producción

```bash
# Opción 1: Render Dashboard (Recomendado)
# 1. https://dashboard.render.com
# 2. Selecciona "sam-metrologia"
# 3. Pestaña "Logs"
# 4. Filtra por nivel: Error, Warning, Info

# Opción 2: Render CLI
render logs -s sam-metrologia -f

# Logs estructurados en JSON:
{
  "timestamp": "2024-11-06T10:30:00Z",
  "level": "ERROR",
  "logger": "django.request",
  "message": "Internal Server Error",
  "path": "/core/panel-decisiones/",
  "traceback": "..."
}
```

### Logs Locales (Desarrollo)

```python
# Usar logger estructurado
import logging
logger = logging.getLogger(__name__)

logger.info("Información general", extra={'equipo_id': 123})
logger.warning("Advertencia", extra={'usuario': request.user.username})
logger.error("Error crítico", exc_info=True)  # Incluye traceback

# Logs se guardan en:
# - logs/sam_info.log      (nivel INFO+)
# - logs/sam_errors.log    (nivel ERROR+)
# - logs/sam_security.log  (eventos de seguridad)
```

### Errores Comunes y Soluciones

#### Error: "Object of type Decimal is not JSON serializable"

```python
# CAUSA: Intentar json.dumps() de Decimal directamente
data = {'precio': Decimal('100.50')}
json.dumps(data)  # ❌ TypeError

# SOLUCIÓN: Usar helper function
json.dumps(decimal_to_float(data))  # ✅
```

#### Error: "unsupported operand type(s) for -: 'decimal.Decimal' and 'float'"

```python
# CAUSA: Mezclar Decimal y float en aritmética
precio = Decimal('100')
descuento = 10.5  # float
total = precio - descuento  # ❌ TypeError

# SOLUCIÓN: Convertir todo a Decimal
descuento = Decimal('10.5')
total = precio - descuento  # ✅
```

#### Error: "Equipo has no attribute 'ima_comprobacion'"

```python
# CAUSA: Typo en nombre de campo (bug histórico)
self.ima_comprobacion = date.today()  # ❌ Campo no existe

# SOLUCIÓN: Usar nombre correcto
self.proxima_comprobacion = date.today()  # ✅
```

#### Error: "Application failed to respond" (Render)

**Síntomas**: Deploy exitoso pero app no responde (502/503)

**Posibles causas**:
1. Gunicorn no escucha en `0.0.0.0:$PORT`
2. Migraciones fallaron silenciosamente
3. Imports circulares
4. Error en `settings.py` que impide arranque

**Solución**:
```bash
# 1. Revisar logs de Render
# 2. Buscar línea: "Listening at: http://0.0.0.0:10000"
# 3. Si no aparece, revisar errores previos
# 4. Verificar start.sh:
cat start.sh
# Debe tener: gunicorn proyecto_c.wsgi:application --bind 0.0.0.0:$PORT

# 5. Probar localmente con Gunicorn
gunicorn proyecto_c.wsgi:application --bind 0.0.0.0:8000
```

#### Error: "Out of Memory" (Render)

**Síntomas**: App se reinicia inesperadamente, logs muestran "Killed"

**Causa**: Render Free tier = 512 MB RAM. ZIPs grandes consumen demasiado.

**Solución**:
- Sistema de cola ya implementado (`ZipRequest` model)
- Máximo 35 equipos por ZIP
- Limpieza automática cada 6 horas (cron job)

```python
# Verificar uso de memoria antes de operación pesada
import psutil
mem = psutil.virtual_memory()
if mem.percent > 80:
    logger.warning("Memoria alta, evitando operación pesada")
    return
```

---

## 🧪 Testing

### Ejecutar Tests Localmente

```bash
# Si hay suite de tests (pytest)
pytest

# Con coverage
pytest --cov=core --cov-report=html

# Tests específicos
pytest tests/test_models.py
pytest tests/test_views/test_equipos.py -v

# Tests rápidos (sin integración)
pytest -m "not slow"
```

**Nota**: El proyecto tiene estructura de tests preparada pero puede no tener 100% cobertura. Agrega tests al crear funcionalidades nuevas.

### Probar Manualmente Antes de Deploy

```python
# Checklist de pruebas manuales

# 1. CRUD básico de equipos
# - Crear equipo
# - Editar equipo
# - Ver detalle equipo
# - Eliminar equipo (soft delete)
# - Listar equipos

# 2. Actividades (calibraciones, mantenimientos, comprobaciones)
# - Crear actividad
# - Verificar que se calculó proxima_comprobacion/calibracion
# - Ver en listado de equipos
# - Verificar notificaciones

# 3. Panel de decisiones
# - Acceder a /core/panel-decisiones/
# - Verificar métricas financieras cargan
# - Verificar gráficos se renderizan
# - Sin errores de consola JS

# 4. Exportación ZIP
# - Seleccionar <35 equipos
# - Generar ZIP
# - Verificar descarga correcta
# - Probar con >35 equipos (debe usar cola)

# 5. Gestión de empresas
# - Crear empresa
# - Verificar límite de equipos
# - Probar multi-tenancy (usuarios ven solo su empresa)
```

---

## 📚 Recursos y Documentación

### Documentos del Proyecto

- **[README.md](./README.md)**: Overview, instalación, características
- **[DEVELOPER-GUIDE.md](./DEVELOPER-GUIDE.md)**: Esta guía (desarrollo seguro)
- **[DESPLEGAR-EN-RENDER.md](./DESPLEGAR-EN-RENDER.md)**: Guía completa de deployment
- **[CLAUDE.md](./CLAUDE.md)**: Guía para Claude Code (AI assistant)
- **[render.yaml](./render.yaml)**: Configuración de infraestructura Render

### Documentación Externa

- **Django 5.2**: https://docs.djangoproject.com/en/5.2/
- **Render Docs**: https://render.com/docs
- **AWS S3 + Django**: https://django-storages.readthedocs.io/
- **TailwindCSS**: https://tailwindcss.com/docs
- **PostgreSQL**: https://www.postgresql.org/docs/

### Comandos Django Útiles

```bash
# Base de datos
python manage.py migrate                    # Aplicar migraciones
python manage.py makemigrations             # Crear migraciones
python manage.py showmigrations             # Ver estado de migraciones
python manage.py sqlmigrate core 0001       # Ver SQL de migración

# Usuarios
python manage.py createsuperuser            # Crear admin
python manage.py changepassword <username>  # Cambiar contraseña

# Archivos estáticos
python manage.py collectstatic              # Recolectar estáticos

# Diagnóstico
python manage.py check                      # Verificar proyecto
python manage.py check --deploy             # Checks de producción
python manage.py health_check               # Health check personalizado

# Shell interactivo
python manage.py shell                      # Python shell con Django
python manage.py dbshell                    # Shell de base de datos

# Comandos personalizados SAM
python manage.py cleanup_zip_files --older-than-hours 6
python manage.py process_zip_queue --check-interval 5
python manage.py enviar_notificaciones_vencimientos
python manage.py cleanup_old_notifications
```

---

## 🔐 Seguridad

### Buenas Prácticas

```python
# ✅ SIEMPRE usa decoradores de autenticación
from django.contrib.auth.decorators import login_required

@login_required
def mi_vista(request):
    ...

# ✅ SIEMPRE filtra por empresa del usuario
equipos = Equipo.objects.filter(empresa=request.user.empresa)

# ❌ NUNCA expongas todos los registros
equipos = Equipo.objects.all()  # Peligroso en multi-tenant

# ✅ Valida archivos uploaded
from core.file_validators import validate_image_file, validate_document_file

validate_image_file(request.FILES['imagen'])
validate_document_file(request.FILES['certificado'])

# ✅ Usa CSRF protection (Django lo hace automático en templates)
<form method="post">
  {% csrf_token %}
  ...
</form>

# ✅ Sanitiza inputs de usuario (Django forms lo hace)
form = EquipoForm(request.POST)
if form.is_valid():
    equipo = form.save()

# ❌ NUNCA uses eval(), exec(), __import__() con input de usuario
```

### Variables Sensibles

```bash
# ⚠️ NUNCA commitees estos valores al repositorio

# ❌ MAL:
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"

# ✅ BIEN:
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')

# ✅ Configura en Render Dashboard → Environment
# NO en código
```

### Acceso a Producción

```
┌─────────────────────────────────────────────────┐
│  ⚠️  NO TIENE ACCESO SSH A PRODUCCIÓN          │
│                                                 │
│  Render no provee SSH en plan Free             │
│  Usa Shell web en Dashboard para comandos      │
└─────────────────────────────────────────────────┘

# Para ejecutar comandos en producción:
# 1. Render Dashboard → sam-metrologia
# 2. Pestaña "Shell"
# 3. Ejecutar comandos Python/Django
python manage.py createsuperuser
python manage.py showmigrations
python manage.py dbshell  # PostgreSQL shell
```

---

## 🚀 Despliegue y CI/CD

### Estado Actual

- **Hosting**: Render Free Tier
- **Auto-deploy**: ✅ Habilitado desde `main` branch
- **Build time**: ~5-10 minutos
- **Servicios**:
  - Web Service: `sam-metrologia` (Django + Gunicorn)
  - Background Worker: `sam-zip-processor`
  - Database: `sam-metrologia-db` (PostgreSQL 15)
  - 6 Cron Jobs activos

### Monitorear Deploy

```bash
# Durante el deploy, Render ejecuta:

# 1. Build phase (./build.sh)
Installing dependencies...
Collecting Django==5.2.4
...
Successfully installed Django-5.2.4 psycopg2-binary-2.9.9 ...

Applying migrations...
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, core, sessions
Running migrations:
  No migrations to apply.

Collecting static files...
X static files copied to '/opt/render/project/src/staticfiles'.

# 2. Start phase (./start.sh)
Starting Gunicorn...
[INFO] Starting gunicorn 21.2.0
[INFO] Listening at: http://0.0.0.0:10000 (1)
[INFO] Using worker: sync
[INFO] Booting worker with pid: 7

# ✅ Deploy exitoso cuando ves "Listening at"
```

### Rollback en Caso de Error

```bash
# Si el deploy rompió algo:

# Opción 1: Revert commit localmente
git revert HEAD
git push origin main  # Deploy del revert

# Opción 2: Render Dashboard Manual Rollback
# 1. Dashboard → sam-metrologia
# 2. Pestaña "Events"
# 3. Encuentra deploy anterior exitoso
# 4. Click "Rollback to this deploy"

# Opción 3: Force push de commit anterior
git reset --hard <commit-hash-anterior>
git push -f origin main  # ⚠️ Usar solo en emergencia
```

### Verificar Health del Sistema

```bash
# Health checks automáticos de Render:
# - HTTP 200 en cualquier ruta
# - Tiempo de respuesta < 30s

# Probar manualmente:
curl https://app.sammetrologia.com/
# Debe retornar HTML (login page)

# Health check personalizado:
curl https://app.sammetrologia.com/health/
# → {"status": "ok", "database": "connected"}
```

---

## 📞 Soporte y Contacto

### Problemas Técnicos

1. **Revisar esta guía primero**: La mayoría de problemas comunes están documentados
2. **Consultar logs**: Render Dashboard → Logs
3. **Revisar issues conocidos**: [Sección Troubleshooting](#debugging-y-troubleshooting)
4. **Contactar**: metrologiasam@gmail.com

### Escalación

- **Errores de producción**: Revisar logs inmediatamente
- **Deploy fallido**: Rollback ASAP, investigar después
- **Pérdida de datos**: Render hace backups automáticos (7 días retención)
- **Problemas de performance**: Monitorear RAM usage (Render Dashboard → Metrics)

---

## ✅ Checklist Final: Antes de Tu Primer Cambio

Antes de modificar cualquier código:

- [ ] Leí esta guía completa
- [ ] Entiendo que estoy trabajando en sistema de producción
- [ ] Sé que `git push origin main` deploys automáticamente
- [ ] Conozco las áreas críticas (financiero, fechas, ZIPs)
- [ ] Configuré mi entorno de desarrollo local
- [ ] Probé que puedo correr el proyecto localmente
- [ ] Entiendo la diferencia entre Decimal y float
- [ ] Sé cómo ver logs en Render
- [ ] Sé cómo hacer rollback si rompo algo
- [ ] Tengo acceso a Render Dashboard
- [ ] Tengo credenciales de AWS S3 (si voy a trabajar con archivos)

---

## 🎯 Principios de Desarrollo SAM

1. **Seguridad primero**: Multi-tenancy estricto, validación de inputs
2. **Precisión financiera**: Decimal para todo lo relacionado a dinero
3. **Confiabilidad**: Sistema en uso real, zero downtime esperado
4. **Simplicidad**: No sobrecomplicar, Django es suficiente
5. **Documentación**: Todo cambio importante debe documentarse

---

**¡Buena suerte con el desarrollo!** 🚀

Si tienes dudas, consulta el código existente como referencia. El proyecto tiene patrones consistentes que debes seguir.

**Recuerda: Cada línea de código que pusheas puede afectar usuarios reales. Desarrolla con responsabilidad.**
