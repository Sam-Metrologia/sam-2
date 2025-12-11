# 📘 Guía para Completar el Manual de Usuario SAM Metrología

## ✅ Estado Actual del Proyecto

### Completado (100%)

- ✅ **Estructura de carpetas** creada
- ✅ **Identidad visual** definida (Gris Slate #334155 + Azul Eléctrico #3B82F6)
- ✅ **Sistema de estilos CSS** corporativo completo
- ✅ **Plantilla HTML base** con diseño elegante y profesional
- ✅ **Secciones 1 y 2** completadas:
  - Introducción al Sistema
  - Acceso y Navegación
- ✅ **Script de generación PDF** funcional
- ✅ **PDF de prueba** generado exitosamente (60 KB)

### Pendiente (Secciones 3-11)

- 🚧 Sección 3: Creación de Equipos
- 🚧 Sección 4: Gestión de Calibraciones
- 🚧 Sección 5: Confirmación Metrológica
- 🚧 Sección 6: Comprobación Intermedia
- 🚧 Sección 7: Mantenimiento de Equipos
- 🚧 Sección 8: Intervalos de Calibración
- 🚧 Sección 9: Generación de Reportes
- 🚧 Sección 10: Baja de Equipos
- 🚧 Sección 11: Preguntas Frecuentes

## 📁 Archivos del Proyecto

```
manual-usuario/
├── index.html                         ✅ Manual principal (HTML interactivo)
├── Manual-SAM-Metrologia.pdf          ✅ PDF generado
├── generar_pdf.py                     ✅ Script automatización PDF
├── README.md                          ✅ Documentación técnica
├── PLANTILLA-SECCION.html             ✅ Template para nuevas secciones
├── GUIA-COLORES.html                  ✅ Referencia visual de colores
├── COMO-COMPLETAR-EL-MANUAL.md        ✅ Este archivo
└── assets/
    ├── css/
    │   └── manual-styles.css          ✅ Estilos corporativos
    ├── images/                        📸 [VACÍO] Para capturas de pantalla
    └── js/                            (Opcional) Scripts adicionales
```

## 🎨 Identidad Visual SAM

### Paleta de Colores

| Uso | Color | Hex | Aplicación |
|-----|-------|-----|------------|
| **Primario** | Gris Slate | `#334155` | Títulos, texto, fondos |
| **Acento** | Azul Eléctrico | `#3B82F6` | Botones, enlaces, destacados |
| **Acento Claro** | Azul Claro | `#60A5FA` | Hover states |
| **Acento Oscuro** | Azul Oscuro | `#2563EB` | Active states |
| **Éxito** | Verde | `#10b981` | Confirmaciones |
| **Advertencia** | Amarillo | `#f59e0b` | Alertas |
| **Error** | Rojo | `#ef4444` | Errores |
| **Info** | Azul | `#3b82f6` | Información |

### Tipografía

- **Fuente**: Inter (Google Fonts)
- **Tamaño base**: 11pt
- **Interlineado**: 1.7

## 🚀 Cómo Completar las Secciones Pendientes

### Paso 1: Tomar Capturas de Pantalla

Para cada proceso que vas a documentar:

1. **Accede a la plataforma**: https://sam-9o6o.onrender.com
2. **Realiza el proceso** que vas a documentar (ej: crear equipo)
3. **Captura cada paso importante** (usar Snipping Tool en Windows o Cmd+Shift+4 en Mac)
4. **Nombra los archivos** según convención:
   ```
   seccion-3-paso-1-menu-equipos.png
   seccion-3-paso-2-boton-crear.png
   seccion-3-paso-3-formulario.png
   seccion-3-paso-4-confirmacion.png
   ```
5. **Guarda en**: `manual-usuario/assets/images/`

### Paso 2: Escribir el Contenido

1. **Abre** `PLANTILLA-SECCION.html` como referencia
2. **Edita** `index.html`
3. **Busca** la sección placeholder (ej: "Sección 3")
4. **Reemplaza** con contenido real usando la plantilla

#### Estructura Recomendada por Sección

**Sección 3: Creación de Equipos**
```html
<div class="section" id="seccion-3">
    <div class="section-header">
        <h2>
            <span class="section-number">3</span>
            <span class="section-title">Creación de Equipos</span>
        </h2>
        <p class="section-subtitle">Registre nuevos equipos de medición</p>
    </div>

    <h3>Proceso Paso a Paso</h3>
    <div class="steps-container">
        <div class="step">
            <div class="step-number">1</div>
            <div class="step-content">
                <div class="step-title">Acceda al módulo Equipos</div>
                <div class="step-description">
                    En el menú lateral, haga clic en <strong>Equipos</strong>
                </div>
                <div class="step-screenshot">
                    <img src="assets/images/seccion-3-paso-1.png" alt="Menú Equipos">
                </div>
            </div>
        </div>

        <div class="step">
            <div class="step-number">2</div>
            <div class="step-content">
                <div class="step-title">Haga clic en "Añadir Equipo"</div>
                <div class="step-description">
                    Ubique el botón azul en la parte superior derecha
                </div>
                <div class="step-screenshot">
                    <img src="assets/images/seccion-3-paso-2.png" alt="Botón Añadir">
                </div>
            </div>
        </div>

        <!-- Continuar con más pasos... -->
    </div>

    <h3>Campos del Formulario</h3>
    <table>
        <thead>
            <tr>
                <th>Campo</th>
                <th>Descripción</th>
                <th>Obligatorio</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>Código Interno</strong></td>
                <td>Identificador único del equipo (ej: BAL-001)</td>
                <td>Sí</td>
            </tr>
            <tr>
                <td><strong>Nombre</strong></td>
                <td>Descripción del equipo</td>
                <td>Sí</td>
            </tr>
            <!-- Más campos... -->
        </tbody>
    </table>

    <div class="tip-box">
        <div class="box-title">
            <i class="fas fa-lightbulb"></i>
            Consejo: Código Interno
        </div>
        <p style="margin-top: 0.5rem; margin-bottom: 0;">
            Use códigos cortos y descriptivos. Ejemplo: BAL-001 para balanzas,
            TERM-001 para termómetros.
        </p>
    </div>
</div>
```

### Paso 3: Regenerar el PDF

Después de completar cada sección:

```bash
# Opción 1: Script Python
cd manual-usuario
python generar_pdf.py

# Opción 2: Navegador (más rápido para pruebas)
# Abrir index.html en Chrome > Ctrl+P > Guardar como PDF
```

### Paso 4: Revisar Calidad

Antes de dar por terminada una sección, verifica:

- ✅ Las capturas de pantalla se ven nítidas
- ✅ El texto es claro y conciso (sin jerga técnica excesiva)
- ✅ Los pasos están numerados correctamente
- ✅ Hay al menos 1 caja de consejo o advertencia por sección
- ✅ Las tablas tienen toda la información necesaria
- ✅ El PDF se genera sin errores

## 📝 Plantillas de Contenido

### Caja de Consejo (Uso frecuente)
```html
<div class="tip-box">
    <div class="box-title">
        <i class="fas fa-lightbulb"></i>
        Consejo Útil
    </div>
    <p style="margin-top: 0.5rem; margin-bottom: 0;">
        Texto del consejo...
    </p>
</div>
```

### Caja de Advertencia (Precauciones)
```html
<div class="warning-box">
    <div class="box-title">
        <i class="fas fa-exclamation-triangle"></i>
        Importante
    </div>
    <p style="margin-top: 0.5rem; margin-bottom: 0;">
        Mensaje de precaución...
    </p>
</div>
```

### Caja de Información (Datos adicionales)
```html
<div class="info-box">
    <div class="box-title">
        <i class="fas fa-info-circle"></i>
        Información
    </div>
    <p style="margin-top: 0.5rem; margin-bottom: 0;">
        Información adicional...
    </p>
</div>
```

### Tabla de Referencia
```html
<table>
    <thead>
        <tr>
            <th>Columna 1</th>
            <th>Columna 2</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Dato 1</td>
            <td>Dato 2</td>
        </tr>
    </tbody>
</table>
```

## 🎯 Contenido Sugerido por Sección

### Sección 3: Creación de Equipos
- Acceso al módulo
- Click en "Añadir Equipo"
- Campos del formulario (código, nombre, tipo, marca, modelo, serie)
- Ubicación y responsable
- Características técnicas (rango, resolución, EMP)
- Carga de imagen del equipo
- Guardar y confirmar

### Sección 4: Gestión de Calibraciones
- Acceder a detalle del equipo
- Click en "Añadir Calibración"
- Fecha de calibración
- Fecha próxima calibración (intervalo)
- Entidad calibradora
- Número de certificado
- Subir PDF del certificado
- Resultado (Conforme/No Conforme)
- Observaciones

### Sección 5: Confirmación Metrológica
- Qué es la confirmación metrológica (ISO 10012:2003)
- Acceso desde detalle del equipo
- Análisis de aptitud
- Comparación error vs EMP
- Decisión (Apto/No Apto)
- Generación de PDF de confirmación

### Sección 6: Comprobación Intermedia
- Qué es comprobación intermedia
- Cuándo realizarla
- Cargar documento externo o crear informe interno
- Resultados de verificación
- Conclusiones
- PDF de comprobación

### Sección 7: Mantenimiento
- Acceso a mantenimiento
- Tipos de mantenimiento (preventivo/correctivo)
- Actividades realizadas
- Repuestos utilizados
- Próximo mantenimiento
- Generación de reporte

### Sección 8: Intervalos de Calibración
- Métodos disponibles (Manual, Predictivo, Escalera, Carta Control, Tiempo Uso)
- Método Predictivo Multifactorial (ILAC G-24:2022)
- Método Escalera
- Método Carta de Control
- Método Tiempo en Uso
- Cómo interpretar resultados
- Aplicar intervalo calculado

### Sección 9: Generación de Reportes
- Hoja de vida PDF
- Informe de vencimientos
- Exportar equipos a Excel
- Dashboard PDF
- Análisis financiero
- Solicitar ZIP masivo
- Descargar reportes

### Sección 10: Baja de Equipos
- Cuándo dar de baja un equipo
- Proceso de baja
- Motivo de baja
- Confirmación
- Registro histórico
- Verificar estado

### Sección 11: Preguntas Frecuentes
- ¿Cómo recupero mi contraseña?
- ¿Puedo editar una calibración?
- ¿Qué significa "No Conforme"?
- ¿Cómo agrego usuarios?
- ¿Puedo eliminar un equipo?
- ¿Los datos son seguros?
- ¿Funciona en móvil?
- ¿Hay límite de equipos?

## ✨ Consejos de Redacción

### ✅ HACER
- Usar lenguaje simple y directo
- Incluir muchas capturas de pantalla
- Enumerar pasos claramente
- Destacar información importante con cajas
- Usar tablas para resumir datos
- Agregar consejos prácticos
- Mencionar atajos de teclado cuando aplique

### ❌ EVITAR
- Jerga técnica innecesaria
- Párrafos largos (máximo 3-4 líneas)
- Instrucciones ambiguas ("luego hace clic en algo")
- Capturas borrosas o con información sensible
- Omitir pasos importantes
- Asumir conocimiento previo

## 🔧 Herramientas Útiles

### Para Capturas de Pantalla
- **Windows**: Snipping Tool (Win + Shift + S)
- **Mac**: Cmd + Shift + 4
- **Extensión Chrome**: Awesome Screenshot

### Para Editar Imágenes
- **Paint** (básico, incluido en Windows)
- **Paint.NET** (gratis, más funciones)
- **Photopea** (online, gratis)

### Para Revisar PDF
- **Adobe Acrobat Reader** (visor estándar)
- **Navegador web** (Chrome, Edge, Firefox)

## 📊 Estimación de Trabajo

| Sección | Pasos Estimados | Tiempo Aproximado |
|---------|-----------------|-------------------|
| 3. Creación Equipos | 8-10 | 2-3 horas |
| 4. Calibraciones | 6-8 | 1.5-2 horas |
| 5. Confirmación | 5-6 | 1-1.5 horas |
| 6. Comprobación | 5-6 | 1-1.5 horas |
| 7. Mantenimiento | 6-8 | 1.5-2 horas |
| 8. Intervalos | 10-12 | 3-4 horas |
| 9. Reportes | 8-10 | 2-3 horas |
| 10. Baja Equipos | 4-5 | 1 hora |
| 11. FAQ | 15-20 | 2-3 horas |

**Total estimado**: 15-20 horas de trabajo

## 🎓 Recursos de Apoyo

- **Plataforma SAM**: https://sam-9o6o.onrender.com
- **Iconos Font Awesome**: https://fontawesome.com/v6/icons
- **Google Fonts (Inter)**: https://fonts.google.com/specimen/Inter
- **WeasyPrint Docs**: https://doc.courtbouillon.org/weasyprint/

## ✅ Checklist de Finalización

Cuando completes el manual, verifica:

- [ ] Todas las secciones (3-11) completadas
- [ ] Todas las capturas de pantalla incluidas y nítidas
- [ ] PDF genera sin errores
- [ ] Tabla de contenidos actualizada con páginas correctas
- [ ] Colores corporativos usados consistentemente
- [ ] Información de contacto y versión actualizadas
- [ ] Manual revisado por al menos 2 personas
- [ ] Probado en navegadores: Chrome, Firefox, Edge
- [ ] PDF probado en lectores: Adobe Reader, navegador
- [ ] Tamaño final razonable (< 10 MB recomendado)

## 📧 Soporte

Si tienes dudas durante el desarrollo:
- **Email**: metrologiasam@gmail.com
- **Plataforma**: https://sam-9o6o.onrender.com

---

**Última actualización**: Diciembre 2025
**Versión del manual**: 8.5
**Estado**: Base completada - Contenido en desarrollo
