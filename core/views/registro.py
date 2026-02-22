# core/views/registro.py
# Vistas públicas para auto-registro de Trial
# Incluye: permisos automáticos, anti-abuso (honeypot + rate limiting), logo

import re
import logging
from datetime import date, timedelta
from decimal import Decimal

from django.shortcuts import render, redirect
from django.db import transaction
from django.utils.crypto import get_random_string
from django.contrib.auth.models import Permission
from django.core.cache import cache

from ..forms import RegistroTrialForm
from ..models import Empresa, CustomUser, Equipo

logger = logging.getLogger('core')

# Tiempo de cooldown tras registro exitoso (24 horas en segundos)
TRIAL_COOLDOWN_SECONDS = 86400
# Máximo intentos POST por IP por hora
TRIAL_MAX_ATTEMPTS_PER_HOUR = 3


# =============================================================================
# Permisos automáticos por rol
# =============================================================================

PERMISOS_TECNICO = [
    'view_equipo',
    'add_calibracion', 'change_calibracion', 'view_calibracion',
    'add_mantenimiento', 'change_mantenimiento', 'view_mantenimiento',
    'add_comprobacion', 'change_comprobacion', 'view_comprobacion',
    'view_proveedor',
    'view_procedimiento',
    'can_view_prestamo',
]

PERMISOS_ADMINISTRADOR = PERMISOS_TECNICO + [
    'add_equipo', 'change_equipo', 'delete_equipo',
    'delete_calibracion', 'delete_mantenimiento', 'delete_comprobacion',
    'add_bajaequipo', 'change_bajaequipo', 'view_bajaequipo', 'delete_bajaequipo',
    'view_empresa', 'change_empresa',
    'add_proveedor', 'change_proveedor', 'delete_proveedor',
    'add_procedimiento', 'change_procedimiento', 'delete_procedimiento',
    'can_add_prestamo', 'can_change_prestamo',
]

# Gerencia tiene los mismos permisos que admin; el acceso extra se maneja con flags
PERMISOS_GERENCIA = PERMISOS_ADMINISTRADOR


def asignar_permisos_por_rol(user):
    """Asigna permisos Django automáticamente según el rol_usuario."""
    mapa = {
        'TECNICO': PERMISOS_TECNICO,
        'ADMINISTRADOR': PERMISOS_ADMINISTRADOR,
        'GERENCIA': PERMISOS_GERENCIA,
    }
    codenames = mapa.get(user.rol_usuario, PERMISOS_TECNICO)
    permisos = Permission.objects.filter(codename__in=codenames)
    user.user_permissions.set(permisos)


# =============================================================================
# Utilidades anti-abuso
# =============================================================================

def _get_client_ip(request):
    """Obtiene la IP real del cliente (maneja proxies)."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def _check_rate_limit(ip):
    """
    Verifica rate limiting por IP.
    Retorna (permitido: bool, mensaje_error: str|None).
    """
    # Verificar cooldown de 24h tras registro exitoso
    cooldown_key = f'trial_success_{ip}'
    if cache.get(cooldown_key):
        return False, 'Ya se registró un trial desde esta conexión. Intenta en 24 horas.'

    # Verificar intentos por hora
    attempts_key = f'trial_attempts_{ip}'
    attempts = cache.get(attempts_key, 0)
    if attempts >= TRIAL_MAX_ATTEMPTS_PER_HOUR:
        return False, 'Demasiados intentos. Espera un momento antes de intentar de nuevo.'

    return True, None


def _increment_attempts(ip):
    """Incrementa el contador de intentos para una IP."""
    key = f'trial_attempts_{ip}'
    attempts = cache.get(key, 0)
    cache.set(key, attempts + 1, 3600)  # expira en 1 hora


def _set_success_cooldown(ip):
    """Marca cooldown de 24h tras registro exitoso."""
    cache.set(f'trial_success_{ip}', True, TRIAL_COOLDOWN_SECONDS)


# =============================================================================
# Vistas
# =============================================================================

def solicitar_trial(request):
    """
    Vista pública para auto-registro de Trial.
    Crea 1 Empresa + 3 Usuarios (ADMINISTRADOR, GERENCIA, TECNICO)
    con permisos automáticos y protección anti-abuso.
    """
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        client_ip = _get_client_ip(request)

        # Anti-abuso: verificar rate limiting
        allowed, error_msg = _check_rate_limit(client_ip)
        if not allowed:
            form = RegistroTrialForm(request.POST, request.FILES)
            form.add_error(None, error_msg)
            return render(request, 'registration/solicitar_trial.html', {'form': form})

        _increment_attempts(client_ip)

        form = RegistroTrialForm(request.POST, request.FILES)

        # Anti-abuso: honeypot (campo oculto que solo bots llenan)
        if request.POST.get('website', ''):
            # Bot detectado - simular éxito sin crear nada
            logger.warning(f"Honeypot activado desde IP {client_ip}")
            return redirect('core:trial_exitoso')

        if form.is_valid():
            try:
                with transaction.atomic():
                    data = form.cleaned_data

                    # 1. Crear Empresa
                    empresa = Empresa(
                        nombre=data['nombre_empresa'],
                        nit=data['nit'],
                        email=data['email_empresa'],
                        telefono=data.get('telefono', ''),
                    )
                    empresa._plan_set_manually = True
                    empresa.save()

                    # 2. Activar Trial de 30 días
                    empresa.activar_periodo_prueba(duracion_dias=30)

                    # 3. Logo (opcional)
                    logo = data.get('logo_empresa')
                    if logo:
                        empresa.logo_empresa = logo
                        empresa.save(update_fields=['logo_empresa'])

                    # 4. Generar credenciales automáticas para los 3 usuarios
                    #    Formato: prefijo + primeras 5 letras + últimos 4 dígitos NIT
                    nit_clean = re.sub(r'[^0-9]', '', data['nit'])
                    letras = re.sub(r'[^a-zA-Z]', '', data['nombre_empresa']).lower()[:5]
                    nit_sufijo = nit_clean[-4:]
                    admin_username = f"dir{letras}{nit_sufijo}"
                    gerente_username = f"ger{letras}{nit_sufijo}"
                    tecnico_username = f"tec{letras}{nit_sufijo}"
                    admin_password = f"Dir.{data['nit']}"
                    gerente_password = f"Ger.{data['nit']}"
                    tecnico_password = f"Tec.{data['nit']}"

                    # 5. Crear usuario ADMINISTRADOR
                    admin_user = CustomUser.objects.create_user(
                        username=admin_username,
                        email=data['email_empresa'],
                        password=admin_password,
                        first_name='Usuario',
                        last_name='Director',
                        empresa=empresa,
                        rol_usuario='ADMINISTRADOR',
                        is_active=True,
                    )
                    asignar_permisos_por_rol(admin_user)

                    # 6. Crear usuario GERENCIA
                    gerente_user = CustomUser.objects.create_user(
                        username=gerente_username,
                        email=f"gerencia@{nit_clean}.trial.sam",
                        password=gerente_password,
                        first_name='Usuario',
                        last_name='Gerencia',
                        empresa=empresa,
                        rol_usuario='GERENCIA',
                        is_management_user=True,
                        can_access_dashboard_decisiones=True,
                        is_active=True,
                    )
                    asignar_permisos_por_rol(gerente_user)

                    # 7. Crear usuario TECNICO
                    tecnico_user = CustomUser.objects.create_user(
                        username=tecnico_username,
                        email=f"tecnico@{nit_clean}.trial.sam",
                        password=tecnico_password,
                        first_name='Usuario',
                        last_name='Técnico',
                        empresa=empresa,
                        rol_usuario='TECNICO',
                        is_active=True,
                    )
                    asignar_permisos_por_rol(tecnico_user)

                    # 8. Crear equipo demo para el tour
                    fecha_hoy = date.today()
                    Equipo.objects.create(
                        codigo_interno='EQ-DEMO-001',
                        nombre='Balanza Analítica (Demo)',
                        empresa=empresa,
                        tipo_equipo='Equipo de Medición',
                        marca='Ohaus',
                        modelo='Pioneer PX224',
                        numero_serie='DEMO-SN-2024',
                        ubicacion='Laboratorio Principal',
                        responsable=admin_user.get_full_name() or admin_user.username,
                        estado='Activo',
                        fecha_adquisicion=fecha_hoy - timedelta(days=365),
                        rango_medida='0 - 220 g',
                        resolucion='0.0001 g (0.1 mg)',
                        error_maximo_permisible='±0.0002 g',
                        frecuencia_calibracion_meses=Decimal('12'),
                        fecha_ultima_calibracion=fecha_hoy - timedelta(days=335),
                        proxima_calibracion=fecha_hoy + timedelta(days=30),
                        observaciones='Equipo de demostración creado automáticamente. '
                                      'Puedes editarlo o eliminarlo cuando quieras.',
                    )

                    # 9. Guardar credenciales en sesión
                    request.session['trial_credenciales'] = {
                        'empresa_nombre': empresa.nombre,
                        'admin': {
                            'username': admin_user.username,
                            'password': admin_password,
                            'rol': 'ADMINISTRADOR',
                            'email': admin_user.email,
                            'nombre': 'Usuario Director',
                        },
                        'gerente': {
                            'username': gerente_user.username,
                            'password': gerente_password,
                            'rol': 'GERENCIA',
                            'email': gerente_user.email,
                            'nombre': 'Usuario Gerencia',
                        },
                        'tecnico': {
                            'username': tecnico_user.username,
                            'password': tecnico_password,
                            'rol': 'TECNICO',
                            'email': tecnico_user.email,
                            'nombre': 'Usuario Técnico',
                        },
                    }

                    # Anti-abuso: cooldown de 24h para esta IP
                    _set_success_cooldown(client_ip)

                    logger.info(
                        f"Trial registrado: empresa='{empresa.nombre}', "
                        f"admin='{admin_user.username}', nit='{data['nit']}', ip={client_ip}"
                    )

                return redirect('core:trial_exitoso')

            except Exception as e:
                logger.error(f"Error en registro de trial: {e}")
                form.add_error(None, "Ocurrió un error al crear la cuenta. Intenta de nuevo.")
    else:
        form = RegistroTrialForm()

    return render(request, 'registration/solicitar_trial.html', {'form': form})


def trial_exitoso(request):
    """
    Muestra las credenciales de los 3 usuarios creados tras el registro de Trial.
    """
    credenciales = request.session.get('trial_credenciales')
    if not credenciales:
        return redirect('core:solicitar_trial')

    return render(request, 'registration/trial_exitoso.html', {
        'credenciales': credenciales,
    })
