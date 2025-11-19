# PLAN DE MEJORAS UX - SAM Metrología
**Fecha:** 19 de Noviembre de 2025
**Prioridad:** 🟡 MEDIA-ALTA
**Categoría:** Mejoras de Experiencia de Usuario y Funcionalidad

---

## 📋 RESUMEN DE PETICIONES

### 1. ⏱️ Auto-Logout Inteligente (Session Timeout)
**Problema actual:** La plataforma se cierra cada cierto tiempo, incluso cuando está en uso activo.

**Mejora solicitada:**
- El sistema debe detectar si hay actividad del usuario
- Solo cerrar sesión si la plataforma está SIN USO
- No cerrar sesión si el usuario está activamente trabajando

---

### 2. 🔄 Navegación Rápida entre Equipos
**Problema actual:** Para editar el siguiente equipo, hay que volver a home y seleccionar el siguiente.

**Mejora solicitada:**
- Botones "Anterior" y "Siguiente" en la vista de edición de equipos
- Navegar entre equipos sin volver a home
- Mejorar fluidez del trabajo con múltiples equipos

---

### 3. 🗑️ Permisos de Eliminación y Eliminación Masiva
**Problema actual:**
- No está claro quién puede eliminar equipos
- No hay forma de eliminar varios equipos a la vez

**Mejora solicitada:**
- **Permisos:** Solo Gerente y SuperUsuario pueden eliminar equipos
- **Eliminación masiva:** Seleccionar múltiples equipos y eliminar en lote
- Otros roles (técnicos, etc.) no deben poder eliminar

---

## 🎯 IMPLEMENTACIÓN DETALLADA

---

## 1️⃣ AUTO-LOGOUT INTELIGENTE

### 📊 Análisis Técnico

**Causa del problema actual:**
- Django tiene un timeout de sesión fijo (`SESSION_COOKIE_AGE`)
- No detecta actividad del usuario, solo tiempo transcurrido
- La sesión expira incluso si el usuario está trabajando

**Solución propuesta:**
Implementar un sistema de "heartbeat" que detecte actividad y extienda la sesión automáticamente.

### 🛠️ Implementación

#### **Paso 1: Middleware de Activity Tracking**

**Crear:** `core/middleware.py` (ya existe, agregar funcionalidad)

```python
# core/middleware.py
from django.utils import timezone
from datetime import timedelta

class SessionActivityMiddleware:
    """
    Middleware que extiende la sesión automáticamente si hay actividad del usuario.

    - Detecta requests del usuario (GET, POST)
    - Actualiza 'last_activity' en la sesión
    - Extiende la sesión si hay actividad reciente
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now = timezone.now()

            # Obtener última actividad
            last_activity = request.session.get('last_activity')

            if last_activity:
                # Convertir string a datetime
                last_activity_time = timezone.datetime.fromisoformat(last_activity)
                inactive_time = now - last_activity_time

                # Si ha estado inactivo más de 30 minutos, cerrar sesión
                if inactive_time > timedelta(minutes=30):
                    # Dejar que expire naturalmente
                    pass
                else:
                    # Hay actividad reciente, extender sesión
                    request.session.set_expiry(1800)  # 30 minutos más

            # Actualizar última actividad
            request.session['last_activity'] = now.isoformat()

        response = self.get_response(request)
        return response
```

**Agregar en `proyecto_c/settings.py`:**
```python
MIDDLEWARE = [
    # ... middlewares existentes
    'core.middleware.SessionActivityMiddleware',  # ← NUEVO
]

# Configuración de sesión
SESSION_COOKIE_AGE = 1800  # 30 minutos (en segundos)
SESSION_SAVE_EVERY_REQUEST = False  # No guardar en cada request (performance)
```

#### **Paso 2: JavaScript Heartbeat (Frontend)**

**Crear:** `core/static/js/session_keepalive.js`

```javascript
/**
 * Sistema de Heartbeat para mantener sesión activa
 *
 * Detecta actividad del usuario (mouse, teclado, clicks) y envía
 * un "ping" al servidor cada 5 minutos si hay actividad.
 */

let lastActivityTime = Date.now();
let heartbeatInterval;

// Detectar actividad del usuario
const activityEvents = ['mousedown', 'keydown', 'scroll', 'touchstart'];

activityEvents.forEach(event => {
    document.addEventListener(event, () => {
        lastActivityTime = Date.now();
    }, { passive: true });
});

// Enviar heartbeat cada 5 minutos si hay actividad
function sendHeartbeat() {
    const inactiveTime = Date.now() - lastActivityTime;
    const fiveMinutes = 5 * 60 * 1000; // 5 minutos en milisegundos

    // Solo enviar si ha habido actividad en los últimos 5 minutos
    if (inactiveTime < fiveMinutes) {
        fetch('/core/session-heartbeat/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ timestamp: Date.now() })
        }).catch(err => console.error('Heartbeat error:', err));
    }
}

// Iniciar heartbeat cada 5 minutos
heartbeatInterval = setInterval(sendHeartbeat, 5 * 60 * 1000);

// Función auxiliar para obtener cookie CSRF
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Mostrar advertencia si está próximo a cerrar sesión (25 minutos sin actividad)
setInterval(() => {
    const inactiveTime = Date.now() - lastActivityTime;
    const twentyFiveMinutes = 25 * 60 * 1000;

    if (inactiveTime > twentyFiveMinutes && inactiveTime < (30 * 60 * 1000)) {
        // Mostrar advertencia
        if (!document.getElementById('session-warning')) {
            const warning = document.createElement('div');
            warning.id = 'session-warning';
            warning.className = 'alert alert-warning position-fixed top-0 start-50 translate-middle-x mt-3';
            warning.style.zIndex = '9999';
            warning.innerHTML = `
                <strong>⚠️ Tu sesión está próxima a expirar</strong>
                <br>Mueve el mouse o presiona una tecla para mantenerla activa.
            `;
            document.body.appendChild(warning);

            // Remover después de 10 segundos
            setTimeout(() => warning.remove(), 10000);
        }
    }
}, 60 * 1000); // Verificar cada minuto
```

**Agregar en `templates/base.html`:**
```html
{% load static %}
<script src="{% static 'js/session_keepalive.js' %}"></script>
```

#### **Paso 3: Vista de Heartbeat (Backend)**

**Agregar en `core/views/auth_views.py`:**
```python
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

@login_required
@require_POST
def session_heartbeat(request):
    """
    Endpoint para recibir heartbeat del frontend y mantener sesión activa.
    """
    # Extender sesión por 30 minutos más
    request.session.set_expiry(1800)

    return JsonResponse({
        'status': 'ok',
        'message': 'Session extended'
    })
```

**Agregar en `core/urls.py`:**
```python
urlpatterns = [
    # ... urls existentes
    path('session-heartbeat/', views.session_heartbeat, name='session_heartbeat'),
]
```

### ✅ Resultado Esperado

- ✅ Sesión NO se cierra si usuario está activo (moviendo mouse, escribiendo, etc.)
- ✅ Sesión SÍ se cierra después de 30 minutos de INACTIVIDAD real
- ✅ Advertencia visual 5 minutos antes de expirar
- ✅ Heartbeat automático cada 5 minutos si hay actividad

---

## 2️⃣ NAVEGACIÓN RÁPIDA ENTRE EQUIPOS

### 📊 Análisis Técnico

**Flujo actual:**
1. Usuario edita Equipo #5
2. Guarda cambios
3. Redirige a home/lista de equipos
4. Usuario busca y hace clic en Equipo #6
5. Edita Equipo #6

**Flujo mejorado:**
1. Usuario edita Equipo #5
2. Ve botones "← Anterior" y "Siguiente →"
3. Clic en "Siguiente" → Va directo a Equipo #6
4. Continúa editando sin interrupciones

### 🛠️ Implementación

#### **Paso 1: Modificar Vista de Edición**

**Editar:** `core/views/equipment.py`

```python
# core/views/equipment.py
from django.shortcuts import get_object_or_404
from django.db.models import Q

@login_required
def equipo_editar(request, pk):
    """Vista de edición con navegación entre equipos"""
    equipo = get_object_or_404(Equipo, pk=pk)

    # Verificar permisos (empresa del usuario)
    if equipo.empresa != request.user.empresa:
        messages.error(request, "No tienes permiso para editar este equipo.")
        return redirect('core:equipos_list')

    # NUEVO: Obtener equipos anterior y siguiente de la misma empresa
    equipos_empresa = Equipo.objects.filter(
        empresa=request.user.empresa
    ).order_by('codigo_equipo')  # Ordenar por código

    # Buscar índice actual
    equipos_ids = list(equipos_empresa.values_list('id', flat=True))
    try:
        current_index = equipos_ids.index(equipo.id)

        # Equipo anterior
        prev_equipo_id = equipos_ids[current_index - 1] if current_index > 0 else None

        # Equipo siguiente
        next_equipo_id = equipos_ids[current_index + 1] if current_index < len(equipos_ids) - 1 else None

    except ValueError:
        prev_equipo_id = None
        next_equipo_id = None

    if request.method == 'POST':
        form = EquipoForm(request.POST, request.FILES, instance=equipo)
        if form.is_valid():
            form.save()
            messages.success(request, f"Equipo {equipo.codigo_equipo} actualizado correctamente.")

            # NUEVO: Determinar redirección según botón presionado
            if 'save_and_next' in request.POST and next_equipo_id:
                return redirect('core:equipo_editar', pk=next_equipo_id)
            elif 'save_and_prev' in request.POST and prev_equipo_id:
                return redirect('core:equipo_editar', pk=prev_equipo_id)
            else:
                # Guardar normal, redirigir a detalles
                return redirect('core:equipo_detalle', pk=equipo.pk)
    else:
        form = EquipoForm(instance=equipo)

    context = {
        'form': form,
        'equipo': equipo,
        'prev_equipo_id': prev_equipo_id,  # ← NUEVO
        'next_equipo_id': next_equipo_id,  # ← NUEVO
        'current_position': current_index + 1 if 'current_index' in locals() else None,
        'total_equipos': equipos_empresa.count(),
    }

    return render(request, 'core/equipos/equipo_form.html', context)
```

#### **Paso 2: Modificar Template**

**Editar:** `templates/core/equipos/equipo_form.html`

```html
<!-- templates/core/equipos/equipo_form.html -->

<div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
        <h3>
            {% if equipo %}
                Editar Equipo: {{ equipo.codigo_equipo }}
            {% else %}
                Crear Nuevo Equipo
            {% endif %}
        </h3>

        <!-- NUEVO: Indicador de posición -->
        {% if current_position and total_equipos %}
        <span class="badge bg-info">
            Equipo {{ current_position }} de {{ total_equipos }}
        </span>
        {% endif %}
    </div>

    <div class="card-body">
        <form method="post" enctype="multipart/form-data">
            {% csrf_token %}

            <!-- Formulario existente -->
            {{ form.as_p }}

            <!-- NUEVO: Botones de navegación y guardado -->
            <div class="d-flex justify-content-between mt-4">

                <!-- Botón Anterior -->
                {% if prev_equipo_id %}
                <button type="submit" name="save_and_prev" class="btn btn-outline-secondary">
                    <i class="fas fa-arrow-left"></i> Guardar y Anterior
                </button>
                {% else %}
                <div></div> <!-- Spacer -->
                {% endif %}

                <!-- Botones centrales -->
                <div class="btn-group">
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save"></i> Guardar
                    </button>
                    <a href="{% url 'core:equipos_list' %}" class="btn btn-secondary">
                        <i class="fas fa-times"></i> Cancelar
                    </a>
                </div>

                <!-- Botón Siguiente -->
                {% if next_equipo_id %}
                <button type="submit" name="save_and_next" class="btn btn-outline-primary">
                    Guardar y Siguiente <i class="fas fa-arrow-right"></i>
                </button>
                {% else %}
                <div></div> <!-- Spacer -->
                {% endif %}
            </div>

            <!-- NUEVO: Atajos de teclado (opcional) -->
            <div class="text-center mt-3">
                <small class="text-muted">
                    💡 Tip: Usa
                    <kbd>Ctrl</kbd> + <kbd>←</kbd> para anterior,
                    <kbd>Ctrl</kbd> + <kbd>→</kbd> para siguiente
                </small>
            </div>
        </form>
    </div>
</div>

<!-- NUEVO: JavaScript para atajos de teclado -->
<script>
document.addEventListener('keydown', function(e) {
    // Ctrl + Flecha Izquierda = Anterior
    if (e.ctrlKey && e.key === 'ArrowLeft') {
        const prevBtn = document.querySelector('button[name="save_and_prev"]');
        if (prevBtn) {
            e.preventDefault();
            prevBtn.click();
        }
    }

    // Ctrl + Flecha Derecha = Siguiente
    if (e.ctrlKey && e.key === 'ArrowRight') {
        const nextBtn = document.querySelector('button[name="save_and_next"]');
        if (nextBtn) {
            e.preventDefault();
            nextBtn.click();
        }
    }
});
</script>
```

### ✅ Resultado Esperado

- ✅ Botones "Anterior" y "Siguiente" en vista de edición
- ✅ Indicador de posición (Ej: "Equipo 5 de 20")
- ✅ Guardado automático al navegar
- ✅ Atajos de teclado Ctrl+← y Ctrl+→
- ✅ Navegación fluida sin volver a home

---

## 3️⃣ PERMISOS DE ELIMINACIÓN Y ELIMINACIÓN MASIVA

### 📊 Análisis Técnico

**Requerimientos:**
1. Solo Gerente y SuperUsuario pueden eliminar equipos
2. Implementar eliminación masiva (múltiples equipos a la vez)
3. Otros roles no deben ver opción de eliminar

### 🛠️ Implementación

#### **Paso 1: Definir Permisos en Modelos**

**Editar:** `core/models.py` (verificar que existan los roles)

```python
# core/models.py
class CustomUser(AbstractUser):
    ROL_SUPERUSUARIO = 'superusuario'
    ROL_GERENTE = 'gerente'
    ROL_TECNICO = 'tecnico'
    ROL_AUDITOR = 'auditor'

    ROLES_CHOICES = [
        (ROL_SUPERUSUARIO, 'Super Usuario'),
        (ROL_GERENTE, 'Gerente'),
        (ROL_TECNICO, 'Técnico'),
        (ROL_AUDITOR, 'Auditor'),
    ]

    rol = models.CharField(max_length=20, choices=ROLES_CHOICES, default=ROL_TECNICO)

    def puede_eliminar_equipos(self):
        """Verifica si el usuario puede eliminar equipos"""
        return self.rol in [self.ROL_SUPERUSUARIO, self.ROL_GERENTE] or self.is_superuser
```

#### **Paso 2: Vista de Eliminación Individual**

**Editar:** `core/views/equipment.py`

```python
from django.contrib.auth.decorators import user_passes_test

def puede_eliminar_equipos(user):
    """Decorador personalizado para verificar permisos de eliminación"""
    return user.puede_eliminar_equipos()

@login_required
@user_passes_test(puede_eliminar_equipos, login_url='core:dashboard')
def equipo_eliminar(request, pk):
    """
    Vista para eliminar un equipo individual.
    Solo accesible por Gerente y SuperUsuario.
    """
    equipo = get_object_or_404(Equipo, pk=pk)

    # Verificar que el equipo pertenece a la empresa del usuario
    if equipo.empresa != request.user.empresa:
        messages.error(request, "No tienes permiso para eliminar este equipo.")
        return redirect('core:equipos_list')

    if request.method == 'POST':
        codigo = equipo.codigo_equipo
        equipo.delete()
        messages.success(request, f"Equipo {codigo} eliminado correctamente.")
        return redirect('core:equipos_list')

    return render(request, 'core/equipos/equipo_confirm_delete.html', {
        'equipo': equipo
    })
```

#### **Paso 3: Vista de Eliminación Masiva**

**Agregar en `core/views/equipment.py`:**

```python
from django.http import JsonResponse
import json

@login_required
@user_passes_test(puede_eliminar_equipos, login_url='core:dashboard')
def equipos_eliminar_masivo(request):
    """
    Vista para eliminar múltiples equipos a la vez.
    Solo accesible por Gerente y SuperUsuario.
    """
    if request.method == 'POST':
        # Obtener IDs de equipos a eliminar
        equipos_ids = request.POST.getlist('equipos_ids[]')

        if not equipos_ids:
            messages.error(request, "No se seleccionaron equipos para eliminar.")
            return redirect('core:equipos_list')

        # Verificar que todos los equipos pertenecen a la empresa del usuario
        equipos = Equipo.objects.filter(
            id__in=equipos_ids,
            empresa=request.user.empresa
        )

        if equipos.count() != len(equipos_ids):
            messages.error(request, "Algunos equipos no pertenecen a tu empresa.")
            return redirect('core:equipos_list')

        # Eliminar equipos
        cantidad = equipos.count()
        equipos.delete()

        messages.success(request, f"{cantidad} equipo(s) eliminado(s) correctamente.")
        return redirect('core:equipos_list')

    # Vista de confirmación
    equipos_ids = request.GET.getlist('ids')
    equipos = Equipo.objects.filter(
        id__in=equipos_ids,
        empresa=request.user.empresa
    )

    return render(request, 'core/equipos/equipos_confirm_delete_masivo.html', {
        'equipos': equipos
    })
```

**Agregar URLs en `core/urls.py`:**
```python
urlpatterns = [
    # ... urls existentes
    path('equipos/eliminar/<int:pk>/', views.equipo_eliminar, name='equipo_eliminar'),
    path('equipos/eliminar-masivo/', views.equipos_eliminar_masivo, name='equipos_eliminar_masivo'),
]
```

#### **Paso 4: Template con Selección Masiva**

**Editar:** `templates/core/equipos/equipos_list.html`

```html
<!-- templates/core/equipos/equipos_list.html -->

<div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
        <h3>Lista de Equipos</h3>

        <!-- NUEVO: Botones de acción masiva (solo para Gerente/SuperUsuario) -->
        {% if request.user.puede_eliminar_equipos %}
        <div>
            <button id="btn-eliminar-seleccionados" class="btn btn-danger" disabled>
                <i class="fas fa-trash"></i> Eliminar Seleccionados (<span id="count-selected">0</span>)
            </button>
        </div>
        {% endif %}
    </div>

    <div class="card-body">
        <form id="form-equipos-masivo" method="POST" action="{% url 'core:equipos_eliminar_masivo' %}">
            {% csrf_token %}

            <table class="table table-striped">
                <thead>
                    <tr>
                        <!-- NUEVO: Columna de selección (solo para Gerente/SuperUsuario) -->
                        {% if request.user.puede_eliminar_equipos %}
                        <th width="50">
                            <input type="checkbox" id="select-all" title="Seleccionar todos">
                        </th>
                        {% endif %}

                        <th>Código</th>
                        <th>Nombre</th>
                        <th>Estado</th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    {% for equipo in equipos %}
                    <tr>
                        <!-- NUEVO: Checkbox de selección -->
                        {% if request.user.puede_eliminar_equipos %}
                        <td>
                            <input type="checkbox" name="equipos_ids[]"
                                   value="{{ equipo.id }}"
                                   class="equipo-checkbox">
                        </td>
                        {% endif %}

                        <td>{{ equipo.codigo_equipo }}</td>
                        <td>{{ equipo.nombre_equipo }}</td>
                        <td>
                            <span class="badge bg-{{ equipo.get_estado_badge }}">
                                {{ equipo.get_estado_display }}
                            </span>
                        </td>
                        <td>
                            <a href="{% url 'core:equipo_detalle' equipo.pk %}"
                               class="btn btn-sm btn-info">
                                <i class="fas fa-eye"></i> Ver
                            </a>
                            <a href="{% url 'core:equipo_editar' equipo.pk %}"
                               class="btn btn-sm btn-primary">
                                <i class="fas fa-edit"></i> Editar
                            </a>

                            <!-- NUEVO: Botón eliminar (solo Gerente/SuperUsuario) -->
                            {% if request.user.puede_eliminar_equipos %}
                            <a href="{% url 'core:equipo_eliminar' equipo.pk %}"
                               class="btn btn-sm btn-danger"
                               onclick="return confirm('¿Seguro que deseas eliminar {{ equipo.codigo_equipo }}?')">
                                <i class="fas fa-trash"></i> Eliminar
                            </a>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </form>
    </div>
</div>

<!-- NUEVO: JavaScript para selección masiva -->
{% if request.user.puede_eliminar_equipos %}
<script>
document.addEventListener('DOMContentLoaded', function() {
    const selectAll = document.getElementById('select-all');
    const checkboxes = document.querySelectorAll('.equipo-checkbox');
    const btnEliminar = document.getElementById('btn-eliminar-seleccionados');
    const countSelected = document.getElementById('count-selected');
    const form = document.getElementById('form-equipos-masivo');

    // Seleccionar/deseleccionar todos
    selectAll.addEventListener('change', function() {
        checkboxes.forEach(cb => cb.checked = this.checked);
        updateDeleteButton();
    });

    // Actualizar al cambiar checkboxes individuales
    checkboxes.forEach(cb => {
        cb.addEventListener('change', updateDeleteButton);
    });

    // Actualizar estado del botón de eliminar
    function updateDeleteButton() {
        const selected = document.querySelectorAll('.equipo-checkbox:checked').length;
        countSelected.textContent = selected;
        btnEliminar.disabled = selected === 0;
    }

    // Confirmar eliminación masiva
    btnEliminar.addEventListener('click', function() {
        const selected = document.querySelectorAll('.equipo-checkbox:checked').length;
        if (confirm(`¿Seguro que deseas eliminar ${selected} equipo(s)? Esta acción no se puede deshacer.`)) {
            form.submit();
        }
    });
});
</script>
{% endif %}
```

#### **Paso 5: Template de Confirmación Masiva**

**Crear:** `templates/core/equipos/equipos_confirm_delete_masivo.html`

```html
<!-- templates/core/equipos/equipos_confirm_delete_masivo.html -->

{% extends 'base.html' %}

{% block content %}
<div class="container mt-4">
    <div class="card border-danger">
        <div class="card-header bg-danger text-white">
            <h3><i class="fas fa-exclamation-triangle"></i> Confirmar Eliminación Masiva</h3>
        </div>
        <div class="card-body">
            <p class="lead">
                Estás a punto de eliminar <strong>{{ equipos.count }}</strong> equipo(s):
            </p>

            <ul class="list-group mb-3">
                {% for equipo in equipos %}
                <li class="list-group-item">
                    <strong>{{ equipo.codigo_equipo }}</strong> - {{ equipo.nombre_equipo }}
                </li>
                {% endfor %}
            </ul>

            <div class="alert alert-danger">
                <strong>⚠️ ADVERTENCIA:</strong> Esta acción NO se puede deshacer.
                Todos los datos asociados (calibraciones, mantenimientos, documentos)
                también serán eliminados.
            </div>

            <form method="POST">
                {% csrf_token %}
                {% for equipo in equipos %}
                <input type="hidden" name="equipos_ids[]" value="{{ equipo.id }}">
                {% endfor %}

                <div class="d-flex justify-content-between">
                    <a href="{% url 'core:equipos_list' %}" class="btn btn-secondary">
                        <i class="fas fa-times"></i> Cancelar
                    </a>
                    <button type="submit" class="btn btn-danger">
                        <i class="fas fa-trash"></i> Sí, Eliminar {{ equipos.count }} Equipo(s)
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
```

### ✅ Resultado Esperado

- ✅ Solo Gerente y SuperUsuario ven botones de eliminar
- ✅ Checkboxes para seleccionar múltiples equipos
- ✅ Botón "Eliminar Seleccionados" con contador
- ✅ Confirmación antes de eliminar
- ✅ Eliminación masiva eficiente
- ✅ Otros roles no tienen acceso a eliminación

---

## 📊 RESUMEN DE CAMBIOS

### Archivos Nuevos
- `core/static/js/session_keepalive.js`
- `templates/core/equipos/equipos_confirm_delete_masivo.html`

### Archivos Modificados
- `core/middleware.py` - Agregar SessionActivityMiddleware
- `proyecto_c/settings.py` - Configuración de sesión
- `templates/base.html` - Agregar script de keepalive
- `core/views/equipment.py` - Navegación entre equipos y eliminación masiva
- `core/views/auth_views.py` - Endpoint de heartbeat
- `core/models.py` - Método `puede_eliminar_equipos()`
- `core/urls.py` - URLs de heartbeat y eliminación
- `templates/core/equipos/equipo_form.html` - Botones de navegación
- `templates/core/equipos/equipos_list.html` - Selección masiva

### Base de Datos
- ✅ No requiere migraciones (solo lógica)

---

## 🧪 PLAN DE TESTING

### Test 1: Auto-Logout Inteligente
```python
# tests/test_session_activity.py
def test_session_extends_with_activity(authenticated_client):
    """Test que sesión se extiende con actividad"""
    # Hacer request
    response = authenticated_client.get('/core/dashboard/')
    assert 'last_activity' in authenticated_client.session

    # Verificar que sesión no expira inmediatamente
    time.sleep(2)
    response = authenticated_client.get('/core/equipos/')
    assert response.status_code == 200  # No redirige a login
```

### Test 2: Navegación entre Equipos
```python
def test_navegacion_siguiente_equipo(authenticated_client, empresa_factory):
    """Test navegación a siguiente equipo"""
    empresa = empresa_factory()
    equipo1 = Equipo.objects.create(empresa=empresa, codigo='EQ-001')
    equipo2 = Equipo.objects.create(empresa=empresa, codigo='EQ-002')

    response = authenticated_client.post(
        f'/core/equipos/{equipo1.id}/editar/',
        {'save_and_next': True, ...}
    )

    # Debe redirigir a equipo2
    assert response.url == f'/core/equipos/{equipo2.id}/editar/'
```

### Test 3: Permisos de Eliminación
```python
def test_tecnico_no_puede_eliminar(authenticated_client):
    """Test que técnico no puede eliminar equipos"""
    user = authenticated_client.user
    user.rol = 'tecnico'
    user.save()

    equipo = Equipo.objects.create(...)
    response = authenticated_client.get(f'/core/equipos/{equipo.id}/eliminar/')

    # Debe redirigir por falta de permisos
    assert response.status_code == 302

def test_gerente_puede_eliminar(authenticated_client):
    """Test que gerente SÍ puede eliminar equipos"""
    user = authenticated_client.user
    user.rol = 'gerente'
    user.save()

    equipo = Equipo.objects.create(...)
    response = authenticated_client.post(f'/core/equipos/{equipo.id}/eliminar/')

    # Debe eliminar exitosamente
    assert not Equipo.objects.filter(id=equipo.id).exists()
```

---

## 📅 CRONOGRAMA DE IMPLEMENTACIÓN

### Semana 1 (20-24 Nov 2025)
- **Día 1-2:** Implementar Auto-Logout Inteligente
  - Middleware de activity tracking
  - JavaScript heartbeat
  - Endpoint de heartbeat
  - Testing local

- **Día 3-4:** Implementar Navegación entre Equipos
  - Modificar vista de edición
  - Agregar botones anterior/siguiente
  - Implementar atajos de teclado
  - Testing local

- **Día 5:** Code review y ajustes

### Semana 2 (25-29 Nov 2025)
- **Día 1-2:** Implementar Permisos y Eliminación Masiva
  - Agregar método `puede_eliminar_equipos()`
  - Vista de eliminación individual
  - Vista de eliminación masiva
  - Templates de confirmación

- **Día 3:** Testing exhaustivo
  - Tests unitarios
  - Tests de integración
  - Testing manual en desarrollo

- **Día 4:** Documentación y preparación para deploy

- **Día 5:** Deploy a producción y monitoreo

---

## 🚀 DEPLOYMENT

### Checklist Pre-Deploy
- [ ] Todos los tests pasando (pytest)
- [ ] Code review completado
- [ ] Documentación actualizada
- [ ] Variables de entorno verificadas
- [ ] Backup de base de datos
- [ ] Plan de rollback preparado

### Comando de Deploy
```bash
cd C:\Users\LENOVO\OneDrive\Escritorio\sam-2

# Verificar cambios
git status
git diff

# Crear commit
git add .
git commit -m "feat: Mejoras UX - Auto-logout inteligente, navegación rápida, eliminación masiva

- Implementa SessionActivityMiddleware para detectar actividad
- Agrega heartbeat JS para mantener sesión activa
- Botones Anterior/Siguiente en edición de equipos
- Permisos de eliminación solo para Gerente/SuperUsuario
- Eliminación masiva con selección múltiple
- Tests agregados para todas las funcionalidades

Ref: auditorias/PLAN_MEJORAS_UX_2025-11-19.md"

# Push a producción
git push origin main
```

### Verificación Post-Deploy
1. ✅ Sesión no se cierra con actividad
2. ✅ Botones de navegación funcionan
3. ✅ Solo Gerente/SuperUsuario ven opción de eliminar
4. ✅ Eliminación masiva funciona correctamente
5. ✅ No hay errores en logs de Render

---

## 📞 CONTACTO Y SEGUIMIENTO

**Solicitado por:** Usuario
**Planificado por:** Equipo de desarrollo
**Fecha:** 19 de Noviembre de 2025
**Estado:** 📋 PLANIFICADO - Listo para implementación

---

**¿Aprobado para implementación?** Por favor confirma si este plan cumple con tus expectativas.
