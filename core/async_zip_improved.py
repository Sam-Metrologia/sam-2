# core/async_zip_improved.py
# Sistema asíncrono que mantiene EXACTAMENTE la estructura ZIP existente

import threading
import time
import logging
import os
import gc
import tempfile
import zipfile
from datetime import datetime, timedelta
from queue import Queue, Empty
from django.utils import timezone
from django.core.files.storage import default_storage
from django.db.models import Max
from .models import ZipRequest, Empresa, Equipo, Proveedor, Procedimiento
from .zip_functions import stream_file_to_zip_local
from .constants import ESTADO_DE_BAJA

logger = logging.getLogger('core')

class AsyncZipProcessor:
    """
    Procesador asíncrono que mantiene EXACTAMENTE la misma estructura ZIP
    pero sin bloquear la aplicación y sin límites de equipos.
    """

    def __init__(self):
        self.processing_queue = Queue()
        self.is_running = False
        self.current_job = None
        self.worker_thread = None

    def start_processor(self):
        """Inicia el procesador en background si no está corriendo"""
        if not self.is_running:
            self.is_running = True

            # 🔄 RECUPERAR solicitudes pendientes de la base de datos
            self._recover_pending_requests()

            self.worker_thread = threading.Thread(
                target=self._process_queue_worker,
                daemon=True,
                name="SAM_ZIP_Processor"
            )
            self.worker_thread.start()
            logger.info("🚀 AsyncZipProcessor iniciado con estructura ZIP original")

    def _recover_pending_requests(self):
        """Recupera solicitudes pendientes de la DB y las agrega a la cola"""
        try:
            from core.models import ZipRequest
            from django.utils import timezone

            # Buscar solicitudes pendientes o en cola que no hayan expirado
            pending_requests = ZipRequest.objects.filter(
                status__in=['pending', 'queued'],
                expires_at__gt=timezone.now()
            ).order_by('position_in_queue', 'created_at')

            count = pending_requests.count()
            if count > 0:
                logger.info(f"🔄 Recuperando {count} solicitudes pendientes de la base de datos")

                for zip_req in pending_requests:
                    self.processing_queue.put(zip_req)
                    logger.info(f"📦 Solicitud recuperada: ID {zip_req.id} - Empresa: {zip_req.empresa.nombre} - Parte {zip_req.parte_numero}/{zip_req.total_partes}")

                logger.info(f"✅ {count} solicitudes recuperadas y agregadas a la cola")
            else:
                logger.info("ℹ️ No hay solicitudes pendientes para recuperar")

        except Exception as e:
            logger.error(f"❌ Error recuperando solicitudes pendientes: {e}", exc_info=True)

    def stop_processor(self):
        """Detiene el procesador"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)

    def add_to_queue(self, zip_request):
        """Agrega una solicitud ZIP a la cola"""
        try:
            self.processing_queue.put(zip_request)
            logger.info(f"📦 Solicitud ZIP agregada a cola: {zip_request.id} - Empresa: {zip_request.empresa.nombre}")
        except Exception as e:
            logger.error(f"Error agregando a cola ZIP: {e}")

    def get_queue_status(self):
        """Obtiene estado de la cola"""
        return {
            'queue_size': self.processing_queue.qsize(),
            'is_running': self.is_running,
            'current_job': self.current_job.id if self.current_job else None
        }

    def _process_queue_worker(self):
        """Worker principal que procesa la cola"""
        logger.info("🔄 Worker ZIP iniciado")

        while self.is_running:
            try:
                # Intentar obtener próxima solicitud (timeout 1 segundo)
                try:
                    zip_request = self.processing_queue.get(timeout=1.0)
                except Empty:
                    continue

                # Procesar la solicitud
                self.current_job = zip_request
                self._process_single_request(zip_request)
                self.current_job = None

                # Marcar como completado en la cola
                self.processing_queue.task_done()

            except Exception as e:
                logger.error(f"❌ Error en worker ZIP: {e}")
                if self.current_job:
                    self._mark_as_failed(self.current_job, str(e))
                    self.current_job = None

        logger.info("🛑 Worker ZIP detenido")

    def _process_single_request(self, zip_request):
        """
        Procesa una sola solicitud ZIP manteniendo la estructura EXACTA.
        """
        try:
            logger.info(f"🔄 Procesando ZIP para empresa {zip_request.empresa.nombre} - Request ID: {zip_request.id}")

            # Marcar como en proceso
            zip_request.status = 'processing'
            zip_request.started_at = timezone.now()
            zip_request.save()

            # Generar ZIP con la estructura EXACTA
            result = self._generate_zip_with_original_structure(zip_request)

            if result['success']:
                # Marcar como completado
                zip_request.status = 'completed'
                zip_request.completed_at = timezone.now()
                zip_request.file_path = result['file_path']
                zip_request.file_size = result['file_size']
                zip_request.save()

                logger.info(f"✅ ZIP completado para {zip_request.empresa.nombre} - {result['file_size_mb']}MB")

            else:
                self._mark_as_failed(zip_request, result['error'])

        except Exception as e:
            logger.error(f"❌ Error procesando solicitud ZIP {zip_request.id}: {e}")
            self._mark_as_failed(zip_request, str(e))

    def _mark_as_failed(self, zip_request, error_message):
        """Marca una solicitud como fallida"""
        try:
            zip_request.status = 'failed'
            zip_request.error_message = error_message
            zip_request.completed_at = timezone.now()
            zip_request.save()
            logger.error(f"❌ ZIP fallido para {zip_request.empresa.nombre}: {error_message}")
        except Exception as e:
            logger.error(f"Error marcando como fallido: {e}")

    def _generate_zip_with_original_structure(self, zip_request):
        """
        Genera ZIP con la MISMA estructura exacta que el sistema original.
        Implementa límite de 35 equipos por parte.
        Basado en descarga_directa_rapida() pero optimizado para background.
        """
        try:
            empresa = zip_request.empresa
            user = zip_request.user
            parte_numero = zip_request.parte_numero
            total_partes = zip_request.total_partes

            MAX_EQUIPOS_POR_PARTE = 35

            # Calcular rango de equipos para esta parte específica
            start_idx = (parte_numero - 1) * MAX_EQUIPOS_POR_PARTE
            end_idx = parte_numero * MAX_EQUIPOS_POR_PARTE

            logger.info(f"🔄 Generando Parte {parte_numero} de {total_partes} - Equipos {start_idx + 1} a {min(end_idx, empresa.equipos.count())}")

            # Obtener SOLO los equipos de esta parte usando slicing
            equipos_empresa = Equipo.objects.filter(
                empresa=empresa
            ).select_related(
                'empresa',
            ).prefetch_related(
                'calibraciones',
                'mantenimientos',
                'comprobaciones',
                'baja_registro'
            ).order_by('codigo_interno')[start_idx:end_idx]

            proveedores_empresa = Proveedor.objects.filter(
                empresa=empresa
            ).select_related('empresa').order_by('nombre_empresa')

            procedimientos_empresa = Procedimiento.objects.filter(
                empresa=empresa
            ).select_related('empresa').order_by('codigo')

            # Obtener préstamos de la empresa (incluir equipos relacionados)
            from .models import PrestamoEquipo
            prestamos_empresa = PrestamoEquipo.objects.filter(
                empresa=empresa
            ).select_related('equipo', 'empresa').order_by('-fecha_prestamo')

            # Crear archivo temporal para el ZIP
            temp_zip = tempfile.NamedTemporaryFile(
                delete=False,
                suffix='.zip',
                prefix=f'sam_async_{empresa.id}_'
            )
            temp_zip_path = temp_zip.name
            temp_zip.close()  # Cerrar inmediatamente para evitar problemas en Windows

            # MISMA lógica de compresión del original
            num_equipos = len(equipos_empresa)
            if num_equipos <= 5:
                compresslevel = 9  # Máxima compresión
            elif num_equipos <= 15:
                compresslevel = 6  # Compresión balanceada
            else:
                compresslevel = 3  # Compresión rápida

            logger.info(f"Usando nivel de compresión {compresslevel} para {num_equipos} equipos")

            empresa_nombre = empresa.nombre

            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=compresslevel) as zf:

                # 0. README.txt con información de la parte
                from .zip_functions import generar_readme_parte
                equipos_totales = empresa.equipos.count()
                rango_inicio = start_idx + 1
                rango_fin = min(end_idx, equipos_totales)

                readme_content = generar_readme_parte(
                    empresa_nombre,
                    parte_numero,
                    total_partes,
                    equipos_totales,
                    rango_inicio,
                    rango_fin
                )
                zf.writestr(f"{empresa_nombre}/LEEME.txt", readme_content)
                logger.info(f"✅ README.txt agregado para Parte {parte_numero}")

                # 1. Excel consolidado con TODOS los equipos (en todas las partes)
                try:
                    from .views.reports import _generate_consolidated_excel_content

                    # Obtener TODOS los equipos de la empresa para el Excel (no solo los de esta parte)
                    todos_equipos_empresa = Equipo.objects.filter(
                        empresa=empresa
                    ).select_related('empresa').prefetch_related(
                        'calibraciones',
                        'mantenimientos',
                        'comprobaciones',
                        'baja_registro'
                    ).order_by('codigo_interno')

                    excel_consolidado = _generate_consolidated_excel_content(
                        todos_equipos_empresa, proveedores_empresa, procedimientos_empresa, prestamos_empresa
                    )
                    zf.writestr(f"{empresa_nombre}/Informe_Consolidado.xlsx", excel_consolidado)
                    logger.info(f"✅ Excel consolidado agregado (con {todos_equipos_empresa.count()} equipos totales)")
                except Exception as e:
                    logger.error(f"Error generando Excel consolidado: {e}")
                    zf.writestr(f"{empresa_nombre}/ERROR_Excel.txt", f"Error generando Excel: {e}")

                # 2. Carpeta de Procedimientos (SOLO en la última parte)
                if parte_numero == total_partes:
                    procedimientos_count = procedimientos_empresa.count()
                    logger.info(f"📁 Procesando {procedimientos_count} procedimientos (última parte)")

                    procedimientos_agregados = 0
                    for idx, procedimiento in enumerate(procedimientos_empresa, 1):
                        if procedimiento.documento_pdf:
                            try:
                                # MISMO nombrado del original
                                safe_codigo = procedimiento.codigo.replace('/', '_').replace('\\', '_')
                                safe_nombre = procedimiento.nombre.replace('/', '_').replace('\\', '_')[:50]
                                filename = f"{safe_codigo}_{safe_nombre}.pdf"

                                # Usar la MISMA función de streaming del original
                                if stream_file_to_zip_local(
                                    zf,
                                    procedimiento.documento_pdf.name,
                                    f"{empresa_nombre}/Procedimientos/{filename}"
                                ):
                                    procedimientos_agregados += 1
                                    logger.debug(f"✅ Procedimiento agregado: {filename}")
                            except Exception as e:
                                logger.error(f"❌ Error añadiendo procedimiento {procedimiento.codigo}: {e}")

                    # Crear README si no hay procedimientos (IGUAL que original)
                    if procedimientos_agregados == 0:
                        zf.writestr(
                            f"{empresa_nombre}/Procedimientos/README.txt",
                            "No hay procedimientos con documentos PDF disponibles para esta empresa."
                        )
                    else:
                        logger.info(f"✅ {procedimientos_agregados} procedimientos agregados en última parte")
                else:
                    logger.info(f"⏭️ Procedimientos omitidos (Parte {parte_numero}, se incluirán en Parte {total_partes})")

                # 3. Procesar cada equipo con la MISMA estructura exacta
                for idx, equipo in enumerate(equipos_empresa, 1):
                    try:
                        # MISMO proceso de naming
                        safe_codigo = equipo.codigo_interno.replace('/', '_').replace('\\', '_')
                        equipo_folder = f"{empresa_nombre}/Equipos/{safe_codigo}"

                        # a) Hoja de vida PDF (MISMO proceso)
                        try:
                            from .views.reports import _generate_equipment_hoja_vida_pdf_content
                            # Crear request mock como en el original
                            class MockRequest:
                                def __init__(self, user):
                                    self.user = user

                            mock_request = MockRequest(user)
                            hoja_vida_pdf_content = _generate_equipment_hoja_vida_pdf_content(mock_request, equipo)
                            zf.writestr(f"{equipo_folder}/Hoja_de_vida.pdf", hoja_vida_pdf_content)
                        except Exception as e:
                            logger.error(f"Error generando PDF para {equipo.codigo_interno}: {e}")
                            zf.writestr(f"{equipo_folder}/Hoja_de_vida_ERROR.txt", f"Error: {e}")

                        # b) Calibraciones con subcarpetas (MISMA estructura)
                        calibraciones = equipo.calibraciones.all()
                        cal_idx = 1
                        conf_idx = 1
                        int_idx = 1

                        for cal in calibraciones:
                            # Certificados de calibración
                            if cal.documento_calibracion:
                                try:
                                    if default_storage.exists(cal.documento_calibracion.name):
                                        with default_storage.open(cal.documento_calibracion.name, 'rb') as f:
                                            content = f.read()
                                            filename = f"cal_{cal_idx}.pdf"
                                            zf.writestr(f"{equipo_folder}/Calibraciones/Certificados_Calibracion/{filename}", content)
                                            cal_idx += 1
                                except Exception as e:
                                    logger.error(f"Error añadiendo certificado calibración: {e}")

                            # Confirmación metrológica
                            if cal.confirmacion_metrologica_pdf:
                                try:
                                    if default_storage.exists(cal.confirmacion_metrologica_pdf.name):
                                        with default_storage.open(cal.confirmacion_metrologica_pdf.name, 'rb') as f:
                                            content = f.read()
                                            filename = f"conf_{conf_idx}.pdf"
                                            zf.writestr(f"{equipo_folder}/Calibraciones/Confirmacion_Metrologica/{filename}", content)
                                            conf_idx += 1
                                except Exception as e:
                                    logger.error(f"Error añadiendo confirmación metrológica: {e}")

                            # Intervalos de calibración
                            if cal.intervalos_calibracion_pdf:
                                try:
                                    if default_storage.exists(cal.intervalos_calibracion_pdf.name):
                                        with default_storage.open(cal.intervalos_calibracion_pdf.name, 'rb') as f:
                                            content = f.read()
                                            filename = f"int_{int_idx}.pdf"
                                            zf.writestr(f"{equipo_folder}/Calibraciones/Intervalos_Calibracion/{filename}", content)
                                            int_idx += 1
                                except Exception as e:
                                    logger.error(f"Error añadiendo intervalos calibración: {e}")

                        # c) Mantenimientos (MISMA estructura)
                        mantenimientos = equipo.mantenimientos.all()
                        for mant_idx, mant in enumerate(mantenimientos, 1):
                            if mant.documento_mantenimiento:
                                try:
                                    if default_storage.exists(mant.documento_mantenimiento.name):
                                        with default_storage.open(mant.documento_mantenimiento.name, 'rb') as f:
                                            content = f.read()
                                            filename = f"mant_{mant_idx}.pdf"
                                            zf.writestr(f"{equipo_folder}/Mantenimientos/{filename}", content)
                                except Exception as e:
                                    logger.error(f"Error añadiendo archivo mantenimiento: {e}")

                        # d) Comprobaciones (ESTRUCTURA COMPLETA con todos los campos)
                        comprobaciones = equipo.comprobaciones.all()
                        comp_cert_idx = 1
                        for comp_idx, comp in enumerate(comprobaciones, 1):
                            # Comprobación PDF (certificados principales - generados en plataforma)
                            if comp.comprobacion_pdf:
                                try:
                                    if default_storage.exists(comp.comprobacion_pdf.name):
                                        with default_storage.open(comp.comprobacion_pdf.name, 'rb') as f:
                                            content = f.read()
                                            filename = f"comp_{comp_cert_idx}.pdf"
                                            zf.writestr(f"{equipo_folder}/Comprobaciones/Certificados_Comprobacion/{filename}", content)
                                            comp_cert_idx += 1
                                except Exception as e:
                                    logger.error(f"Error añadiendo certificado comprobación: {e}")

                            # Documento Externo (proveedor)
                            if comp.documento_externo:
                                try:
                                    if default_storage.exists(comp.documento_externo.name):
                                        with default_storage.open(comp.documento_externo.name, 'rb') as f:
                                            content = f.read()
                                            filename = os.path.basename(comp.documento_externo.name)
                                            zf.writestr(f"{equipo_folder}/Comprobaciones/Documentos_Externos/{filename}", content)
                                except Exception as e:
                                    logger.error(f"Error añadiendo documento externo comprobación: {e}")

                            # Documento Interno (SAM)
                            if comp.documento_interno:
                                try:
                                    if default_storage.exists(comp.documento_interno.name):
                                        with default_storage.open(comp.documento_interno.name, 'rb') as f:
                                            content = f.read()
                                            filename = os.path.basename(comp.documento_interno.name)
                                            zf.writestr(f"{equipo_folder}/Comprobaciones/Documentos_Internos/{filename}", content)
                                except Exception as e:
                                    logger.error(f"Error añadiendo documento interno comprobación: {e}")

                            # Documento General (documentos manuales subidos)
                            if comp.documento_comprobacion:
                                try:
                                    if default_storage.exists(comp.documento_comprobacion.name):
                                        with default_storage.open(comp.documento_comprobacion.name, 'rb') as f:
                                            content = f.read()
                                            filename = os.path.basename(comp.documento_comprobacion.name)
                                            zf.writestr(f"{equipo_folder}/Comprobaciones/Documentos_Generales/{filename}", content)
                                except Exception as e:
                                    logger.error(f"Error añadiendo archivo comprobación: {e}")

                        # e) Documentos del equipo (MISMA estructura)
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
                                        if default_storage.exists(doc_field.name):
                                            with default_storage.open(doc_field.name, 'rb') as f:
                                                content = f.read()
                                                zf.writestr(f"{equipo_folder}/{nombre_descriptivo}", content)
                                except Exception as e:
                                    logger.error(f"Error añadiendo documento del equipo: {e}")

                        # f) Carpeta de Baja SOLO si estado = 'De Baja' (IGUAL que original)
                        if equipo.estado == ESTADO_DE_BAJA:
                            try:
                                baja_registro = equipo.baja_registro
                                if baja_registro and baja_registro.documento_baja:
                                    if default_storage.exists(baja_registro.documento_baja.name):
                                        with default_storage.open(baja_registro.documento_baja.name, 'rb') as f:
                                            content = f.read()
                                            filename = "documento_baja.pdf"
                                            zf.writestr(f"{equipo_folder}/Baja/{filename}", content)
                            except Exception as e:
                                logger.error(f"Error añadiendo documento de baja para {equipo.codigo_interno}: {e}")

                        # Liberar memoria cada 10 equipos para evitar overflow
                        if idx % 10 == 0:
                            gc.collect()
                            logger.debug(f"Procesados {idx}/{num_equipos} equipos")

                    except Exception as e:
                        logger.error(f"Error procesando equipo {equipo.codigo_interno}: {e}")
                        continue

            # Subir archivo final a storage con nombre que incluye parte y rango
            final_path = self._upload_to_storage(
                temp_zip_path,
                empresa,
                parte_numero,
                total_partes,
                rango_inicio,
                rango_fin
            )

            # Obtener tamaño
            file_size = os.path.getsize(temp_zip_path)

            # Limpiar archivo temporal con manejo de errores para Windows
            try:
                os.unlink(temp_zip_path)
                logger.debug(f"Archivo temporal eliminado: {temp_zip_path}")
            except (OSError, PermissionError) as e:
                logger.warning(f"No se pudo eliminar archivo temporal {temp_zip_path}: {e}")
                # Intentar eliminar más tarde
                import atexit
                atexit.register(lambda: self._safe_cleanup(temp_zip_path))

            return {
                'success': True,
                'file_path': final_path,
                'file_size': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'equipos_count': num_equipos
            }

        except Exception as e:
            logger.error(f"Error generando ZIP con estructura original: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _upload_to_storage(self, temp_path, empresa, parte_numero=1, total_partes=1, rango_inicio=1, rango_fin=1):
        """Sube el ZIP a storage (S3 o local) con nombre descriptivo"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')

            # Generar nombre de archivo descriptivo con rango de equipos
            if total_partes > 1:
                # Formato: SAM_Equipos_EmpresaX_P1de3_EQ001-035_20251014_1530.zip
                if parte_numero == total_partes:
                    # Última parte incluye "_COMPLETO"
                    file_name = f"zips/SAM_Equipos_{empresa.nombre}_P{parte_numero}de{total_partes}_EQ{rango_inicio:03d}-{rango_fin:03d}_COMPLETO_{timestamp}.zip"
                else:
                    file_name = f"zips/SAM_Equipos_{empresa.nombre}_P{parte_numero}de{total_partes}_EQ{rango_inicio:03d}-{rango_fin:03d}_{timestamp}.zip"
            else:
                # Descarga normal (sin partes)
                file_name = f"zips/SAM_Equipos_{empresa.nombre}_{timestamp}.zip"

            # Subir a storage configurado
            with open(temp_path, 'rb') as f:
                path = default_storage.save(file_name, f)

            logger.info(f"ZIP subido a storage: {path}")
            return path

        except Exception as e:
            logger.error(f"Error subiendo ZIP a storage: {e}")
            return temp_path

    def _safe_cleanup(self, file_path):
        """Limpieza segura de archivos temporales con reintentos"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.debug(f"Archivo temporal eliminado en cleanup: {file_path}")
        except Exception as e:
            logger.warning(f"No se pudo limpiar archivo en cleanup: {e}")


# Instancia global del procesador
async_zip_processor = AsyncZipProcessor()


# Funciones de integración con el sistema existente
def start_async_processor():
    """Inicia el procesador asíncrono"""
    async_zip_processor.start_processor()

def stop_async_processor():
    """Detiene el procesador asíncrono"""
    async_zip_processor.stop_processor()

def add_zip_request_to_queue(zip_request):
    """Agrega una solicitud ZIP a la cola asíncrona"""
    async_zip_processor.add_to_queue(zip_request)

def get_async_queue_status():
    """Obtiene estado de la cola asíncrona"""
    return async_zip_processor.get_queue_status()