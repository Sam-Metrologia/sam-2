# core/storage_validators.py
# Validadores para límites de almacenamiento

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
import logging

logger = logging.getLogger(__name__)


class StorageLimitValidator:
    """Validador para verificar límites de almacenamiento por empresa."""

    @staticmethod
    def validate_storage_limit(empresa, archivo_size_bytes=0):
        """
        Valida si la empresa puede subir un archivo sin exceder su límite.

        Args:
            empresa: Instancia del modelo Empresa
            archivo_size_bytes: Tamaño del archivo a subir en bytes

        Raises:
            ValidationError: Si se excede el límite de almacenamiento
        """
        if not empresa:
            raise ValidationError("No se puede validar: empresa no especificada.")

        # Obtener límite y uso actual
        limite_mb = empresa.limite_almacenamiento_mb
        uso_actual_mb = empresa.get_total_storage_used_mb()
        archivo_mb = archivo_size_bytes / (1024 * 1024)

        # Calcular uso proyectado
        uso_proyectado_mb = uso_actual_mb + archivo_mb

        logger.info(f"Validación storage - Empresa: {empresa.nombre}, "
                   f"Límite: {limite_mb}MB, Actual: {uso_actual_mb}MB, "
                   f"Archivo: {archivo_mb:.2f}MB, Proyectado: {uso_proyectado_mb:.2f}MB")

        # Verificar si se excede el límite
        if uso_proyectado_mb > limite_mb:
            exceso_mb = uso_proyectado_mb - limite_mb

            # Crear mensaje profesional para el límite excedido
            if limite_mb >= 1000:  # Mostrar en GB si es apropiado
                limite_display = f"{limite_mb / 1000:.1f} GB"
                exceso_display = f"{exceso_mb / 1000:.1f} GB"
            else:
                limite_display = f"{limite_mb} MB"
                exceso_display = f"{exceso_mb} MB"

            mensaje_profesional = f"Límite de almacenamiento superado. Su plan permite {limite_display}, pero este archivo requiere {exceso_display} adicionales. Por favor, libere espacio o actualice su plan."

            raise ValidationError(mensaje_profesional)

        # Advertencia si está cerca del límite (90%+)
        porcentaje_uso = (uso_proyectado_mb / limite_mb) * 100
        if porcentaje_uso >= 90:
            logger.warning(f"Empresa {empresa.nombre} cerca del límite: {porcentaje_uso:.1f}%")

        return True

    @staticmethod
    def validate_equipment_limit(empresa):
        """
        Valida si la empresa puede crear más equipos.

        Args:
            empresa: Instancia del modelo Empresa

        Raises:
            ValidationError: Si se excede el límite de equipos
        """
        if not empresa:
            raise ValidationError("No se puede validar: empresa no especificada.")

        limite_equipos = empresa.get_limite_equipos()

        # Si el límite es infinito, no hay restricción
        if limite_equipos == float('inf'):
            return True

        from core.models import Equipo
        equipos_actuales = Equipo.objects.filter(empresa=empresa).count()

        logger.info(f"Validación equipos - Empresa: {empresa.nombre}, "
                   f"Límite: {limite_equipos}, Actual: {equipos_actuales}")

        if equipos_actuales >= limite_equipos:
            raise ValidationError(
                f"[LIMITE EQUIPOS] Limite de equipos alcanzado. "
                f"Limite: {limite_equipos}, "
                f"Equipos actuales: {equipos_actuales}. "
                f"No puede crear mas equipos. Contacte al administrador para aumentar su limite."
            )

        return True

    @staticmethod
    def get_storage_summary(empresa):
        """
        Obtiene un resumen del estado de almacenamiento de la empresa.

        Args:
            empresa: Instancia del modelo Empresa

        Returns:
            dict: Resumen con límite, uso, porcentaje y estado
        """
        if not empresa:
            return {
                'limite_mb': 0,
                'uso_mb': 0,
                'porcentaje': 0,
                'estado': 'error',
                'mensaje': 'Empresa no especificada'
            }

        limite_mb = empresa.limite_almacenamiento_mb
        uso_mb = empresa.get_total_storage_used_mb()
        porcentaje = empresa.get_storage_usage_percentage()

        # Determinar estado
        if porcentaje >= 100:
            estado = 'full'
            mensaje = 'Almacenamiento lleno'
        elif porcentaje >= 90:
            estado = 'critical'
            mensaje = 'Almacenamiento crítico'
        elif porcentaje >= 75:
            estado = 'warning'
            mensaje = 'Almacenamiento alto'
        elif porcentaje >= 50:
            estado = 'moderate'
            mensaje = 'Uso moderado'
        else:
            estado = 'good'
            mensaje = 'Almacenamiento disponible'

        return {
            'limite_mb': limite_mb,
            'uso_mb': uso_mb,
            'porcentaje': porcentaje,
            'estado': estado,
            'mensaje': mensaje,
            'disponible_mb': max(0, limite_mb - uso_mb)
        }