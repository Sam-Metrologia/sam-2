"""
Rearma las propuestas de las lecturas IA ya hechas con las reglas actuales de conversión,
usando lo que Gemini ya leyó (resultado_crudo). No vuelve a llamar a Gemini: no cuesta nada.

Solo toca lecturas "listas" cuya calibración todavía no tiene confirmación guardada.

    python manage.py reconstruir_lecturas_ia                # todas
    python manage.py reconstruir_lecturas_ia --empresa 23   # una empresa
    python manage.py reconstruir_lecturas_ia --dry-run      # solo mostrar
"""
from django.core.management.base import BaseCommand

from core import lectura_certificados as lc
from core.models import LecturaCertificado


class Command(BaseCommand):
    help = 'Rearma las propuestas de lectura IA con las reglas actuales (sin volver a llamar a Gemini).'

    def add_arguments(self, parser):
        parser.add_argument('--empresa', type=int, help='ID de la empresa (por defecto, todas)')
        parser.add_argument('--dry-run', action='store_true', help='Mostrar sin guardar')

    def handle(self, *args, **opciones):
        lecturas = (LecturaCertificado.objects
                    .filter(estado=LecturaCertificado.ESTADO_LISTO, resultado_crudo__isnull=False,
                            calibracion__confirmacion_metrologica_datos__isnull=True)
                    .select_related('calibracion__equipo'))
        if opciones['empresa']:
            lecturas = lecturas.filter(empresa_id=opciones['empresa'])

        total = 0
        for lectura in lecturas:
            cal = lectura.calibracion
            propuesta = lc.construir_propuesta(lectura.resultado_crudo, equipo=cal.equipo, calibracion=cal,
                                               nombres_previos=lc.nombres_previos_equipo(cal))
            total += 1
            self.stdout.write(f'{cal.equipo.codigo_interno}: {len(propuesta["magnitudes"])} variable(s)')
            if not opciones['dry_run']:
                lectura.propuesta = propuesta
                lectura.save(update_fields=['propuesta'])
        accion = 'se revisarían' if opciones['dry_run'] else 'rearmadas'
        self.stdout.write(self.style.SUCCESS(f'{total} lectura(s) {accion}.'))
