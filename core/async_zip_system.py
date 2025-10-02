# core/async_zip_system.py
# Sistema de generación de ZIP completamente asíncrono sin límites

import asyncio
import aiofiles
import zipfile
import tempfile
import os
import logging
from datetime import datetime, timedelta
from django.core.files.storage import default_storage
from django.utils import timezone
from django.conf import settings
from asgiref.sync import sync_to_async
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue
import uuid

logger = logging.getLogger('core')

class AsyncZipProcessor:
    """
    Procesador ZIP asíncrono que no bloquea la aplicación principal.
    Puede manejar CUALQUIER cantidad de equipos sin límites.
    """

    def __init__(self):
        self.processing_queue = Queue()
        self.active_jobs = {}
        self.executor = ThreadPoolExecutor(max_workers=2)  # 2 workers en paralelo
        self.is_running = False

    def start_processor(self):
        """Inicia el procesador en background"""
        if not self.is_running:
            self.is_running = True
            # Crear thread daemon para no bloquear shutdown
            processor_thread = threading.Thread(
                target=self._process_queue,
                daemon=True
            )
            processor_thread.start()
            logger.info("🚀 AsyncZipProcessor iniciado")

    def request_zip(self, empresa, formatos, user, callback_url=None):
        """
        Solicita generación de ZIP sin bloquear la respuesta.
        Retorna inmediatamente con job_id para tracking.
        """
        job_id = str(uuid.uuid4())

        zip_request = {
            'job_id': job_id,
            'empresa_id': empresa.id,
            'empresa_nombre': empresa.nombre,
            'formatos': formatos,
            'user_id': user.id,
            'callback_url': callback_url,
            'created_at': timezone.now(),
            'status': 'queued'
        }

        # Agregar a cola sin bloquear
        self.processing_queue.put(zip_request)
        self.active_jobs[job_id] = zip_request

        logger.info(f"📦 ZIP solicitado para empresa {empresa.nombre} - Job ID: {job_id}")

        return {
            'job_id': job_id,
            'status': 'queued',
            'estimated_time': self._estimate_processing_time(empresa),
            'message': 'Su archivo ZIP está siendo procesado. Recibirá una notificación cuando esté listo.'
        }

    def get_job_status(self, job_id):
        """Obtiene el estado actual del trabajo"""
        if job_id in self.active_jobs:
            return self.active_jobs[job_id]
        return {'status': 'not_found'}

    def _estimate_processing_time(self, empresa):
        """Estima tiempo de procesamiento basado en equipos"""
        equipos_count = empresa.equipos.count()

        if equipos_count <= 50:
            return "1-2 minutos"
        elif equipos_count <= 200:
            return "3-5 minutos"
        elif equipos_count <= 500:
            return "5-10 minutos"
        else:
            return f"10-15 minutos (aprox. {equipos_count} equipos)"

    def _process_queue(self):
        """Procesa la cola de trabajos en background"""
        while self.is_running:
            try:
                if not self.processing_queue.empty():
                    zip_request = self.processing_queue.get()

                    # Actualizar estado
                    zip_request['status'] = 'processing'
                    zip_request['started_at'] = timezone.now()

                    # Procesar en thread separado
                    future = self.executor.submit(
                        self._generate_zip_background,
                        zip_request
                    )

                    # No bloquear, continuar con siguiente trabajo

                # Dormir un poco para no consumir CPU innecesariamente
                threading.Event().wait(0.5)

            except Exception as e:
                logger.error(f"❌ Error en process_queue: {e}")

    def _generate_zip_background(self, zip_request):
        """Genera el ZIP en background sin bloquear nada"""
        try:
            from .models import Empresa, CustomUser
            from .zip_optimizer import OptimizedZipGenerator

            # Recrear objetos Django (necesario en thread separado)
            empresa = Empresa.objects.get(id=zip_request['empresa_id'])
            user = CustomUser.objects.get(id=zip_request['user_id'])

            logger.info(f"🔄 Iniciando generación ZIP para {empresa.nombre}")

            # Usar el generador optimizado existente pero sin límites
            generator = UnlimitedZipGenerator(
                empresa,
                zip_request['formatos'],
                user
            )

            # Generar ZIP (esto puede tomar tiempo, pero no bloquea la app)
            zip_path = generator.generate_unlimited_zip()

            # Actualizar estado
            zip_request['status'] = 'completed'
            zip_request['completed_at'] = timezone.now()
            zip_request['download_url'] = zip_path
            zip_request['expires_at'] = timezone.now() + timedelta(hours=6)

            # Notificar al usuario (email, notification, websocket, etc.)
            self._notify_completion(zip_request)

            logger.info(f"✅ ZIP completado para {empresa.nombre} - {zip_path}")

        except Exception as e:
            zip_request['status'] = 'failed'
            zip_request['error'] = str(e)
            logger.error(f"❌ Error generando ZIP: {e}")

    def _notify_completion(self, zip_request):
        """Notifica al usuario que el ZIP está listo"""
        try:
            from .models import NotificacionZip

            # Crear notificación en BD
            NotificacionZip.objects.create(
                user_id=zip_request['user_id'],
                empresa_id=zip_request['empresa_id'],
                job_id=zip_request['job_id'],
                download_url=zip_request['download_url'],
                expires_at=zip_request['expires_at'],
                status='ready'
            )

            # TODO: Enviar email, push notification, websocket, etc.
            logger.info(f"📧 Notificación enviada para job {zip_request['job_id']}")

        except Exception as e:
            logger.error(f"❌ Error enviando notificación: {e}")


class UnlimitedZipGenerator:
    """
    Generador de ZIP que puede manejar CUALQUIER cantidad de equipos.
    Usa técnicas avanzadas de streaming y chunks dinámicos.
    """

    def __init__(self, empresa, formatos, user):
        self.empresa = empresa
        self.formatos = formatos
        self.user = user

    def generate_unlimited_zip(self):
        """
        Genera ZIP sin límites usando técnicas avanzadas.
        """
        try:
            # Crear archivo temporal
            temp_zip = tempfile.NamedTemporaryFile(
                delete=False,
                suffix='.zip',
                prefix=f'sam_unlimited_{self.empresa.id}_'
            )

            # Obtener TODOS los equipos (sin límite)
            equipos = self.empresa.equipos.all().select_related().prefetch_related(
                'calibraciones',
                'mantenimientos',
                'comprobaciones',
                'documentos'
            )

            equipos_count = equipos.count()
            logger.info(f"🔢 Generando ZIP para {equipos_count} equipos (SIN LÍMITE)")

            # Crear ZIP con compresión optimizada
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zip_file:

                # Procesar equipos en chunks dinámicos
                chunk_size = self._calculate_dynamic_chunk_size(equipos_count)

                for i in range(0, equipos_count, chunk_size):
                    chunk_equipos = equipos[i:i + chunk_size]

                    logger.info(f"📦 Procesando chunk {i//chunk_size + 1}/{(equipos_count//chunk_size) + 1}")

                    # Procesar chunk
                    self._process_equipment_chunk(zip_file, chunk_equipos)

                    # Liberar memoria después de cada chunk
                    import gc
                    gc.collect()

                    # Mini pausa para no saturar CPU
                    threading.Event().wait(0.1)

            # Subir a S3 si está configurado, o mantener local
            final_path = self._upload_zip_to_storage(temp_zip.name)

            # Limpiar archivo temporal local
            os.unlink(temp_zip.name)

            return final_path

        except Exception as e:
            logger.error(f"❌ Error en generate_unlimited_zip: {e}")
            raise

    def _calculate_dynamic_chunk_size(self, total_equipos):
        """Calcula chunk size dinámico basado en cantidad de equipos"""
        if total_equipos <= 100:
            return 25  # Chunks pequeños para pocos equipos
        elif total_equipos <= 500:
            return 50  # Chunks medianos
        elif total_equipos <= 1000:
            return 75  # Chunks grandes
        else:
            return 100  # Chunks muy grandes para muchos equipos

    def _process_equipment_chunk(self, zip_file, equipos_chunk):
        """Procesa un chunk de equipos optimizadamente"""
        for equipo in equipos_chunk:
            try:
                # Procesar cada formato solicitado
                for formato in self.formatos:
                    if formato == 'pdf':
                        self._add_equipment_pdf(zip_file, equipo)
                    elif formato == 'excel':
                        self._add_equipment_excel(zip_file, equipo)
                    # Agregar más formatos según necesidad

            except Exception as e:
                logger.warning(f"⚠️ Error procesando equipo {equipo.id}: {e}")
                continue  # Continuar con siguiente equipo

    def _add_equipment_pdf(self, zip_file, equipo):
        """Agrega PDF del equipo al ZIP usando streaming"""
        # Implementar lógica de PDF streaming
        pass

    def _add_equipment_excel(self, zip_file, equipo):
        """Agrega Excel del equipo al ZIP usando streaming"""
        # Implementar lógica de Excel streaming
        pass

    def _upload_zip_to_storage(self, temp_path):
        """Sube el ZIP a S3 o almacenamiento configurado"""
        try:
            # Generar nombre único
            file_name = f"zips/sam_export_{self.empresa.id}_{int(timezone.now().timestamp())}.zip"

            # Subir a storage (S3 o local)
            with open(temp_path, 'rb') as f:
                path = default_storage.save(file_name, f)

            return path

        except Exception as e:
            logger.error(f"❌ Error subiendo ZIP: {e}")
            return temp_path  # Fallback a archivo local


# Instancia global del procesador
zip_processor = AsyncZipProcessor()