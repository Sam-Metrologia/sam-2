from django.apps import AppConfig
import logging

logger = logging.getLogger('core')

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """
        Se ejecuta cuando la aplicación Django está lista.
        Inicializa sistemas en background.
        """
        # ⚠️ DESHABILITADO: El procesador ZIP ahora corre como Background Worker separado
        # No inicializamos el thread worker aquí para evitar conflictos
        # Ver: render.yaml (type: worker) o crear manualmente en Render Dashboard

        # try:
        #     # Inicializar el sistema ZIP asíncrono
        #     from .async_zip_improved import start_async_processor
        #     start_async_processor()
        #     logger.info("🚀 Sistema ZIP asíncrono inicializado al arrancar Django")
        # except Exception as e:
        #     logger.warning(f"⚠️ No se pudo inicializar sistema ZIP asíncrono: {e}")
        #     # No fallar el arranque de Django por esto

        # Importar signals si existen
        try:
            from . import signals
        except ImportError:
            pass
