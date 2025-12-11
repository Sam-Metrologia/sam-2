# Manual de Usuario - SAM Metrología

## Descripción

Este directorio contiene el **Manual de Usuario** interactivo y didáctico para la plataforma SAM Metrología.

### Identidad Visual

- **Colores Corporativos**: Gris Slate (#334155) + Azul Eléctrico (#3B82F6)
- **Estilo**: Moderno, elegante y profesional
- **Formato**: HTML responsivo convertible a PDF de alta calidad

## Estructura del Proyecto

```
manual-usuario/
├── index.html                    # Manual principal (HTML)
├── README.md                     # Este archivo
├── assets/
│   ├── css/
│   │   └── manual-styles.css    # Estilos corporativos SAM
│   ├── images/                   # Capturas de pantalla (vacío por ahora)
│   └── js/                       # Scripts si es necesario
└── secciones/                    # Secciones modulares (futuro)
```

## Secciones del Manual

1. ✅ **Introducción al Sistema** - Qué es SAM, beneficios, módulos
2. ✅ **Acceso y Navegación** - Login, menú, navegación básica
3. 🚧 **Creación de Equipos** - Registro paso a paso
4. 🚧 **Gestión de Calibraciones** - Carga de certificados
5. 🚧 **Confirmación Metrológica** - Análisis de aptitud
6. 🚧 **Comprobación Intermedia** - Verificaciones internas
7. 🚧 **Mantenimiento de Equipos** - Programación y seguimiento
8. 🚧 **Intervalos de Calibración** - Métodos ILAC G-24:2022
9. 🚧 **Generación de Reportes** - PDFs, Excel, ZIPs
10. 🚧 **Baja de Equipos** - Proceso de retiro
11. 🚧 **Preguntas Frecuentes** - FAQ y solución de problemas

## Cómo Visualizar

### Opción 1: Navegador Web (Recomendado)

```bash
# Abrir directamente en el navegador
start index.html  # Windows
open index.html   # macOS
xdg-open index.html  # Linux
```

### Opción 2: Servidor Local

```bash
# Python 3
python -m http.server 8000

# Luego abrir: http://localhost:8000
```

## Cómo Generar PDF

### Método 1: WeasyPrint (Alta Calidad - Recomendado)

```bash
# Instalar WeasyPrint
pip install weasyprint

# Generar PDF
weasyprint index.html manual-sam-metrologia.pdf

# Con marcadores de sección
weasyprint --presentational-hints index.html manual-sam-metrologia.pdf
```

### Método 2: Desde el Navegador (Rápido)

1. Abrir `index.html` en Chrome/Edge
2. `Ctrl + P` o `Cmd + P`
3. Configurar:
   - Destino: **Guardar como PDF**
   - Diseño: **Vertical**
   - Márgenes: **Predeterminados**
   - Opciones: ✅ **Gráficos de fondo**
4. Guardar como `manual-sam-metrologia.pdf`

### Método 3: Herramientas Online

- [HTML to PDF Converter](https://www.sejda.com/html-to-pdf)
- [PDF Crowd](https://pdfcrowd.com/)

## Próximos Pasos

### Para Desarrolladores

1. **Capturar Screenshots**: Tomar capturas de pantalla de cada proceso
   ```bash
   # Guardar en: assets/images/
   # Nombrar: seccion-X-paso-Y.png
   # Ejemplo: seccion-3-paso-1-crear-equipo.png
   ```

2. **Completar Secciones**: Desarrollar las secciones 3-11 con el mismo formato
   - Copiar estructura de pasos numerados
   - Incluir cajas de información (tip-box, warning-box)
   - Agregar tablas de referencia cuando sea necesario

3. **Optimizar para Impresión**: Ajustar `@page` y `@media print` en CSS

### Para Diseñadores

1. **Crear Iconografía**: Diseñar iconos personalizados SAM
2. **Ilustraciones**: Agregar diagramas de flujo de procesos
3. **Infografías**: Crear visualizaciones de conceptos metrológicos

## Guía de Estilo

### Colores

```css
Primario:     #334155 (Gris Slate)
Acento:       #3B82F6 (Azul Eléctrico)
Éxito:        #10B981 (Verde)
Advertencia:  #F59E0B (Amarillo)
Error:        #EF4444 (Rojo)
Info:         #3B82F6 (Azul)
```

### Tipografía

- **Fuente principal**: Inter (Google Fonts)
- **Fuente monoespaciada**: JetBrains Mono
- **Tamaño base**: 11pt
- **Line height**: 1.7

### Componentes Reutilizables

#### Paso Numerado
```html
<div class="step">
    <div class="step-number">1</div>
    <div class="step-content">
        <div class="step-title">Título del paso</div>
        <div class="step-description">Descripción</div>
    </div>
</div>
```

#### Caja de Consejo
```html
<div class="tip-box">
    <div class="box-title">
        <i class="fas fa-lightbulb"></i>
        Consejo
    </div>
    <p>Contenido del consejo...</p>
</div>
```

#### Caja de Advertencia
```html
<div class="warning-box">
    <div class="box-title">
        <i class="fas fa-exclamation-triangle"></i>
        Importante
    </div>
    <p>Mensaje importante...</p>
</div>
```

## Convenciones

- ✅ Sección completada
- 🚧 Sección en desarrollo
- 📸 Necesita capturas de pantalla
- 📝 Necesita revisión de contenido

## Contacto

Para sugerencias o mejoras al manual:
- **Email**: metrologiasam@gmail.com
- **Web**: https://sam-9o6o.onrender.com

---

**Versión**: 8.5
**Última actualización**: Diciembre 2025
**Normas**: ISO 17020:2012, ISO 17025:2017, ISO 10012:2003, ILAC G-24:2022
