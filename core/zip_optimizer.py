# core/zip_optimizer.py
# Sistema optimizado de generación de ZIP con streaming y menor uso de RAM

import zipfile
import tempfile
import os
import gc
from datetime import datetime
from django.http import StreamingHttpResponse
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils import timezone
from io import BytesIO
import logging

logger = logging.getLogger('core')

class OptimizedZipGenerator:
    """
    Generador de ZIP optimizado para manejar más equipos con menos RAM.
    Usa streaming y procesamiento por chunks.
    """

    # Configuración optimizada
    CHUNK_SIZE = 100  # Equipos por chunk (aumentado de 50)
    MEMORY_LIMIT_MB = 150  # Límite de memoria por operación
    COMPRESSION_LEVEL = 6  # Compresión balanceada

    def __init__(self, empresa, formatos_seleccionados, user):
        self.empresa = empresa
        self.formatos_seleccionados = formatos_seleccionados
        self.user = user
        self.temp_files = []  # Track temporary files for cleanup

    def generate_streaming_zip(self):
        """
        Genera ZIP usando streaming para optimizar memoria.
        """
        try:
            # Crear archivo temporal para el ZIP
            temp_zip = tempfile.NamedTemporaryFile(
                delete=False,
                suffix='.zip',
                prefix=f'sam_optimized_{self.empresa.id}_'
            )
            self.temp_files.append(temp_zip.name)

            # Obtener equipos de la empresa (TODOS los equipos, no solo activos)
            equipos = self.empresa.equipos.all().select_related().prefetch_related(
                'calibraciones',
                'mantenimientos',
                'comprobaciones'
            )

            total_equipos = equipos.count()
            logger.info(f"Generating optimized ZIP for {total_equipos} equipos from {self.empresa.nombre}")

            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED, compresslevel=self.COMPRESSION_LEVEL) as zip_file:
                # Procesar equipos por chunks
                for chunk_start in range(0, total_equipos, self.CHUNK_SIZE):
                    chunk_end = min(chunk_start + self.CHUNK_SIZE, total_equipos)
                    equipos_chunk = equipos[chunk_start:chunk_end]

                    logger.info(f"Processing chunk {chunk_start}-{chunk_end} of {total_equipos}")

                    # Procesar chunk actual
                    self._process_chunk(zip_file, equipos_chunk, chunk_start)

                    # Forzar liberación de memoria
                    gc.collect()

                # Agregar archivos de empresa
                self._add_empresa_files(zip_file)

                # Agregar procedimientos de la empresa si está seleccionado
                if 'procedimientos' in self.formatos_seleccionados:
                    self._add_procedimientos(zip_file)

            # Retornar información del archivo generado
            file_size = os.path.getsize(temp_zip.name)

            return {
                'success': True,
                'file_path': temp_zip.name,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'total_equipos': total_equipos,
                'chunks_processed': (total_equipos // self.CHUNK_SIZE) + 1
            }

        except Exception as e:
            logger.error(f"Error generating optimized ZIP: {e}")
            self.cleanup_temp_files()
            return {
                'success': False,
                'error': str(e)
            }

    def _process_chunk(self, zip_file, equipos_chunk, chunk_start):
        """
        Procesa un chunk de equipos de forma optimizada.
        """
        from core.views.reports import _generate_equipment_hoja_vida_pdf_content

        for idx, equipo in enumerate(equipos_chunk):
            try:
                equipo_folder = f"Equipos/{equipo.codigo_interno}_{equipo.nombre}/"

                # Generar Hoja de Vida PDF si está seleccionado
                if 'hoja_vida' in self.formatos_seleccionados:
                    pdf_content = self._generate_pdf_optimized(equipo)
                    if pdf_content:
                        zip_file.writestr(
                            f"{equipo_folder}Hoja_Vida_{equipo.codigo_interno}.pdf",
                            pdf_content
                        )

                # Generar Manual Excel si está seleccionado
                if 'manual' in self.formatos_seleccionados:
                    excel_content = self._generate_excel_optimized(equipo)
                    if excel_content:
                        zip_file.writestr(
                            f"{equipo_folder}Manual_Datos_{equipo.codigo_interno}.xlsx",
                            excel_content
                        )

                # Agregar documentos de calibraciones con subcarpetas
                self._add_calibraciones_subcarpetas(zip_file, equipo, equipo_folder)

                # Agregar documentos de mantenimientos
                self._add_mantenimientos(zip_file, equipo, equipo_folder)

                # Agregar documentos de comprobaciones
                self._add_comprobaciones(zip_file, equipo, equipo_folder)

                # Liberar memoria cada 10 equipos
                if (chunk_start + idx + 1) % 10 == 0:
                    gc.collect()

            except Exception as e:
                logger.warning(f"Error processing equipo {equipo.codigo_interno}: {e}")
                continue

    def _generate_pdf_optimized(self, equipo):
        """
        Genera PDF optimizado para el equipo.
        """
        try:
            from core.views.reports import _generate_equipment_hoja_vida_pdf_content

            # Generar PDF en memoria
            pdf_buffer = BytesIO()
            pdf_content = _generate_equipment_hoja_vida_pdf_content(None, equipo)

            # Si es exitoso, retornar el contenido
            if pdf_content:
                return pdf_content

            return None

        except Exception as e:
            logger.warning(f"Error generating PDF for {equipo.codigo_interno}: {e}")
            return None

    def _generate_excel_optimized(self, equipo):
        """
        Genera Excel optimizado para el equipo.
        """
        try:
            import pandas as pd
            from io import BytesIO

            # Crear datos básicos del equipo
            data = {
                'Código Interno': [equipo.codigo_interno],
                'Nombre': [equipo.nombre],
                'Marca': [equipo.marca],
                'Modelo': [equipo.modelo],
                'Serie': [equipo.numero_serie],
                'Estado': [equipo.estado],
                'Próxima Calibración': [equipo.proxima_calibracion],
                'Próximo Mantenimiento': [equipo.proximo_mantenimiento],
                'Ubicación': [str(equipo.ubicacion) if equipo.ubicacion else 'N/A']
            }

            # Crear Excel en memoria
            excel_buffer = BytesIO()
            df = pd.DataFrame(data)

            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Datos_Equipo', index=False)

                # Agregar calibraciones si existen
                calibraciones = equipo.calibraciones.all()[:20]  # Limitar a 20 más recientes
                if calibraciones:
                    cal_data = []
                    for cal in calibraciones:
                        cal_data.append({
                            'Fecha': cal.fecha_calibracion,
                            'Resultado': cal.resultado,
                            'Procedimiento': str(cal.procedimiento) if cal.procedimiento else 'N/A',
                            'Observaciones': cal.observaciones or 'N/A'
                        })

                    cal_df = pd.DataFrame(cal_data)
                    cal_df.to_excel(writer, sheet_name='Calibraciones', index=False)

            excel_buffer.seek(0)
            return excel_buffer.getvalue()

        except Exception as e:
            logger.warning(f"Error generating Excel for {equipo.codigo_interno}: {e}")
            return None

    def _add_empresa_files(self, zip_file):
        """
        Agrega archivos de la empresa al ZIP.
        """
        try:
            # Agregar logo de empresa si existe
            if self.empresa.logo_empresa:
                try:
                    if default_storage.exists(self.empresa.logo_empresa.name):
                        logo_content = default_storage.open(self.empresa.logo_empresa.name).read()
                        file_extension = os.path.splitext(self.empresa.logo_empresa.name)[1]
                        zip_file.writestr(
                            f"Empresa/Logo_Empresa{file_extension}",
                            logo_content
                        )
                except Exception as e:
                    logger.warning(f"Error adding empresa logo: {e}")

            # Agregar información de la empresa
            empresa_info = f"""
INFORMACIÓN DE LA EMPRESA
========================

Nombre: {self.empresa.nombre}
NIT: {self.empresa.nit or 'N/A'}
Dirección: {self.empresa.direccion or 'N/A'}
Teléfono: {self.empresa.telefono or 'N/A'}
Email: {self.empresa.email or 'N/A'}

Fecha de Generación: {timezone.now().strftime('%d/%m/%Y %H:%M')}
Generado por: {self.user.get_full_name() or self.user.username}

Total de Equipos: {self.empresa.equipos.filter(estado__in=['Activo', 'En Mantenimiento', 'En Calibración', 'En Comprobación']).count()}
"""

            zip_file.writestr("Empresa/Informacion_Empresa.txt", empresa_info.encode('utf-8'))

        except Exception as e:
            logger.warning(f"Error adding empresa files: {e}")

    def cleanup_temp_files(self):
        """
        Limpia archivos temporales.
        """
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                logger.warning(f"Error cleaning temp file {temp_file}: {e}")

        self.temp_files.clear()

    def __del__(self):
        """
        Cleanup cuando se destruye el objeto.
        """
        self.cleanup_temp_files()

    def _add_calibraciones_subcarpetas(self, zip_file, equipo, equipo_folder):
        """
        Agrega documentos de calibraciones organizados en subcarpetas.
        """
        try:
            calibraciones = equipo.calibraciones.all()
            if calibraciones.exists():
                for calibracion in calibraciones:
                    # Carpeta base de calibraciones
                    cal_folder = f"{equipo_folder}Calibraciones/"

                    # Subcarpeta para certificados de calibración
                    if calibracion.documento_calibracion:
                        subfolder = f"{cal_folder}Certificados_Calibracion/"
                        self._add_file_to_zip(zip_file, calibracion.documento_calibracion, subfolder)

                    # Subcarpeta para confirmación metrológica
                    if calibracion.confirmacion_metrologica_pdf:
                        subfolder = f"{cal_folder}Confirmacion_Metrologica/"
                        self._add_file_to_zip(zip_file, calibracion.confirmacion_metrologica_pdf, subfolder)

                    # Subcarpeta para intervalos de calibración
                    if calibracion.intervalos_calibracion_pdf:
                        subfolder = f"{cal_folder}Intervalos_Calibracion/"
                        self._add_file_to_zip(zip_file, calibracion.intervalos_calibracion_pdf, subfolder)
        except Exception as e:
            logger.warning(f"Error adding calibraciones for {equipo.codigo_interno}: {e}")

    def _add_mantenimientos(self, zip_file, equipo, equipo_folder):
        """
        Agrega documentos de mantenimientos en subcarpetas organizadas.
        """
        try:
            mantenimientos = equipo.mantenimientos.all()
            logger.info(f"[DEBUG] Equipo {equipo.codigo_interno}: {mantenimientos.count()} mantenimientos encontrados")
            if mantenimientos.exists():
                mant_folder = f"{equipo_folder}Mantenimientos/"
                for mantenimiento in mantenimientos:
                    logger.info(f"[DEBUG] Procesando mantenimiento ID:{mantenimiento.pk}")
                    # Documento Externo
                    if mantenimiento.documento_externo:
                        logger.info(f"[DEBUG] -> Agregando documento_externo: {mantenimiento.documento_externo.name}")
                        subfolder = f"{mant_folder}Documentos_Externos/"
                        self._add_file_to_zip(zip_file, mantenimiento.documento_externo, subfolder)

                    # Análisis Interno
                    if mantenimiento.analisis_interno:
                        logger.info(f"[DEBUG] -> Agregando analisis_interno: {mantenimiento.analisis_interno.name}")
                        subfolder = f"{mant_folder}Analisis_Internos/"
                        self._add_file_to_zip(zip_file, mantenimiento.analisis_interno, subfolder)

                    # Documento General
                    if mantenimiento.documento_mantenimiento:
                        logger.info(f"[DEBUG] -> Agregando documento_mantenimiento: {mantenimiento.documento_mantenimiento.name}")
                        subfolder = f"{mant_folder}Documentos_Generales/"
                        self._add_file_to_zip(zip_file, mantenimiento.documento_mantenimiento, subfolder)
            else:
                logger.info(f"[DEBUG] Equipo {equipo.codigo_interno}: Sin mantenimientos")
        except Exception as e:
            logger.error(f"Error adding mantenimientos for {equipo.codigo_interno}: {e}")

    def _add_comprobaciones(self, zip_file, equipo, equipo_folder):
        """
        Agrega documentos de comprobaciones en subcarpetas organizadas.
        """
        try:
            comprobaciones = equipo.comprobaciones.all()
            logger.info(f"[DEBUG] Equipo {equipo.codigo_interno}: {comprobaciones.count()} comprobaciones encontradas")
            if comprobaciones.exists():
                comp_folder = f"{equipo_folder}Comprobaciones/"
                for comprobacion in comprobaciones:
                    logger.info(f"[DEBUG] Procesando comprobacion ID:{comprobacion.pk}")
                    # Documento Externo
                    if comprobacion.documento_externo:
                        logger.info(f"[DEBUG] -> Agregando documento_externo: {comprobacion.documento_externo.name}")
                        subfolder = f"{comp_folder}Documentos_Externos/"
                        self._add_file_to_zip(zip_file, comprobacion.documento_externo, subfolder)

                    # Análisis Interno
                    if comprobacion.analisis_interno:
                        logger.info(f"[DEBUG] -> Agregando analisis_interno: {comprobacion.analisis_interno.name}")
                        subfolder = f"{comp_folder}Analisis_Internos/"
                        self._add_file_to_zip(zip_file, comprobacion.analisis_interno, subfolder)

                    # Documento General
                    if comprobacion.documento_comprobacion:
                        logger.info(f"[DEBUG] -> Agregando documento_comprobacion: {comprobacion.documento_comprobacion.name}")
                        subfolder = f"{comp_folder}Documentos_Generales/"
                        self._add_file_to_zip(zip_file, comprobacion.documento_comprobacion, subfolder)
            else:
                logger.info(f"[DEBUG] Equipo {equipo.codigo_interno}: Sin comprobaciones")
        except Exception as e:
            logger.error(f"Error adding comprobaciones for {equipo.codigo_interno}: {e}")

    def _add_procedimientos(self, zip_file):
        """
        Agrega procedimientos de la empresa.
        """
        try:
            procedimientos = self.empresa.procedimientos.all()
            if procedimientos.exists():
                proc_folder = "Procedimientos/"
                for procedimiento in procedimientos:
                    if procedimiento.documento_pdf:
                        self._add_file_to_zip(zip_file, procedimiento.documento_pdf, proc_folder)
                        logger.info(f"Agregado procedimiento: {procedimiento.nombre}")
                    else:
                        logger.warning(f"Procedimiento sin archivo PDF: {procedimiento.nombre}")
            else:
                logger.info("No hay procedimientos para esta empresa")
        except Exception as e:
            logger.error(f"Error adding procedimientos: {e}")

    def _add_file_to_zip(self, zip_file, file_field, folder_path):
        """
        Agrega un archivo al ZIP desde un FileField.
        """
        try:
            if file_field and file_field.name:
                # Obtener el nombre del archivo sin la ruta
                filename = os.path.basename(file_field.name)
                zip_path = f"{folder_path}{filename}"

                # Leer el contenido del archivo
                if default_storage.exists(file_field.name):
                    with default_storage.open(file_field.name, 'rb') as f:
                        zip_file.writestr(zip_path, f.read())
                    logger.debug(f"Agregado archivo: {zip_path}")
                else:
                    logger.warning(f"Archivo no encontrado: {file_field.name}")
        except Exception as e:
            logger.warning(f"Error adding file {file_field.name}: {e}")


class StreamingZipResponse:
    """
    Respuesta de streaming para descargas ZIP grandes.
    """

    def __init__(self, zip_file_path, filename):
        self.zip_file_path = zip_file_path
        self.filename = filename

    def generate_response(self):
        """
        Genera respuesta de streaming HTTP.
        """
        def file_iterator():
            try:
                with open(self.zip_file_path, 'rb') as f:
                    while True:
                        chunk = f.read(8192)  # 8KB chunks
                        if not chunk:
                            break
                        yield chunk
            finally:
                # Cleanup after streaming
                try:
                    os.unlink(self.zip_file_path)
                except Exception as e:
                    logger.warning(f"Error cleaning up ZIP file: {e}")

        response = StreamingHttpResponse(
            file_iterator(),
            content_type='application/zip'
        )
        response['Content-Disposition'] = f'attachment; filename="{self.filename}"'

        # Obtener tamaño del archivo para el header
        try:
            file_size = os.path.getsize(self.zip_file_path)
            response['Content-Length'] = str(file_size)
        except Exception:
            pass  # Content-Length opcional para streaming

        return response


# Funciones de utilidad para integrar con el sistema existente
def generate_optimized_zip(empresa, formatos_seleccionados, user):
    """
    Función principal para generar ZIP optimizado.
    """
    generator = OptimizedZipGenerator(empresa, formatos_seleccionados, user)
    return generator.generate_streaming_zip()

def create_streaming_download(zip_file_path, empresa_nombre):
    """
    Crea respuesta de descarga streaming.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"SAM_Equipos_{empresa_nombre}_{timestamp}.zip"

    streamer = StreamingZipResponse(zip_file_path, filename)
    return streamer.generate_response()