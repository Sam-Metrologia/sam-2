# core/context_processors.py

from django.db.models import Count, Q
from django.contrib.auth.models import AnonymousUser
from .models import Equipo, Mantenimiento, Calibracion, Comprobacion, Empresa

def company_data(request):
    """
    Agrega datos de la empresa al contexto de la plantilla.
    """
    return {
        'nombre_empresa': 'SAM Metrología',
        'eslogan_empresa': 'Gestión de Equipos de Medición',
    }

def unread_messages_count(request):
    """
    Calcula el número de mensajes no leídos para el usuario actual.
    """
    if isinstance(request.user, AnonymousUser) or not request.user.is_authenticated:
        return {
            'unread_messages_count': 0
        }

    return {
        'unread_messages_count': 0
    }


def aprobaciones_pendientes_count(request):
    """
    Calcula el número de aprobaciones pendientes y rechazos para el usuario actual.
    Muestra badge en el menú de Aprobaciones estilo WhatsApp/redes sociales.

    Documentos que requieren aprobación:
    - Confirmaciones metrológicas (en Calibracion: confirmacion_estado_aprobacion)
    - Intervalos de calibración (en Calibracion: intervalos_estado_aprobacion)
    - Comprobaciones metrológicas (en Comprobacion: estado_aprobacion)
    """
    if isinstance(request.user, AnonymousUser) or not request.user.is_authenticated:
        return {
            'aprobaciones_pendientes_count': 0,
            'aprobaciones_rechazadas_count': 0,
            'aprobaciones_total_badge': 0,
        }

    user = request.user
    pendientes = 0
    rechazados = 0

    try:
        # Determinar si es aprobador (gerente, admin o superuser)
        es_aprobador = user.is_superuser or (hasattr(user, 'rol_usuario') and user.rol_usuario in ['ADMINISTRADOR', 'GERENCIA'])

        if user.empresa or user.is_superuser:
            # Filtro base por empresa
            if user.is_superuser:
                empresa_filter = Q()  # Sin filtro, ve todas las empresas
            else:
                empresa_filter = Q(equipo__empresa=user.empresa)

            if es_aprobador:
                # Aprobador ve pendientes de otros usuarios

                # Confirmaciones metrológicas pendientes (solo las generadas por plataforma)
                pendientes += Calibracion.objects.filter(
                    empresa_filter,
                    confirmacion_estado_aprobacion='pendiente',
                    confirmacion_metrologica_pdf__isnull=False,
                    confirmacion_metrologica_datos__isnull=False
                ).exclude(
                    confirmacion_metrologica_datos={}
                ).exclude(creado_por=user).count()

                # Intervalos de calibración pendientes
                pendientes += Calibracion.objects.filter(
                    empresa_filter,
                    intervalos_estado_aprobacion='pendiente',
                    intervalos_calibracion_pdf__isnull=False,
                    intervalos_calibracion_datos__isnull=False
                ).exclude(
                    intervalos_calibracion_datos={}
                ).exclude(creado_por=user).count()

                # Comprobaciones metrológicas pendientes
                pendientes += Comprobacion.objects.filter(
                    empresa_filter,
                    estado_aprobacion='pendiente',
                    comprobacion_pdf__isnull=False,
                    datos_comprobacion__isnull=False
                ).exclude(
                    datos_comprobacion={}
                ).exclude(creado_por=user).count()
            else:
                # Usuario normal ve sus propios rechazos
                user_filter = Q(creado_por=user)

                # Confirmaciones rechazadas
                rechazados += Calibracion.objects.filter(
                    empresa_filter & user_filter,
                    confirmacion_estado_aprobacion='rechazado'
                ).count()

                # Intervalos rechazados
                rechazados += Calibracion.objects.filter(
                    empresa_filter & user_filter,
                    intervalos_estado_aprobacion='rechazado'
                ).count()

                # Comprobaciones rechazadas
                rechazados += Comprobacion.objects.filter(
                    empresa_filter & user_filter,
                    estado_aprobacion='rechazado'
                ).count()
    except Exception:
        # En caso de error, no mostrar badge
        pass

    total = pendientes + rechazados

    return {
        'aprobaciones_pendientes_count': pendientes,
        'aprobaciones_rechazadas_count': rechazados,
        'aprobaciones_total_badge': total,
    }


def modo_trabajo_context(request):
    """
    Agrega información del modo trabajo (impersonación) al contexto.
    Solo visible para superusuarios o cuando están impersonando.
    """
    from .utils.impersonation import is_impersonating, get_impersonator

    if isinstance(request.user, AnonymousUser) or not request.user.is_authenticated:
        return {
            'modo_trabajo_activo': False,
            'superusuario_original': None,
            'empresas_disponibles': [],
            'puede_usar_modo_trabajo': False,
        }

    impersonating = is_impersonating(request)
    impersonator = get_impersonator(request) if impersonating else None

    # Solo superusuarios reales o impersonando pueden usar modo trabajo
    es_superuser_real = request.user.is_superuser and not impersonating
    puede_usar_modo_trabajo = es_superuser_real or impersonating

    # Obtener empresas disponibles para el selector
    empresas_disponibles = []
    if puede_usar_modo_trabajo:
        try:
            empresas_disponibles = list(
                Empresa.objects.filter(is_deleted=False)
                .order_by('nombre')
                .values('id', 'nombre')
            )
        except Exception:
            pass

    return {
        'modo_trabajo_activo': impersonating,
        'superusuario_original': impersonator,
        'empresas_disponibles': empresas_disponibles,
        'puede_usar_modo_trabajo': puede_usar_modo_trabajo,
        'empresa_trabajo': request.user.empresa if impersonating else None,
        'usuario_impersonado': request.user if impersonating else None,
    }