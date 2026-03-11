"""
Comando de gestión para recalcular stats del dashboard en todas las empresas activas.

Uso:
    python manage.py recalcular_stats_empresas
    python manage.py recalcular_stats_empresas --empresa-id 42
    python manage.py recalcular_stats_empresas --dry-run

Se recomienda ejecutar este comando una vez al día (cron) para mantener las stats
frescas, ya que algunas métricas dependen de la fecha actual (vencidas/próximas).
"""
from django.core.management.base import BaseCommand
from core.models import Empresa


class Command(BaseCommand):
    help = 'Recalcula stats del dashboard para todas las empresas activas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='Recalcular solo para la empresa con este ID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo lista las empresas sin recalcular',
        )

    def handle(self, *args, **options):
        empresas = Empresa.objects.filter(is_deleted=False)

        if options['empresa_id']:
            empresas = empresas.filter(id=options['empresa_id'])

        ok = 0
        errores = 0

        for empresa in empresas:
            try:
                if not options['dry_run']:
                    empresa.recalcular_stats_dashboard()
                self.stdout.write(
                    f"OK {empresa.nombre}: {empresa.stats_total_equipos} equipos"
                )
                ok += 1
            except Exception as e:
                self.stderr.write(f"ERROR {empresa.nombre}: {e}")
                errores += 1

        self.stdout.write(f"\nTotal: {ok} OK, {errores} errores")
