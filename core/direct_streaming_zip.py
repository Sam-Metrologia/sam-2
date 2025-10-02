# core/direct_streaming_zip.py
# Sistema de streaming directo para ZIPs pequeños/medianos

from django.http import StreamingHttpResponse
import zipfile
import io
import tempfile
from django.core.files.storage import default_storage
import logging

logger = logging.getLogger('core')

class DirectStreamingZip:
    """
    Genera ZIP directamente en streaming para descargas inmediatas.
    Ideal para empresas pequeñas-medianas (hasta 200 equipos).
    """

    def __init__(self, empresa, formatos, user):
        self.empresa = empresa
        self.formatos = formatos
        self.user = user

    def generate_streaming_response(self):
        """
        Genera ZIP directamente como streaming response.
        El usuario ve la descarga inmediatamente.
        """
        try:
            equipos = self.empresa.equipos.all().select_related().prefetch_related(
                'calibraciones', 'mantenimientos', 'comprobaciones'
            )

            filename = f"SAM_Export_{self.empresa.nombre}_{timezone.now().strftime('%Y%m%d_%H%M')}.zip"

            def zip_stream_generator():
                """Generador que produce el ZIP en chunks"""

                # Crear buffer en memoria para ZIP pequeño
                zip_buffer = io.BytesIO()

                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zip_file:

                    # Procesar equipos en chunks pequeños
                    chunk_size = 20  # Procesar 20 equipos por vez
                    total_equipos = equipos.count()

                    for i in range(0, total_equipos, chunk_size):
                        chunk_equipos = equipos[i:i + chunk_size]

                        for equipo in chunk_equipos:
                            try:
                                # Agregar archivos del equipo
                                self._add_equipment_files(zip_file, equipo)

                            except Exception as e:
                                logger.warning(f"Error procesando equipo {equipo.id}: {e}")
                                continue

                        # Yield control para no bloquear
                        yield b''  # Yield vacío para mantener conexión

                # Al finalizar, enviar el ZIP completo
                zip_buffer.seek(0)

                # Leer en chunks y enviar
                while True:
                    chunk = zip_buffer.read(8192)  # 8KB chunks
                    if not chunk:
                        break
                    yield chunk

                zip_buffer.close()

            # Crear streaming response
            response = StreamingHttpResponse(
                zip_stream_generator(),
                content_type='application/zip'
            )

            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Cache-Control'] = 'no-cache'

            return response

        except Exception as e:
            logger.error(f"Error en generate_streaming_response: {e}")
            raise

    def _add_equipment_files(self, zip_file, equipo):
        """Agrega archivos de un equipo al ZIP"""

        # Crear carpeta para el equipo
        equipo_folder = f"Equipos/{equipo.codigo_interno}/"

        try:
            # PDF de hoja de vida
            if 'pdf' in self.formatos:
                pdf_content = self._generate_equipment_pdf(equipo)
                if pdf_content:
                    zip_file.writestr(
                        f"{equipo_folder}Hoja_Vida_{equipo.codigo_interno}.pdf",
                        pdf_content
                    )

            # Excel de datos
            if 'excel' in self.formatos:
                excel_content = self._generate_equipment_excel(equipo)
                if excel_content:
                    zip_file.writestr(
                        f"{equipo_folder}Datos_{equipo.codigo_interno}.xlsx",
                        excel_content
                    )

            # Documentos adjuntos
            if 'documentos' in self.formatos:
                self._add_equipment_documents(zip_file, equipo, equipo_folder)

        except Exception as e:
            logger.warning(f"Error agregando archivos para equipo {equipo.id}: {e}")

    def _generate_equipment_pdf(self, equipo):
        """Genera PDF para un equipo específico"""
        try:
            # Usar tu sistema existente de PDF
            from .pdf_generator import PDFGenerator

            pdf_gen = PDFGenerator()
            return pdf_gen.generate_equipment_pdf(equipo)

        except Exception as e:
            logger.warning(f"Error generando PDF para equipo {equipo.id}: {e}")
            return None

    def _generate_equipment_excel(self, equipo):
        """Genera Excel para un equipo específico"""
        try:
            # Implementar generación de Excel
            import openpyxl
            from openpyxl.utils.dataframe import dataframe_to_rows
            import pandas as pd
            from io import BytesIO

            # Crear workbook
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Datos del Equipo"

            # Datos básicos del equipo
            data = [
                ['Código Interno', equipo.codigo_interno],
                ['Descripción', equipo.descripcion],
                ['Marca', equipo.marca],
                ['Modelo', equipo.modelo],
                ['Serie', equipo.serie],
                ['Estado', equipo.estado],
                # Agregar más campos según necesidad
            ]

            for row in data:
                ws.append(row)

            # Guardar en buffer
            buffer = BytesIO()
            wb.save(buffer)
            buffer.seek(0)

            return buffer.getvalue()

        except Exception as e:
            logger.warning(f"Error generando Excel para equipo {equipo.id}: {e}")
            return None

    def _add_equipment_documents(self, zip_file, equipo, equipo_folder):
        """Agrega documentos adjuntos del equipo"""
        try:
            documentos = equipo.documentos.all()

            for doc in documentos:
                if doc.archivo and default_storage.exists(doc.archivo.name):
                    try:
                        # Streaming del archivo desde storage
                        with default_storage.open(doc.archivo.name, 'rb') as f:
                            doc_content = f.read()

                        zip_file.writestr(
                            f"{equipo_folder}Documentos/{doc.nombre or 'documento'}.{doc.archivo.name.split('.')[-1]}",
                            doc_content
                        )

                    except Exception as e:
                        logger.warning(f"Error agregando documento {doc.id}: {e}")

        except Exception as e:
            logger.warning(f"Error agregando documentos para equipo {equipo.id}: {e}")


# Vista para usar streaming directo
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

@login_required
def download_streaming_zip(request):
    """
    Vista para descarga con streaming directo.
    Para empresas pequeñas-medianas.
    """
    try:
        empresa_id = request.POST.get('empresa_id')
        formatos = request.POST.getlist('formatos[]')

        empresa = get_object_or_404(Empresa, id=empresa_id)

        # Verificar permisos
        if not request.user.is_superuser and request.user.empresa != empresa:
            return JsonResponse({'error': 'Sin permisos'})

        # Verificar si es adecuado para streaming directo
        equipos_count = empresa.equipos.count()

        if equipos_count > 200:
            return JsonResponse({
                'error': f'Empresa con {equipos_count} equipos. Use descarga asíncrona.',
                'suggest_async': True
            })

        # Generar streaming response
        streaming_zip = DirectStreamingZip(empresa, formatos, request.user)
        return streaming_zip.generate_streaming_response()

    except Exception as e:
        logger.error(f"Error en download_streaming_zip: {e}")
        return JsonResponse({'error': 'Error interno del servidor'})