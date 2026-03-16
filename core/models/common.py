# core/models/common.py
# Funciones auxiliares compartidas por todos los modelos

from dateutil.relativedelta import relativedelta


def meses_decimales_a_relativedelta(meses_decimal):
    """
    Convierte meses decimales a un objeto relativedelta con meses y días.

    Permite frecuencias más precisas como 1.5 meses (1 mes + 15 días)
    o 2.25 meses (2 meses + 7 días).

    Ejemplos:
        - 1.5 meses = 1 mes + 15 días
        - 2.25 meses = 2 meses + 7 días
        - 0.5 meses = 15 días
        - 6.0 meses = 6 meses exactos

    Args:
        meses_decimal (Decimal): Número de meses (puede tener decimales)

    Returns:
        relativedelta: Objeto relativedelta con meses y días calculados
    """
    if meses_decimal is None:
        return relativedelta(months=0)

    # Convertir Decimal a float
    meses_float = float(meses_decimal)

    # Separar parte entera (meses) y decimal (fracción de mes)
    meses_enteros = int(meses_float)
    fraccion_mes = meses_float - meses_enteros

    # Convertir fracción de mes a días (promedio de 30.44 días por mes)
    dias_adicionales = round(fraccion_mes * 30.44)

    return relativedelta(months=meses_enteros, days=dias_adicionales)


def get_upload_path(instance, filename):
    """Define la ruta de subida para los archivos de equipo y sus actividades."""
    import re
    import os
    import uuid

    # Sanitizar el nombre del archivo
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w\-_\.]', '_', filename)

    # Importaciones diferidas para evitar importaciones circulares
    from core.models.equipment import Equipo, BajaEquipo
    from core.models.activities import Calibracion, Mantenimiento, Comprobacion
    from core.models.catalogs import Procedimiento
    from core.models.documents import Documento

    base_code = None
    if isinstance(instance, Equipo):
        base_code = instance.codigo_interno
    elif hasattr(instance, 'equipo') and hasattr(instance.equipo, 'codigo_interno'):
        base_code = instance.equipo.codigo_interno
    elif isinstance(instance, Procedimiento):
        base_code = instance.codigo
    elif isinstance(instance, Documento):
        if instance.pk:
            base_code = f"doc_{instance.pk}"
        else:
            base_code = f"temp_doc_{uuid.uuid4()}"

    if not base_code:
        raise AttributeError(f"No se pudo determinar el código interno del equipo/procedimiento/documento para la instancia de tipo {type(instance).__name__}. Asegúrese de que tiene un código definido.")

    # Sanitizar el código base
    safe_base_code = re.sub(r'[^\w\-_]', '_', str(base_code))

    # Construir la ruta base dentro de MEDIA_ROOT
    base_path = f"documentos/{safe_base_code}/"

    # Determinar subcarpeta específica para el tipo de documento
    subfolder = ""
    if isinstance(instance, Calibracion):
        if 'confirmacion' in filename.lower():
            subfolder = "calibraciones/confirmaciones/"
        elif 'intervalos' in filename.lower():
            subfolder = "calibraciones/intervalos/"
        else: # Por defecto, si no es confirmación o intervalos, es certificado
            subfolder = "calibraciones/certificados/"
    elif isinstance(instance, Mantenimiento):
        subfolder = "mantenimientos/"
    elif isinstance(instance, Comprobacion):
        subfolder = "comprobaciones/"
    elif isinstance(instance, BajaEquipo):
        subfolder = "bajas_equipo/"
    elif isinstance(instance, Equipo):
        # Para los documentos directos del equipo, usar subcarpetas más específicas
        if 'compra' in filename.lower():
            subfolder = "equipos/compra/"
        elif 'ficha_tecnica' in filename.lower() or 'ficha-tecnica' in filename.lower():
            subfolder = "equipos/ficha_tecnica/"
        elif 'manual' in filename.lower():
            subfolder = "equipos/manuales/"
        elif filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            subfolder = "equipos/imagenes/"
        else:
            subfolder = "equipos/otros_documentos/"
    elif isinstance(instance, Procedimiento):
        subfolder = "procedimientos/" # Subcarpeta para documentos de procedimiento
    elif isinstance(instance, Documento): # Nueva subcarpeta para documentos genéricos
        subfolder = "generales/"

    # Asegurarse de que el nombre del archivo es seguro
    safe_filename = filename # Por simplicidad, se mantiene el nombre original, pero es un punto de mejora

    return os.path.join(base_path, subfolder, safe_filename)
