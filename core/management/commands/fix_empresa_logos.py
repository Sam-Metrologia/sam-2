# Comando para corregir logos de empresas perdidos en la migración a S3
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from core.models import Empresa
import logging
import os

logger = logging.getLogger('core')

class Command(BaseCommand):
    help = 'Corrige logos de empresas que se perdieron en la migración a S3'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué se haría, sin hacer cambios reales',
        )
        parser.add_argument(
            '--reset-missing',
            action='store_true',
            help='Limpiar referencias a logos que no existen en S3',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        reset_missing = options['reset_missing']

        self.stdout.write(self.style.SUCCESS('🔍 Analizando logos de empresas...'))

        empresas_con_logo = Empresa.objects.exclude(logo_empresa__isnull=True).exclude(logo_empresa='')

        logos_existentes = 0
        logos_perdidos = 0
        logos_corregidos = 0

        for empresa in empresas_con_logo:
            logo_path = empresa.logo_empresa.name if empresa.logo_empresa else None

            if not logo_path:
                continue

            # Verificar si existe en S3
            exists = default_storage.exists(logo_path)

            if exists:
                logos_existentes += 1
                self.stdout.write(f"✅ {empresa.nombre}: Logo OK - {logo_path}")
            else:
                logos_perdidos += 1
                self.stdout.write(
                    self.style.WARNING(f"❌ {empresa.nombre}: Logo PERDIDO - {logo_path}")
                )

                if reset_missing and not dry_run:
                    # Limpiar referencia al logo perdido
                    empresa.logo_empresa = None
                    empresa.save()
                    logos_corregidos += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"🔧 {empresa.nombre}: Referencia limpiada")
                    )

        # Resumen
        self.stdout.write(self.style.SUCCESS('\n📊 RESUMEN:'))
        self.stdout.write(f"✅ Logos existentes: {logos_existentes}")
        self.stdout.write(f"❌ Logos perdidos: {logos_perdidos}")

        if reset_missing:
            self.stdout.write(f"🔧 Referencias corregidas: {logos_corregidos}")

        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN: No se hicieron cambios reales'))
            self.stdout.write('Para aplicar cambios, ejecuta: python manage.py fix_empresa_logos --reset-missing')

        if logos_perdidos > 0 and not reset_missing:
            self.stdout.write(self.style.WARNING('\n💡 RECOMENDACIÓN:'))
            self.stdout.write('1. Ejecuta: python manage.py fix_empresa_logos --reset-missing')
            self.stdout.write('2. Pide a las empresas que vuelvan a subir sus logos')
            self.stdout.write('3. Los nuevos logos se guardarán correctamente en S3')