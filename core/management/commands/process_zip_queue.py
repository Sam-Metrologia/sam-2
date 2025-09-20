"""
Comando para procesar la cola de generación de archivos ZIP.
Este comando se ejecuta continuamente procesando las solicitudes ZIP una por una.

Uso:
    python manage.py process_zip_queue

Para ejecutar en producción como servicio en background:
    nohup python manage.py process_zip_queue >> logs/zip_queue.log 2>&1 &
"""

import time
import os
import tempfile
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.files.storage import default_storage
from django.http import HttpRequest
from django.contrib.auth import get_user_model
from core.models import ZipRequest, Empresa, Equipo, Proveedor, Procedimiento
from core.views import _generate_consolidated_excel_content
import zipfile
import io
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Procesa la cola de solicitudes ZIP en background'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-interval',
            type=int,
            default=30,
            help='Intervalo en segundos para revisar la cola (default: 30)'
        )
        parser.add_argument(
            '--max-iterations',
            type=int,
            default=0,
            help='Máximo número de iteraciones (0 = infinito)'
        )
        parser.add_argument(
            '--cleanup-old',
            action='store_true',
            help='Limpiar solicitudes antiguas al iniciar'
        )

    def handle(self, *args, **options):
        check_interval = options['check_interval']
        max_iterations = options['max_iterations']
        cleanup_old = options['cleanup_old']

        self.stdout.write(
            self.style.SUCCESS(f'[INICIO] Procesador de cola ZIP iniciado (intervalo: {check_interval}s)')
        )

        if cleanup_old:
            self.cleanup_old_requests()

        iteration = 0
        while True:
            iteration += 1

            try:
                # Buscar próxima solicitud pendiente
                next_request = ZipRequest.objects.filter(
                    status='pending'
                ).order_by('position_in_queue').first()

                if next_request:
                    self.stdout.write(f'[PROCESANDO] Solicitud #{next_request.id} de {next_request.user.username}')
                    self.process_zip_request(next_request)
                else:
                    self.stdout.write(f'[ESPERANDO] Iteración {iteration}: Cola vacía, esperando...')

                # Limpiar solicitudes expiradas
                self.cleanup_expired_requests()

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'[ERROR] Error en procesamiento: {e}')
                )
                logger.error(f'Error en cola ZIP: {e}', exc_info=True)

            # Verificar si se debe continuar
            if max_iterations > 0 and iteration >= max_iterations:
                self.stdout.write(
                    self.style.SUCCESS(f'[COMPLETADO] {iteration} iteraciones realizadas, terminando...')
                )
                break

            # Esperar antes de la siguiente iteración
            time.sleep(check_interval)

    def process_zip_request(self, zip_request):
        """Procesa una solicitud ZIP específica."""
        try:
            # Marcar como procesándose
            zip_request.status = 'processing'
            zip_request.started_at = timezone.now()
            zip_request.save()

            self.stdout.write(f'[GENERANDO] Iniciando ZIP para empresa {zip_request.empresa.nombre}')

            # Generar el ZIP
            file_path, file_size = self.generate_zip_file(zip_request)

            # Marcar como completado
            zip_request.status = 'completed'
            zip_request.completed_at = timezone.now()
            zip_request.file_path = file_path
            zip_request.file_size = file_size
            zip_request.expires_at = timezone.now() + timedelta(hours=6)  # Expira en 6 horas
            zip_request.save()

            self.stdout.write(
                self.style.SUCCESS(f'[EXITOSO] ZIP completado: {file_path} ({file_size} bytes)')
            )

        except Exception as e:
            # Marcar como fallido
            zip_request.status = 'failed'
            zip_request.error_message = str(e)
            zip_request.completed_at = timezone.now()
            zip_request.save()

            self.stdout.write(
                self.style.ERROR(f'[ERROR] Error generando ZIP: {e}')
            )
            logger.error(f'Error generando ZIP para solicitud {zip_request.id}: {e}', exc_info=True)

    def generate_zip_file(self, zip_request):
        """Genera el archivo ZIP y lo guarda en storage."""
        from core.views import stream_file_to_zip  # Importar función helper

        # Crear request mock para la generación PDF
        mock_request = self.create_mock_request(zip_request.user)

        # Obtener datos para el ZIP
        empresa = zip_request.empresa
        parte_numero = zip_request.parte_numero

        # Configuración igual que en la vista original
        EQUIPOS_POR_ZIP = 35
        equipos_empresa_total = Equipo.objects.filter(empresa=empresa).count()
        offset = (parte_numero - 1) * EQUIPOS_POR_ZIP

        # Obtener equipos con prefetch optimizado
        equipos_empresa = Equipo.objects.filter(empresa=empresa).select_related('empresa').prefetch_related(
            'calibraciones', 'mantenimientos', 'comprobaciones', 'baja_registro'
        ).order_by('codigo_interno')[offset:offset + EQUIPOS_POR_ZIP]

        # Obtener proveedores y procedimientos
        proveedores_empresa = Proveedor.objects.filter(empresa=empresa)
        procedimientos_empresa = Procedimiento.objects.filter(empresa=empresa)

        # Crear buffer para ZIP
        zip_buffer = io.BytesIO()
        empresa_nombre = empresa.nombre

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=2) as zf:
            # Excel consolidado
            self.stdout.write('[EXCEL] Generando Excel consolidado...')
            excel_consolidado = _generate_consolidated_excel_content(
                equipos_empresa, proveedores_empresa, procedimientos_empresa
            )
            zf.writestr(f"{empresa_nombre}/Informe_Consolidado.xlsx", excel_consolidado)

            # Procesar cada equipo
            for idx, equipo in enumerate(equipos_empresa, 1):
                self.stdout.write(f'[EQUIPO] Procesando {idx}/{len(equipos_empresa)}: {equipo.codigo_interno}')

                safe_codigo = equipo.codigo_interno.replace('/', '_').replace('\\', '_')
                equipo_folder = f"{empresa_nombre}/Equipos/{safe_codigo}"

                # Generar Hoja de Vida PDF
                try:
                    from core.views import _generate_equipment_hoja_vida_pdf_content
                    hoja_vida_pdf_content = _generate_equipment_hoja_vida_pdf_content(mock_request, equipo)
                    zf.writestr(f"{equipo_folder}/Hoja_de_vida.pdf", hoja_vida_pdf_content)
                except Exception as e:
                    logger.error(f"Error generating PDF for {equipo.codigo_interno}: {e}")
                    zf.writestr(f"{equipo_folder}/Hoja_de_vida_ERROR.txt", f"Error: {e}")

                # Agregar documentos de calibraciones
                cal_idx = 1
                for cal in equipo.calibraciones.all():
                    if cal.documento_calibracion:
                        try:
                            simple_name = f"cal_{cal_idx}.pdf"
                            if stream_file_to_zip(zf, cal.documento_calibracion.name, f"{equipo_folder}/Calibraciones/{simple_name}"):
                                cal_idx += 1
                        except Exception as e:
                            logger.error(f"Error adding calibration file: {e}")

                    if cal.confirmacion_metrologica_pdf:
                        try:
                            simple_name = f"conf_{cal_idx}.pdf"
                            if stream_file_to_zip(zf, cal.confirmacion_metrologica_pdf.name, f"{equipo_folder}/Calibraciones/{simple_name}"):
                                cal_idx += 1
                        except Exception as e:
                            logger.error(f"Error adding confirmation file: {e}")

                    if cal.intervalos_calibracion_pdf:
                        try:
                            simple_name = f"int_{cal_idx}.pdf"
                            if stream_file_to_zip(zf, cal.intervalos_calibracion_pdf.name, f"{equipo_folder}/Calibraciones/{simple_name}"):
                                cal_idx += 1
                        except Exception as e:
                            logger.error(f"Error adding intervals file: {e}")

                # Agregar documentos de mantenimientos
                mant_idx = 1
                for mant in equipo.mantenimientos.all():
                    if mant.documento_mantenimiento:
                        try:
                            simple_name = f"mant_{mant_idx}.pdf"
                            if stream_file_to_zip(zf, mant.documento_mantenimiento.name, f"{equipo_folder}/Mantenimientos/{simple_name}"):
                                mant_idx += 1
                        except Exception as e:
                            logger.error(f"Error adding maintenance file: {e}")

                # Agregar documentos de comprobaciones
                comp_idx = 1
                for comp in equipo.comprobaciones.all():
                    if comp.documento_comprobacion:
                        try:
                            simple_name = f"comp_{comp_idx}.pdf"
                            if stream_file_to_zip(zf, comp.documento_comprobacion.name, f"{equipo_folder}/Comprobaciones/{simple_name}"):
                                comp_idx += 1
                        except Exception as e:
                            logger.error(f"Error adding verification file: {e}")

                # Agregar documentos del equipo
                equipment_docs = [
                    (equipo.archivo_compra_pdf, 'compra'),
                    (equipo.ficha_tecnica_pdf, 'ficha_tecnica'),
                    (equipo.manual_pdf, 'manual'),
                    (equipo.otros_documentos_pdf, 'otros_documentos')
                ]

                for doc_field, doc_type in equipment_docs:
                    if doc_field:
                        try:
                            if doc_field.name.lower().endswith('.pdf'):
                                nombre_descriptivo = f"{doc_type}.pdf"
                                stream_file_to_zip(zf, doc_field.name, f"{equipo_folder}/{nombre_descriptivo}")
                        except Exception as e:
                            logger.error(f"Error adding equipment document: {e}")

                # Agregar documento de baja si existe
                try:
                    baja_registro = equipo.baja_registro
                    if baja_registro and baja_registro.documento_baja:
                        baja_folder = f"{equipo_folder}/Baja"
                        file_name_in_zip = os.path.basename(baja_registro.documento_baja.name)
                        stream_file_to_zip(zf, baja_registro.documento_baja.name, f"{baja_folder}/{file_name_in_zip}")
                except Exception as e:
                    logger.error(f"Error adding decommission document: {e}")

        # Guardar archivo en storage
        zip_buffer.seek(0)
        file_content = zip_buffer.getvalue()
        file_size = len(file_content)

        # Generar nombre de archivo único
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"zip_requests/{empresa.id}/{timestamp}_parte_{parte_numero}_req_{zip_request.id}.zip"

        # Guardar en storage
        file_path = default_storage.save(filename, io.BytesIO(file_content))

        return file_path, file_size

    def create_mock_request(self, user):
        """Crea un objeto request mock para generar PDFs."""
        mock_request = HttpRequest()
        mock_request.user = user
        mock_request.method = 'GET'
        return mock_request

    def cleanup_expired_requests(self):
        """Limpia solicitudes expiradas."""
        expired_requests = ZipRequest.objects.filter(
            status='completed',
            expires_at__lt=timezone.now()
        )

        for req in expired_requests:
            # Eliminar archivo físico si existe
            if req.file_path and default_storage.exists(req.file_path):
                try:
                    default_storage.delete(req.file_path)
                except Exception as e:
                    logger.error(f"Error deleting expired file {req.file_path}: {e}")

            # Marcar como expirado
            req.status = 'expired'
            req.file_path = None
            req.save()

    def cleanup_old_requests(self):
        """Limpia solicitudes antiguas al iniciar."""
        self.stdout.write('[LIMPIEZA] Limpiando solicitudes antiguas...')

        # Eliminar solicitudes muy antiguas (más de 7 días)
        old_date = timezone.now() - timedelta(days=7)
        old_requests = ZipRequest.objects.filter(created_at__lt=old_date)

        for req in old_requests:
            if req.file_path and default_storage.exists(req.file_path):
                try:
                    default_storage.delete(req.file_path)
                except Exception as e:
                    logger.error(f"Error deleting old file {req.file_path}: {e}")

        deleted_count = old_requests.count()
        old_requests.delete()

        self.stdout.write(f'[LIMPIEZA] Eliminadas {deleted_count} solicitudes antiguas')