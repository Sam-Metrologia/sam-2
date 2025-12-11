#!/usr/bin/env python3
"""
Script para generar PDF del Manual de Usuario SAM Metrología
Utiliza WeasyPrint para convertir HTML a PDF de alta calidad
"""

import os
import sys
from pathlib import Path

def verificar_dependencias():
    """Verifica que WeasyPrint esté instalado"""
    try:
        import weasyprint
        print("[OK] WeasyPrint esta instalado")
        return True
    except ImportError:
        print("[ERROR] WeasyPrint no esta instalado")
        print("\nPara instalar, ejecute:")
        print("  pip install weasyprint")
        print("\nEn Windows, puede necesitar instalar GTK3:")
        print("  https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer")
        return False

def generar_pdf(archivo_html="index.html", archivo_salida="Manual-SAM-Metrologia.pdf"):
    """
    Genera PDF a partir del archivo HTML

    Args:
        archivo_html: Ruta al archivo HTML fuente
        archivo_salida: Nombre del archivo PDF de salida
    """
    from weasyprint import HTML, CSS

    # Obtener ruta absoluta
    directorio_actual = Path(__file__).parent
    ruta_html = directorio_actual / archivo_html
    ruta_pdf = directorio_actual / archivo_salida

    if not ruta_html.exists():
        print(f"[ERROR] No se encontro el archivo {archivo_html}")
        return False

    print(f"[PDF] Generando PDF desde: {archivo_html}")
    print(f"[DEST] Destino: {archivo_salida}")

    try:
        # CSS adicional para mejorar el PDF
        css_pdf = CSS(string='''
            @page {
                size: A4;
                margin: 2cm 1.5cm;
            }

            /* Evitar cortes de página en elementos importantes */
            .step, .feature-card, .info-box, .tip-box, .warning-box {
                page-break-inside: avoid;
            }

            /* Asegurar que las secciones empiecen en página nueva */
            .section {
                page-break-before: always;
            }

            /* Primera sección no necesita salto */
            .section:first-of-type {
                page-break-before: auto;
            }

            /* Ocultar elementos no imprimibles */
            .no-print {
                display: none;
            }
        ''')

        # Generar PDF
        html_doc = HTML(filename=str(ruta_html))
        html_doc.write_pdf(
            str(ruta_pdf),
            stylesheets=[css_pdf],
            presentational_hints=True
        )

        # Obtener tamaño del archivo
        tamaño_mb = ruta_pdf.stat().st_size / (1024 * 1024)

        print(f"\n[OK] PDF generado exitosamente!")
        print(f"[INFO] Tamano: {tamaño_mb:.2f} MB")
        print(f"[INFO] Ubicacion: {ruta_pdf.absolute()}")

        return True

    except Exception as e:
        print(f"\n[ERROR] Error al generar PDF: {str(e)}")
        return False

def main():
    """Función principal"""
    print("=" * 60)
    print("  GENERADOR DE PDF - MANUAL SAM METROLOGÍA")
    print("=" * 60)
    print()

    # Verificar dependencias
    if not verificar_dependencias():
        sys.exit(1)

    # Generar PDF
    exito = generar_pdf()

    if exito:
        print("\n" + "=" * 60)
        print("  [EXITO] Generacion completada exitosamente")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("  [FALLO] Generacion fallida")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()
