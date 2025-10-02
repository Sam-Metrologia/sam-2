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
from core.views.reports import _generate_consolidated_excel_content
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
            default=5,
            help='Intervalo en segundos para revisar la cola (default: 5 - ACELERADO)'
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
            # Inicializar progreso
            total_equipos = zip_request.empresa.equipos.count()

            # Marcar como procesándose con progreso inicial
            zip_request.status = 'processing'
            zip_request.started_at = timezone.now()
            zip_request.current_step = 'Inicializando generación de ZIP...'
            zip_request.total_equipos = total_equipos
            zip_request.progress_percentage = 0
            zip_request.equipos_procesados = 0

            # Estimar tiempo de finalización (aproximadamente 3 segundos por equipo + overhead)
            estimated_seconds = (total_equipos * 3) + 30  # 30 segundos de overhead
            zip_request.estimated_completion = timezone.now() + timedelta(seconds=estimated_seconds)
            zip_request.save()

            self.stdout.write(f'[GENERANDO] Iniciando ZIP para empresa {zip_request.empresa.nombre} ({total_equipos} equipos)')

            # Generar el ZIP con seguimiento de progreso
            file_path, file_size = self.generate_zip_file(zip_request)

            # Marcar como completado
            zip_request.status = 'completed'
            zip_request.completed_at = timezone.now()
            zip_request.file_path = file_path
            zip_request.file_size = file_size
            zip_request.expires_at = timezone.now() + timedelta(hours=6)  # Expira en 6 horas
            zip_request.current_step = 'ZIP completado y listo para descarga'
            zip_request.progress_percentage = 100
            zip_request.save()

            # Crear notificación push para el usuario
            self.create_zip_notification(zip_request, 'zip_ready')

            self.stdout.write(
                self.style.SUCCESS(f'[EXITOSO] ZIP completado: {file_path} ({file_size} bytes)')
            )

        except Exception as e:
            # Marcar como fallido
            zip_request.status = 'failed'
            zip_request.error_message = str(e)
            zip_request.completed_at = timezone.now()
            zip_request.current_step = f'Error en generación: {str(e)[:100]}'
            zip_request.save()

            # Crear notificación de error para el usuario
            self.create_zip_notification(zip_request, 'zip_failed')

            self.stdout.write(
                self.style.ERROR(f'[ERROR] Error generando ZIP: {e}')
            )
            logger.error(f'Error generando ZIP para solicitud {zip_request.id}: {e}', exc_info=True)

    def generate_zip_file(self, zip_request):
        """Genera el archivo ZIP y lo guarda en storage."""
        from core.views.reports import stream_file_to_zip  # Importar función helper

        # Crear request mock para la generación PDF
        mock_request = self.create_mock_request(zip_request.user)

        # Obtener datos para el ZIP
        empresa = zip_request.empresa
        parte_numero = zip_request.parte_numero

        # Configuración igual que en la vista original
        EQUIPOS_POR_ZIP = 100
        equipos_empresa_total = Equipo.objects.filter(empresa=empresa).count()
        offset = (parte_numero - 1) * EQUIPOS_POR_ZIP

        # Obtener TODOS los equipos (activos + dados de baja + inactivos) con prefetch optimizado
        equipos_empresa = Equipo.objects.filter(empresa=empresa).select_related(
            'empresa',  # Empresa ya está filtrada, pero incluir para evitar queries extras
        ).prefetch_related(
            # Optimizar calibraciones con campos específicos que necesitamos
            'calibraciones__documento_calibracion',
            'calibraciones__confirmacion_metrologica_pdf',
            'calibraciones__intervalos_calibracion_pdf',
            # Optimizar mantenimientos
            'mantenimientos__documento_mantenimiento',
            # Optimizar comprobaciones
            'comprobaciones__documento_comprobacion',
            # Optimizar baja_registro
            'baja_registro'
        ).order_by('codigo_interno')[offset:offset + EQUIPOS_POR_ZIP]

        # Optimizar consultas de proveedores y procedimientos
        proveedores_empresa = Proveedor.objects.filter(empresa=empresa).select_related('empresa').order_by('nombre_empresa')
        procedimientos_empresa = Procedimiento.objects.filter(empresa=empresa).select_related('empresa').order_by('codigo')

        # Crear buffer para ZIP con compresión adaptativa
        zip_buffer = io.BytesIO()
        empresa_nombre = empresa.nombre

        # Optimizar nivel de compresión basado en cantidad de equipos
        num_equipos = len(equipos_empresa)
        if num_equipos <= 5:
            compresslevel = 9  # Máxima compresión para empresas pequeñas
        elif num_equipos <= 15:
            compresslevel = 6  # Compresión balanceada
        else:
            compresslevel = 2  # Compresión rápida para empresas grandes (optimizada para cola)

        self.stdout.write(f'[COMPRESIÓN] Usando nivel {compresslevel} para {num_equipos} equipos')

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=compresslevel) as zf:
            # Actualizar progreso: Excel consolidado
            zip_request.current_step = 'Generando Excel consolidado...'
            zip_request.progress_percentage = 5
            zip_request.save()

            # Excel consolidado
            self.stdout.write('[EXCEL] Generando Excel consolidado...')
            excel_consolidado = _generate_consolidated_excel_content(
                equipos_empresa, proveedores_empresa, procedimientos_empresa
            )
            zf.writestr(f"{empresa_nombre}/Informe_Consolidado.xlsx", excel_consolidado)

            # Actualizar progreso: Procedimientos
            zip_request.current_step = 'Procesando procedimientos de la empresa...'
            zip_request.progress_percentage = 10
            zip_request.save()

            # Carpeta de Procedimientos de la empresa
            procedimientos_count = procedimientos_empresa.count()
            self.stdout.write(f'[PROCEDIMIENTOS] Empresa {empresa_nombre} tiene {procedimientos_count} procedimientos')

            procedimientos_agregados = 0
            for idx, procedimiento in enumerate(procedimientos_empresa, 1):
                tiene_archivo = bool(procedimiento.documento_pdf)
                archivo_path = procedimiento.documento_pdf.name if procedimiento.documento_pdf else "No hay archivo"
                self.stdout.write(f'[PROC] {idx}: "{procedimiento.codigo}" - "{procedimiento.nombre}" - Archivo: {tiene_archivo} - Path: {archivo_path}')

                if procedimiento.documento_pdf:
                        try:
                            # Nombre descriptivo: CODIGO_Nombre.pdf
                            safe_codigo = procedimiento.codigo.replace('/', '_').replace('\\', '_')
                            safe_nombre = procedimiento.nombre.replace('/', '_').replace('\\', '_')[:50]  # Limitar longitud
                            filename = f"{safe_codigo}_{safe_nombre}.pdf"
                            if stream_file_to_zip(zf, procedimiento.documento_pdf.name, f"{empresa_nombre}/Procedimientos/{filename}"):
                                procedimientos_agregados += 1
                                self.stdout.write(f'[PROC] ✅ Procedimiento agregado: {filename}')
                            else:
                                self.stdout.write(f'[PROC] ❌ No se pudo agregar: {filename}')
                        except Exception as e:
                            logger.error(f"Error adding procedure {procedimiento.codigo}: {e}")

            # Crear carpeta vacía si no hay procedimientos
            if procedimientos_agregados == 0:
                zf.writestr(f"{empresa_nombre}/Procedimientos/README.txt", "No hay procedimientos con documentos PDF disponibles para esta empresa.")
                self.stdout.write(f'[PROC] 📁 Carpeta /Procedimientos/ creada (vacía)')
            else:
                self.stdout.write(f'[PROC] ✅ {procedimientos_agregados} procedimientos agregados')

            # Procesar cada equipo con seguimiento de progreso
            for idx, equipo in enumerate(equipos_empresa, 1):
                # Actualizar progreso
                progress = int(((idx - 1) / len(equipos_empresa)) * 80) + 15  # 15-95% para equipos
                zip_request.current_step = f'Procesando equipo {idx}/{len(equipos_empresa)}: {equipo.codigo_interno}'
                zip_request.progress_percentage = progress
                zip_request.equipos_procesados = idx - 1
                zip_request.save()

                self.stdout.write(f'[EQUIPO] Procesando {idx}/{len(equipos_empresa)} ({progress}%): {equipo.codigo_interno}')

                safe_codigo = equipo.codigo_interno.replace('/', '_').replace('\\', '_')
                equipo_folder = f"{empresa_nombre}/Equipos/{safe_codigo}"

                # Generar Hoja de Vida PDF
                try:
                    from core.views.reports import _generate_equipment_hoja_vida_pdf_content
                    hoja_vida_pdf_content = _generate_equipment_hoja_vida_pdf_content(mock_request, equipo)

                    # Verificar que el contenido sea válido (bytes de PDF)
                    if isinstance(hoja_vida_pdf_content, bytes) and len(hoja_vida_pdf_content) > 0:
                        zf.writestr(f"{equipo_folder}/Hoja_de_vida.pdf", hoja_vida_pdf_content)
                        self.stdout.write(f'[PDF] Hoja de vida generada exitosamente para {equipo.codigo_interno}')
                    else:
                        raise ValueError(f"Contenido PDF inválido o vacío para {equipo.codigo_interno}")

                except Exception as e:
                    error_msg = f"Error generando PDF para {equipo.codigo_interno}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    self.stdout.write(self.style.ERROR(f'[PDF ERROR] {error_msg}'))

                    # Crear archivo de error con información detallada
                    error_content = f"""Error generando Hoja de Vida PDF:
Equipo: {equipo.codigo_interno} - {equipo.nombre}
Error: {str(e)}
Timestamp: {timezone.now().isoformat()}

Por favor reporte este error al administrador del sistema.
"""
                    zf.writestr(f"{equipo_folder}/Hoja_de_vida_ERROR.txt", error_content)

                # Agregar documentos de calibraciones con subcarpetas organizadas
                cal_idx = 1
                conf_idx = 1
                int_idx = 1

                for cal in equipo.calibraciones.all():
                    # Certificados de calibración -> Subcarpeta específica
                    if cal.documento_calibracion:
                        try:
                            simple_name = f"cal_{cal_idx}.pdf"
                            if stream_file_to_zip(zf, cal.documento_calibracion.name, f"{equipo_folder}/Calibraciones/Certificados_Calibracion/{simple_name}"):
                                cal_idx += 1
                        except Exception as e:
                            logger.error(f"Error adding calibration certificate: {e}")

                    # Confirmación metrológica -> Subcarpeta específica
                    if cal.confirmacion_metrologica_pdf:
                        try:
                            simple_name = f"conf_{conf_idx}.pdf"
                            if stream_file_to_zip(zf, cal.confirmacion_metrologica_pdf.name, f"{equipo_folder}/Calibraciones/Confirmacion_Metrologica/{simple_name}"):
                                conf_idx += 1
                        except Exception as e:
                            logger.error(f"Error adding metrological confirmation: {e}")

                    # Intervalos de calibración -> Subcarpeta específica
                    if cal.intervalos_calibracion_pdf:
                        try:
                            simple_name = f"int_{int_idx}.pdf"
                            if stream_file_to_zip(zf, cal.intervalos_calibracion_pdf.name, f"{equipo_folder}/Calibraciones/Intervalos_Calibracion/{simple_name}"):
                                int_idx += 1
                        except Exception as e:
                            logger.error(f"Error adding calibration intervals: {e}")

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

                # LÓGICA NUEVA: Carpeta de Baja SOLO si equipo está dado de baja
                if equipo.estado == 'De Baja':
                    try:
                        baja_registro = equipo.baja_registro
                        if baja_registro and baja_registro.documento_baja:
                            baja_folder = f"{equipo_folder}/Baja"
                            filename = "documento_baja.pdf"
                            if stream_file_to_zip(zf, baja_registro.documento_baja.name, f"{baja_folder}/{filename}"):
                                self.stdout.write(f'[BAJA] Carpeta /Baja/ agregada para equipo dado de baja: {equipo.codigo_interno}')
                    except Exception as e:
                        logger.error(f"Error adding decommission document for {equipo.codigo_interno}: {e}")

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
        mock_request.path = '/'
        mock_request.path_info = '/'

        # Configurar META para evitar errores de SERVER_NAME
        mock_request.META = {
            'SERVER_NAME': 'sam-9o6o.onrender.com',
            'SERVER_PORT': '443',
            'wsgi.url_scheme': 'https',
            'HTTP_HOST': 'sam-9o6o.onrender.com',
            'SCRIPT_NAME': '',
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'CONTENT_TYPE': '',
            'CONTENT_LENGTH': '',
        }

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

    def create_zip_notification(self, zip_request, tipo):
        """Crea una notificación push para el usuario cuando el ZIP está listo o falla."""
        from core.models import NotificacionZip

        try:
            if tipo == 'zip_ready':
                titulo = f"✅ ZIP Listo - {zip_request.empresa.nombre}"
                mensaje = f"Tu archivo ZIP para la empresa {zip_request.empresa.nombre} está listo para descarga. Expira en 6 horas."
            elif tipo == 'zip_failed':
                titulo = f"❌ Error en ZIP - {zip_request.empresa.nombre}"
                mensaje = f"Hubo un error generando el ZIP para {zip_request.empresa.nombre}. Error: {zip_request.error_message[:100]}"
            else:
                titulo = f"📁 Actualización ZIP - {zip_request.empresa.nombre}"
                mensaje = f"Estado actualizado para ZIP de {zip_request.empresa.nombre}"

            # Crear la notificación
            notificacion = NotificacionZip.objects.create(
                user=zip_request.user,
                zip_request=zip_request,
                tipo=tipo,
                titulo=titulo,
                mensaje=mensaje
            )

            self.stdout.write(f'[NOTIFICACIÓN] Creada para {zip_request.user.username}: {titulo}')
            logger.info(f"Notificación {tipo} creada para usuario {zip_request.user.username}, ZIP {zip_request.id}")

        except Exception as e:
            logger.error(f"Error creando notificación {tipo} para ZIP {zip_request.id}: {e}")
            self.stdout.write(self.style.ERROR(f'[NOTIF ERROR] {e}'))