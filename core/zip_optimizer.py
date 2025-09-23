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
    CHUNK_SIZE = 50  # Equipos por chunk (aumentado de 35)
    MEMORY_LIMIT_MB = 100  # Límite de memoria por operación
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

            # Obtener equipos de la empresa
            equipos = self.empresa.equipos.filter(
                estado__in=['Activo', 'En Mantenimiento', 'En Calibración', 'En Comprobación']
            ).select_related().prefetch_related(
                'calibraciones__procedimiento',
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
        from core.views import generar_hoja_vida_pdf_content

        for idx, equipo in enumerate(equipos_chunk):
            try:
                equipo_folder = f"Equipos/{equipo.codigo_interno}_{equipo.nombre}/"

                # Generar PDFs si están seleccionados
                if 'pdf' in self.formatos_seleccionados:
                    pdf_content = self._generate_pdf_optimized(equipo)
                    if pdf_content:
                        zip_file.writestr(
                            f"{equipo_folder}Hoja_Vida_{equipo.codigo_interno}.pdf",
                            pdf_content
                        )

                # Generar Excel si está seleccionado
                if 'excel' in self.formatos_seleccionados:
                    excel_content = self._generate_excel_optimized(equipo)
                    if excel_content:
                        zip_file.writestr(
                            f"{equipo_folder}Datos_{equipo.codigo_interno}.xlsx",
                            excel_content
                        )

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
            from core.views import generar_hoja_vida_pdf_content

            # Generar PDF en memoria
            pdf_buffer = BytesIO()
            pdf_content = generar_hoja_vida_pdf_content(equipo)

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