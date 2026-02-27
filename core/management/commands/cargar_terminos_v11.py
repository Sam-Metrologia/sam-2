# core/management/commands/cargar_terminos_v11.py
# Carga la versión 1.1 de los Términos y Condiciones.
# Uso: python manage.py cargar_terminos_v11

from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import TerminosYCondiciones
import os


class Command(BaseCommand):
    help = 'Carga los Términos y Condiciones versión 1.1 (26/02/2026)'

    def handle(self, *args, **options):
        self.stdout.write('=' * 65)
        self.stdout.write('CARGANDO TÉRMINOS Y CONDICIONES v1.1')
        self.stdout.write('=' * 65)

        VERSION = '1.1'
        ARCHIVO_HTML = 'terminos_condiciones_v1.1.html'

        # Ruta al HTML en la raíz del proyecto
        base_dir = os.path.dirname(
            os.path.dirname(  # commands/
                os.path.dirname(  # management/
                    os.path.dirname(  # core/
                        os.path.abspath(__file__)
                    )
                )
            )
        )
        ruta_html = os.path.join(base_dir, ARCHIVO_HTML)

        if not os.path.exists(ruta_html):
            self.stdout.write(self.style.ERROR(
                f'[ERROR] No se encontró el archivo: {ruta_html}\n'
                f'Asegúrate de que {ARCHIVO_HTML} esté en la raíz del proyecto.'
            ))
            return

        # Verificar si ya existe v1.1
        if TerminosYCondiciones.objects.filter(version=VERSION).exists():
            self.stdout.write(self.style.WARNING(f'\n[!] Ya existe la versión {VERSION}'))
            respuesta = input('¿Desea reemplazarla? (s/n): ')
            if respuesta.lower() != 's':
                self.stdout.write(self.style.ERROR('[X] Operación cancelada'))
                return
            TerminosYCondiciones.objects.filter(version=VERSION).delete()
            self.stdout.write(self.style.WARNING(f'[OK] Versión {VERSION} anterior eliminada'))

        # Leer el contenido HTML
        with open(ruta_html, 'r', encoding='utf-8') as f:
            contenido_html = f.read()

        # Crear el registro
        terminos = TerminosYCondiciones.objects.create(
            version=VERSION,
            contenido_html=contenido_html,
            fecha_vigencia='2026-02-26',
            activo=True,
        )

        # Desactivar versiones anteriores
        TerminosYCondiciones.objects.exclude(pk=terminos.pk).update(activo=False)

        self.stdout.write(self.style.SUCCESS(
            f'\n[OK] Términos v{VERSION} cargados correctamente (ID: {terminos.pk})\n'
            f'     Versiones anteriores desactivadas.\n'
            f'     Fecha de vigencia: 26/02/2026\n'
        ))
        self.stdout.write('=' * 65)
