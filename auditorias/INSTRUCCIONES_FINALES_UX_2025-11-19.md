# INSTRUCCIONES FINALES - Mejoras UX SAM
**Fecha:** 19 de Noviembre de 2025
**Estado:** 75% COMPLETADO - Faltan ajustes finales

---

## ✅ COMPLETADO (75%)

### 1. ✅ Auto-Logout Inteligente - 100%
- ✅ Middleware SessionActivityMiddleware
- ✅ JavaScript de heartbeat
- ✅ Endpoint `/core/session-heartbeat/`
- ✅ Script agregado en base.html
- ✅ Configuración en settings.py

### 2. ✅ Permisos de Eliminación - 100%
- ✅ Método `puede_eliminar_equipos()` en CustomUser
- ✅ Solo ADMINISTRADOR, GERENCIA y SuperUsuario pueden eliminar

### 3. ✅ Navegación entre Equipos (Backend) - 100%
- ✅ Lógica implementada en `editar_equipo()`
- ✅ Detecta equipos anterior/siguiente
- ✅ Guarda y navega automáticamente
- ⏳ FALTA: Actualizar template HTML

---

## ⏳ PENDIENTE (25%)

### 4. Template de Edición de Equipos
**Archivo:** `templates/core/editar_equipo.html`

**Agregar botones de navegación:**

```html
<!-- Agregar en el header del formulario -->
<div class="card-header d-flex justify-content-between align-items-center">
    <h3>Editar Equipo: {{ equipo.codigo_interno }}</h3>

    <!-- Indicador de posición -->
    {% if current_position and total_equipos %}
    <span class="badge bg-info">
        Equipo {{ current_position }} de {{ total_equipos }}
    </span>
    {% endif %}
</div>

<!-- Reemplazar los botones de guardado con esto -->
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
        <a href="{% url 'core:home' %}" class="btn btn-secondary">
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

<!-- Atajos de teclado (agregar al final del formulario) -->
<div class="text-center mt-3">
    <small class="text-muted">
        💡 Tip: Usa <kbd>Ctrl</kbd> + <kbd>←</kbd> para anterior,
        <kbd>Ctrl</kbd> + <kbd>→</kbd> para siguiente
    </small>
</div>

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

---

### 5. Eliminación Masiva de Equipos

#### A. Modificar vista de eliminación individual

**Archivo:** `core/views/equipment.py` - Función `eliminar_equipo`

**REEMPLAZAR LA FUNCIÓN COMPLETA:**

```python
@access_check
@login_required
@trial_check
@monitor_view
def eliminar_equipo(request, pk):
    """
    Elimina un equipo individual.
    Solo ADMINISTRADOR, GERENCIA y SuperUsuario pueden eliminar.
    """
    # Verificar permisos usando el método del modelo
    if not request.user.puede_eliminar_equipos():
        messages.error(request, 'No tienes permisos para eliminar equipos.')
        return redirect('core:home')

    equipo = get_object_or_404(Equipo, pk=pk)

    # Verificar que el equipo pertenece a la empresa del usuario
    if not request.user.is_superuser:
        if equipo.empresa != request.user.empresa:
            messages.error(request, 'No tienes permiso para eliminar este equipo.')
            return redirect('core:home')

    if request.method == 'POST':
        codigo = equipo.codigo_interno
        equipo.delete()
        messages.success(request, f'Equipo {codigo} eliminado correctamente.')
        return redirect('core:home')

    return render(request, 'core/eliminar_equipo.html', {
        'equipo': equipo,
        'titulo_pagina': f'Eliminar Equipo: {equipo.codigo_interno}'
    })
```

#### B. Agregar vista de eliminación masiva

**Archivo:** `core/views/equipment.py` - AGREGAR AL FINAL DEL ARCHIVO:

```python
@access_check
@login_required
@trial_check
@monitor_view
def equipos_eliminar_masivo(request):
    """
    Vista para eliminar múltiples equipos a la vez.
    Solo ADMINISTRADOR, GERENCIA y SuperUsuario pueden eliminar.
    """
    # Verificar permisos
    if not request.user.puede_eliminar_equipos():
        messages.error(request, 'No tienes permisos para eliminar equipos.')
        return redirect('core:home')

    if request.method == 'POST':
        # Obtener IDs de equipos a eliminar
        equipos_ids = request.POST.getlist('equipos_ids[]')

        if not equipos_ids:
            messages.error(request, 'No se seleccionaron equipos para eliminar.')
            return redirect('core:home')

        # Verificar que todos los equipos pertenecen a la empresa del usuario
        empresa = request.user.empresa
        equipos = Equipo.objects.filter(
            id__in=equipos_ids,
            empresa=empresa
        )

        if not request.user.is_superuser and equipos.count() != len(equipos_ids):
            messages.error(request, 'Algunos equipos no pertenecen a tu empresa.')
            return redirect('core:home')

        # Eliminar equipos
        cantidad = equipos.count()
        equipos.delete()

        messages.success(request, f'{cantidad} equipo(s) eliminado(s) correctamente.')
        return redirect('core:home')

    # Vista GET - Confirmación
    equipos_ids = request.GET.getlist('ids')
    empresa = request.user.empresa

    if request.user.is_superuser:
        equipos = Equipo.objects.filter(id__in=equipos_ids)
    else:
        equipos = Equipo.objects.filter(
            id__in=equipos_ids,
            empresa=empresa
        )

    return render(request, 'core/equipos_eliminar_masivo.html', {
        'equipos': equipos,
        'titulo_pagina': 'Eliminar Equipos Masivamente'
    })
```

#### C. Agregar URLs

**Archivo:** `core/urls.py` - AGREGAR DESPUÉS DE LA LÍNEA DE `eliminar_equipo`:

```python
# Alrededor de la línea 41
path('equipos/<int:pk>/eliminar/', views.eliminar_equipo, name='eliminar_equipo'),
path('equipos/eliminar-masivo/', views.equipos_eliminar_masivo, name='equipos_eliminar_masivo'),  # NUEVO
```

#### D. Modificar template de lista de equipos

**Archivo:** `templates/core/home.html` (o el template donde se lista equipos)

**AGREGAR AL INICIO DE LA TABLA:**

```html
{% if user.puede_eliminar_equipos %}
<div class="mb-3">
    <button id="btn-eliminar-seleccionados" class="btn btn-danger" disabled>
        <i class="fas fa-trash"></i> Eliminar Seleccionados (<span id="count-selected">0</span>)
    </button>
</div>

<form id="form-equipos-masivo" method="POST" action="{% url 'core:equipos_eliminar_masivo' %}">
    {% csrf_token %}
{% endif %}

<!-- En el <thead> de la tabla, agregar columna de checkbox -->
<thead>
    <tr>
        {% if user.puede_eliminar_equipos %}
        <th width="50">
            <input type="checkbox" id="select-all" title="Seleccionar todos">
        </th>
        {% endif %}
        <th>Código</th>
        <!-- resto de columnas -->
    </tr>
</thead>

<!-- En cada fila del <tbody>, agregar checkbox -->
<tbody>
    {% for equipo in equipos %}
    <tr>
        {% if user.puede_eliminar_equipos %}
        <td>
            <input type="checkbox" name="equipos_ids[]"
                   value="{{ equipo.id }}"
                   class="equipo-checkbox">
        </td>
        {% endif %}
        <td>{{ equipo.codigo_interno }}</td>
        <!-- resto de columnas -->
    </tr>
    {% endfor %}
</tbody>

{% if user.puede_eliminar_equipos %}
</form>
{% endif %}

<!-- JavaScript al final del template -->
{% if user.puede_eliminar_equipos %}
<script>
document.addEventListener('DOMContentLoaded', function() {
    const selectAll = document.getElementById('select-all');
    const checkboxes = document.querySelectorAll('.equipo-checkbox');
    const btnEliminar = document.getElementById('btn-eliminar-seleccionados');
    const countSelected = document.getElementById('count-selected');
    const form = document.getElementById('form-equipos-masivo');

    // Seleccionar/deseleccionar todos
    if (selectAll) {
        selectAll.addEventListener('change', function() {
            checkboxes.forEach(cb => cb.checked = this.checked);
            updateDeleteButton();
        });
    }

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
    if (btnEliminar) {
        btnEliminar.addEventListener('click', function() {
            const selected = document.querySelectorAll('.equipo-checkbox:checked').length;
            if (confirm(`¿Seguro que deseas eliminar ${selected} equipo(s)? Esta acción no se puede deshacer.`)) {
                form.submit();
            }
        });
    }
});
</script>
{% endif %}
```

#### E. Crear template de confirmación masiva

**Crear archivo:** `templates/core/equipos_eliminar_masivo.html`

```html
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
                    <strong>{{ equipo.codigo_interno }}</strong> - {{ equipo.nombre }}
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
                    <a href="{% url 'core:home' %}" class="btn btn-secondary">
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

---

## 🧪 TESTING

### Verificación Manual

1. **Auto-Logout:**
   - Iniciar sesión
   - Dejar inactivo 25 minutos → debe mostrar advertencia
   - Mover mouse → advertencia desaparece
   - Dejar inactivo 30 minutos → debe cerrar sesión

2. **Navegación entre Equipos:**
   - Editar un equipo
   - Verificar que aparecen botones "Anterior" y "Siguiente"
   - Clic en "Guardar y Siguiente" → debe ir al siguiente
   - Probar atajos Ctrl+← y Ctrl+→

3. **Eliminación Masiva:**
   - Iniciar sesión como TÉCNICO → NO debe ver checkboxes ni botón eliminar
   - Iniciar sesión como ADMINISTRADOR → SÍ debe ver opciones
   - Seleccionar varios equipos → botón debe mostrar contador
   - Eliminar → debe confirmar y eliminar correctamente

### Comando de Prueba
```bash
cd C:\Users\LENOVO\OneDrive\Escritorio\sam-2
python manage.py runserver

# Abrir en navegador: http://localhost:8000
```

---

## 📝 RESUMEN DE ARCHIVOS MODIFICADOS

### ✅ Ya Modificados
1. `core/models.py` - Método `puede_eliminar_equipos()`
2. `core/middleware.py` - SessionActivityMiddleware
3. `proyecto_c/settings.py` - Middleware agregado
4. `core/static/core/js/session_keepalive.js` - JavaScript heartbeat
5. `core/views/base.py` - Endpoint session_heartbeat
6. `core/urls.py` - URL session-heartbeat
7. `templates/base.html` - Script keepalive
8. `core/views/equipment.py` - Función editar_equipo con navegación

### ⏳ Pendientes de Modificar
1. `templates/core/editar_equipo.html` - Botones de navegación
2. `core/views/equipment.py` - Actualizar `eliminar_equipo()` y agregar `equipos_eliminar_masivo()`
3. `core/urls.py` - Agregar URL de eliminación masiva
4. `templates/core/home.html` - Checkboxes y selección masiva
5. **CREAR NUEVO:** `templates/core/equipos_eliminar_masivo.html`

---

## 🚀 DEPLOYMENT

Cuando todo esté listo:

```bash
cd C:\Users\LENOVO\OneDrive\Escritorio\sam-2

# Verificar cambios
git status

# Crear commit
git add .
git commit -m "feat: Mejoras UX - Auto-logout, navegación rápida, eliminación masiva

- Implementa auto-logout inteligente con heartbeat
- Navegación anterior/siguiente en edición de equipos
- Permisos de eliminación por rol (ADMIN/GERENCIA/SUPER)
- Eliminación masiva con selección múltiple
- Atajos de teclado para navegación

Ref: auditorias/PLAN_MEJORAS_UX_2025-11-19.md"

# Push a producción (⚠️ AUTO-DEPLOY activo)
git push origin main
```

---

## ✅ CHECKLIST FINAL

Antes de hacer push:

- [ ] Modificar template `editar_equipo.html` con botones
- [ ] Actualizar función `eliminar_equipo()` con permisos
- [ ] Agregar función `equipos_eliminar_masivo()`
- [ ] Agregar URL de eliminación masiva
- [ ] Modificar `home.html` con checkboxes
- [ ] Crear template `equipos_eliminar_masivo.html`
- [ ] Testing manual de las 3 funcionalidades
- [ ] Verificar que no hay errores en consola del navegador
- [ ] Verificar que roles funcionan correctamente
- [ ] Crear backup de base de datos

---

**Estado: 75% COMPLETADO**
**Tiempo estimado para completar: 15-20 minutos**

Las instrucciones están claras y detalladas. Cualquier desarrollador puede seguirlas para completar la implementación.
