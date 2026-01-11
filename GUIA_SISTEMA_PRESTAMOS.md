# 📚 Guía Rápida - Sistema de Préstamos de Equipos

## ✅ Permisos Asignados

Los permisos se han asignado exitosamente a:
- **CERTI** (villy@gmail.com)
- **CERTIBOY** (certiboy@test.com)

---

## 🚀 Cómo Acceder al Sistema

### 1. Iniciar el Servidor de Desarrollo

```bash
cd C:\Users\LENOVO\OneDrive\Escritorio\sam-2
python manage.py runserver
```

### 2. Abrir el Navegador

Ve a: `http://localhost:8000`

### 3. Iniciar Sesión

Usa tus credenciales (CERTI o CERTIBOY)

### 4. Buscar el Menú "Préstamos"

En el **sidebar izquierdo**, verás un nuevo elemento:

```
📋 Préstamos
```

**IMPORTANTE:** Si no ves el menú, presiona `Ctrl + F5` para recargar la página completamente.

---

## 📍 Ubicaciones del Sistema

### En el Menú Principal (Sidebar)
- **Préstamos** → Lleva al Dashboard de Préstamos

### En el Dashboard Principal
- Tarjeta **"Préstamos Activos"** con botón "Ver Dashboard"

---

## 🎯 Funcionalidades Disponibles

### 1. **Dashboard de Préstamos** (`/prestamos/dashboard/`)
- Vista colapsable por prestatario
- Estadísticas: total activos, vencidos, próximos
- Ver todos los equipos prestados por persona

### 2. **Lista de Préstamos** (`/prestamos/`)
- Ver todos los préstamos
- Filtros por estado (Activo, Devuelto, Vencido)
- Búsqueda por equipo o prestatario
- Paginación

### 3. **Crear Préstamo** (`/prestamos/nuevo/`)
- Seleccionar equipo disponible
- Datos del prestatario:
  - Nombre (requerido)
  - Cédula
  - Cargo
  - Email
  - Teléfono
  - Fecha de devolución programada
  - Observaciones

### 4. **Ver Detalle** (`/prestamos/<id>/`)
- Información completa del préstamo
- Datos del equipo
- Datos del prestatario
- Fechas
- Responsables
- Observaciones

### 5. **Devolver Equipo** (`/prestamos/<id>/devolver/`)
- Verificación funcional:
  - Verificado por (técnico que recibe)
  - Condición del equipo (Bueno/Regular/Malo)
  - Verificación funcional (Conforme/No Conforme)
- Observaciones de devolución
- Opcional: Subir documento PDF

---

## 📝 Ejemplo de Flujo Completo

### Crear un Préstamo

1. **Ir a Préstamos** (sidebar) → **+ Nuevo Préstamo**

2. **Seleccionar Equipo**
   - Solo aparecen equipos **Activos** sin préstamo

3. **Llenar Datos del Prestatario**
   ```
   Nombre: Juan Pérez
   Cédula: 1234567890
   Cargo: Técnico de Laboratorio
   Email: juan@empresa.com
   Teléfono: 3001234567
   Devolución: 07/01/2026 (7 días adelante)
   ```

4. **Guardar** → Se crea el préstamo

5. **Ver en Dashboard** → Aparece en la sección de Juan Pérez

### Devolver un Equipo

1. **Ir a Préstamos** → **Ver** (botón del préstamo)

2. **Click en "Devolver Equipo"**

3. **Llenar Verificación**
   ```
   Verificado por: Técnico Receptor
   Condición: Bueno - Sin daños
   Verificación: Conforme - Funciona correctamente
   Observaciones: Equipo devuelto en perfectas condiciones
   ```

4. **Confirmar Devolución** → Estado cambia a "Devuelto"

---

## 🔔 Alertas y Notificaciones

### En el Dashboard Principal

- **Contador Verde**: Préstamos activos totales
- **Alerta Roja**: Préstamos vencidos (no devueltos a tiempo)
- **Alerta Amarilla**: Devoluciones próximas (siguientes 7 días)

### En el Dashboard de Préstamos

- **Badge Azul**: Cantidad de equipos por persona
- **Badge Rojo**: Equipos vencidos de esa persona

---

## ⚠️ Validaciones Importantes

### No se Puede:
1. ❌ Prestar un equipo que ya está prestado (activo)
2. ❌ Ver préstamos de otra empresa (multi-tenant)
3. ❌ Devolver un préstamo ya devuelto
4. ❌ Acceder sin permisos

### Sí se Puede:
1. ✅ Prestar múltiples equipos a la misma persona
2. ✅ Volver a prestar un equipo que ya fue devuelto
3. ✅ Ver historial completo de préstamos
4. ✅ Buscar y filtrar préstamos

---

## 🎨 Navegación Rápida

### Desde el Dashboard Principal
```
Dashboard → Tarjeta "Préstamos Activos" → Ver Dashboard
```

### Desde el Menú
```
Sidebar → Préstamos → Seleccionar opción
```

### Atajos de Teclado (en lista)
- `Ctrl + F` → Buscar
- `Enter` → Aplicar filtro

---

## 🔧 Troubleshooting

### No veo el menú "Préstamos"

**Solución:**
1. Presiona `Ctrl + F5` para recargar
2. Cierra sesión y vuelve a iniciar
3. Verifica que tengas permisos (ya asignados)

### Error al crear préstamo

**Posibles causas:**
- Equipo ya está prestado → Selecciona otro
- Falta nombre del prestatario → Campo obligatorio
- Fecha inválida → Usa formato dd/mm/aaaa

### No puedo devolver un equipo

**Verifica:**
- El préstamo esté en estado "ACTIVO"
- Tengas permiso `can_change_prestamo`
- El equipo no esté ya devuelto

---

## 📊 Permisos Asignados

Los siguientes permisos están activos:

✅ `can_view_prestamo` - Ver préstamos
✅ `can_add_prestamo` - Crear préstamos
✅ `can_change_prestamo` - Modificar/devolver préstamos
✅ `can_delete_prestamo` - Eliminar préstamos
✅ `can_view_all_prestamos` - Ver todos los préstamos de la empresa

---

## 📞 Soporte

Si encuentras algún problema:
1. Revisa esta guía
2. Verifica los logs del servidor
3. Ejecuta: `python manage.py check`

---

## 🎉 ¡Listo para Usar!

El sistema está completamente funcional. Accede a:

**http://localhost:8000** → Inicia sesión → **Préstamos**

¡Disfruta del nuevo sistema de control de préstamos! 🚀
