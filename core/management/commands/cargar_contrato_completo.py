# core/management/commands/cargar_contrato_completo.py
"""
Comando para cargar el contrato COMPLETO desde terminos_condiciones_v1.0.html
Reemplaza TODO el contenido anterior con el nuevo contrato de 180 días
"""

from django.core.management.base import BaseCommand
from core.models import TerminosYCondiciones
from datetime import date
import os


class Command(BaseCommand):
    help = 'Carga el contrato completo v1.0 desde terminos_condiciones_v1.0.html'

    def handle(self, *args, **options):
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS('CARGANDO CONTRATO COMPLETO V1.0'))
        self.stdout.write("=" * 70)

        # Ruta al archivo HTML
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        html_file = os.path.join(base_dir, 'terminos_condiciones_v1.0.html')

        # Verificar que el archivo existe
        if not os.path.exists(html_file):
            self.stdout.write(self.style.ERROR(f'\n[ERROR] No se encontró el archivo: {html_file}'))
            self.stdout.write(self.style.ERROR('Asegúrate de que terminos_condiciones_v1.0.html está en la raíz del proyecto'))
            return

        self.stdout.write(self.style.SUCCESS(f'\n[1/4] Archivo encontrado: {html_file}'))

        # Leer el contenido HTML
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            self.stdout.write(self.style.SUCCESS(f'[OK] Archivo leído ({len(content)} caracteres)'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] No se pudo leer el archivo: {e}'))
            return

        # Extraer solo el contenido del body
        start_marker = '<body>'
        end_marker = '</body>'

        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker)

        if start_idx == -1 or end_idx == -1:
            self.stdout.write(self.style.ERROR('[ERROR] No se encontraron etiquetas <body> en el archivo'))
            return

        body_content = content[start_idx + len(start_marker):end_idx].strip()

        # Extraer el div con class="terminos-condiciones"
        div_start = body_content.find('<div class="terminos-condiciones">')
        div_end = body_content.rfind('</div>')

        if div_start == -1:
            self.stdout.write(self.style.WARNING('[!] No se encontró div con class terminos-condiciones, usando todo el body'))
            html_content = body_content
        else:
            html_content = body_content[div_start:div_end + 6]

        self.stdout.write(self.style.SUCCESS(f'[2/4] HTML extraído ({len(html_content)} caracteres)'))

        # Buscar o crear términos v1.0
        try:
            terminos = TerminosYCondiciones.objects.get(version='1.0')
            self.stdout.write(self.style.SUCCESS('[3/4] Términos v1.0 encontrados - REEMPLAZANDO contenido completo'))
        except TerminosYCondiciones.DoesNotExist:
            self.stdout.write(self.style.WARNING('[3/4] Creando nuevos términos v1.0'))
            terminos = TerminosYCondiciones()
            terminos.version = '1.0'
            terminos.fecha_vigencia = date(2025, 10, 1)
            terminos.titulo = 'Contrato de Licencia de Uso y Provisión de Servicios SaaS - Plataforma SAM'
            terminos.activo = True

        # REEMPLAZAR TODO el contenido
        terminos.contenido_html = html_content
        terminos.save()

        self.stdout.write(self.style.SUCCESS('[4/4] Contrato guardado en base de datos'))

        # Verificación
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS('CONTRATO ACTUALIZADO EXITOSAMENTE'))
        self.stdout.write("=" * 70)
        self.stdout.write(f'Versión: {terminos.version}')
        self.stdout.write(f'Fecha vigencia: {terminos.fecha_vigencia}')
        self.stdout.write(f'Estado: {"Activo" if terminos.activo else "Inactivo"}')
        self.stdout.write(f'Longitud HTML: {len(terminos.contenido_html)} caracteres')

        # Verificar contenido clave
        verificaciones = [
            ('180 días (6 meses)', 'Periodo de gracia actualizado'),
            ('Carrera 13i # 33 20 sur', 'Dirección actualizada'),
            ('contacto@sammetrologia.com', 'Email profesional'),
            ('200 equipos', 'Límite de equipos actualizado'),
            ('4 GB', 'Almacenamiento actualizado'),
            ('$200.000', 'Precio actualizado')
        ]

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write('VERIFICACIÓN DE CONTENIDO:')
        self.stdout.write("=" * 70)

        todo_ok = True
        for texto, descripcion in verificaciones:
            if texto in terminos.contenido_html:
                self.stdout.write(self.style.SUCCESS(f'[OK] {descripcion}'))
            else:
                self.stdout.write(self.style.WARNING(f'[X] {descripcion}: NO ENCONTRADO'))
                todo_ok = False

        if todo_ok:
            self.stdout.write("\n" + self.style.SUCCESS('[OK] TODAS LAS VERIFICACIONES PASARON'))
        else:
            self.stdout.write("\n" + self.style.WARNING('[!] Algunas verificaciones fallaron'))

        self.stdout.write("=" * 70)
        self.stdout.write('\nURL del contrato:')
        self.stdout.write('https://app.sammetrologia.com/core/mi-aceptacion-terminos/')
        self.stdout.write("=" * 70 + "\n")
