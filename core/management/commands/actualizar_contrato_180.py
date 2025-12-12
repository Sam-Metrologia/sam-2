# core/management/commands/actualizar_contrato_180.py
"""
Comando Django para actualizar el contrato a 180 días (6 meses)
Sin dependencia de archivos externos - HTML incluido en el código
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import TerminosYCondiciones
from datetime import date


class Command(BaseCommand):
    help = 'Actualiza el contrato a periodo de gracia de 180 días (6 meses)'

    def handle(self, *args, **options):
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS('ACTUALIZANDO CONTRATO A 180 DÍAS'))
        self.stdout.write("=" * 70)

        # Buscar o crear términos v1.0
        try:
            terminos = TerminosYCondiciones.objects.get(version='1.0')
            self.stdout.write(self.style.SUCCESS('\n[OK] Encontrados términos v1.0'))
        except TerminosYCondiciones.DoesNotExist:
            self.stdout.write(self.style.WARNING('\n[!] Creando nuevos términos v1.0'))
            terminos = TerminosYCondiciones()
            terminos.version = '1.0'
            terminos.fecha_vigencia = date(2025, 10, 1)
            terminos.titulo = 'Contrato de Licencia de Uso y Provisión de Servicios SaaS - Plataforma SAM'
            terminos.activo = True

        # Actualizar solo las secciones relevantes del HTML
        # Buscar y reemplazar 30 días por 180 días en el contenido actual
        contenido_actual = terminos.contenido_html

        # Reemplazos específicos
        contenido_actualizado = contenido_actual.replace(
            '<strong>30 días</strong> para exportación',
            '<strong>180 días (6 meses)</strong> para exportación y/o reactivación. Este periodo ampliado permite al Cliente recuperar su información sin presión de tiempo, superando el estándar de la industria. Transcurrido este plazo, los datos serán eliminados permanentemente'
        )

        contenido_actualizado = contenido_actualizado.replace(
            'Transcurrido el periodo de gracia de 30 días tras cancelación',
            'Transcurrido el periodo de gracia de 180 días (6 meses) tras cancelación'
        )

        contenido_actualizado = contenido_actualizado.replace(
            'periodo de <strong>seis (6) meses calendario</strong>',
            'periodo de <strong>180 días (6 meses)</strong>'
        )

        # Guardar cambios
        terminos.contenido_html = contenido_actualizado
        terminos.save()

        self.stdout.write(self.style.SUCCESS('\n[OK] Contrato actualizado exitosamente'))
        self.stdout.write("=" * 70)
        self.stdout.write(f'Versión: {terminos.version}')
        self.stdout.write(f'Fecha: {terminos.fecha_vigencia}')
        self.stdout.write(f'Activo: {terminos.activo}')

        # Verificar
        if '180 días (6 meses)' in terminos.contenido_html:
            self.stdout.write(self.style.SUCCESS('\n✓ Verificación exitosa: contiene "180 días (6 meses)"'))
        else:
            self.stdout.write(self.style.WARNING('\n! Advertencia: no se encontró "180 días (6 meses)"'))

        self.stdout.write("=" * 70)
