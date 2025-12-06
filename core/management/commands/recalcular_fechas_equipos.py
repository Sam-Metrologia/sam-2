from django.core.management.base import BaseCommand
from core.models import Equipo

class Command(BaseCommand):
    help = 'Recalcula las fechas de próximas actividades para todos los equipos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué cambios se harían sin ejecutarlos',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== MODO SIMULACIÓN (DRY RUN) ==='))
            self.stdout.write(self.style.WARNING('No se realizarán cambios en la base de datos\n'))

        equipos = Equipo.objects.all()
        total_equipos = equipos.count()

        self.stdout.write(f'Encontrados {total_equipos} equipos para procesar\n')

        actualizados = 0
        errores = 0

        for equipo in equipos:
            try:
                # Guardar valores anteriores para comparación
                anterior_calibracion = equipo.proxima_calibracion
                anterior_mantenimiento = equipo.proximo_mantenimiento
                anterior_comprobacion = equipo.proxima_comprobacion

                # Recalcular todas las fechas
                equipo.calcular_proxima_calibracion()
                equipo.calcular_proximo_mantenimiento()
                equipo.calcular_proxima_comprobacion()

                # Verificar si hubo cambios
                cambios = []
                if anterior_calibracion != equipo.proxima_calibracion:
                    cambios.append(f'  [CAL] Proxima calibracion: {anterior_calibracion} -> {equipo.proxima_calibracion}')
                if anterior_mantenimiento != equipo.proximo_mantenimiento:
                    cambios.append(f'  [MAN] Proximo mantenimiento: {anterior_mantenimiento} -> {equipo.proximo_mantenimiento}')
                if anterior_comprobacion != equipo.proxima_comprobacion:
                    cambios.append(f'  [COM] Proxima comprobacion: {anterior_comprobacion} -> {equipo.proxima_comprobacion}')

                if cambios:
                    self.stdout.write(self.style.SUCCESS(f'\n{equipo.codigo_interno} - {equipo.nombre}'))
                    for cambio in cambios:
                        self.stdout.write(cambio)

                    if not dry_run:
                        # Guardar solo los campos de fechas para evitar triggers del modelo
                        equipo.save(update_fields=['proxima_calibracion', 'proximo_mantenimiento', 'proxima_comprobacion'])
                        actualizados += 1
                    else:
                        actualizados += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'\nX Error en {equipo.codigo_interno}: {str(e)}'))
                errores += 1

        self.stdout.write('\n' + '='*60)
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'\n[OK] Simulacion completada:'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n[OK] Proceso completado:'))

        self.stdout.write(f'  - Total equipos: {total_equipos}')
        self.stdout.write(self.style.SUCCESS(f'  - Actualizados: {actualizados}'))
        if errores > 0:
            self.stdout.write(self.style.ERROR(f'  - Errores: {errores}'))
        else:
            self.stdout.write(f'  - Errores: {errores}')
        self.stdout.write(f'  - Sin cambios: {total_equipos - actualizados - errores}')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n[!] Para aplicar los cambios, ejecuta el comando sin --dry-run'))
