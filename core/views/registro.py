# core/views/registro.py
# Vistas públicas para auto-registro de Trial
# Incluye: permisos automáticos, anti-abuso (honeypot + rate limiting), logo

import re
import logging
from datetime import date, timedelta
from decimal import Decimal

from django import forms
from django.shortcuts import render, redirect
from django.db import transaction
from django.utils.crypto import get_random_string
from django.contrib.auth.models import Permission
from django.contrib.auth import login as auth_login, update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.contrib import messages
from django.core.cache import cache

from ..forms import RegistroTrialForm
from ..models import Empresa, CustomUser, Equipo
from .pagos import _send_html_email, _EMAIL_STYLE, SAM_FROM_LABEL

logger = logging.getLogger('core')

# Tiempo de cooldown tras registro exitoso (24 horas en segundos)
TRIAL_COOLDOWN_SECONDS = 86400
# Máximo intentos POST por IP por hora
TRIAL_MAX_ATTEMPTS_PER_HOUR = 3


# =============================================================================
# Permisos automáticos por rol
# =============================================================================

PERMISOS_TECNICO = [
    # Equipos
    'view_equipo', 'add_equipo', 'change_equipo',
    # Calibraciones + confirmación metrológica e intervalos
    'add_calibracion', 'change_calibracion', 'view_calibracion',
    'can_view_calibracion', 'can_change_calibracion',
    # Mantenimientos
    'add_mantenimiento', 'change_mantenimiento', 'view_mantenimiento',
    # Comprobaciones
    'add_comprobacion', 'change_comprobacion', 'view_comprobacion',
    # Catálogos (solo lectura)
    'view_proveedor',
    'view_procedimiento',
    # Préstamos
    'can_view_prestamo', 'can_add_prestamo', 'can_change_prestamo',
]

PERMISOS_ADMINISTRADOR = PERMISOS_TECNICO + [
    'delete_equipo',
    'delete_calibracion', 'delete_mantenimiento', 'delete_comprobacion',
    'add_bajaequipo', 'change_bajaequipo', 'view_bajaequipo', 'delete_bajaequipo',
    'view_empresa', 'change_empresa',
    'add_proveedor', 'change_proveedor', 'delete_proveedor',
    'add_procedimiento', 'change_procedimiento', 'delete_procedimiento',
    'can_add_prestamo', 'can_change_prestamo',
    # Ubicaciones (requerido por companies.py)
    'view_ubicacion', 'add_ubicacion', 'change_ubicacion', 'delete_ubicacion',
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
    permisos = Permission.objects.filter(
        codename__in=codenames,
        content_type__app_label='core',
    )
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
                        direccion=data.get('direccion', ''),
                        correos_facturacion=data.get('correos_facturacion', ''),
                        correos_notificaciones=data.get('correos_notificaciones', ''),
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
                    # Contraseñas aleatorias seguras (16 chars, letras + dígitos)
                    admin_password = get_random_string(16)
                    gerente_password = get_random_string(16)
                    tecnico_password = get_random_string(16)

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

                # 10. Iniciar sesión automáticamente con el Administrador.
                #     Así el cliente entra directo a la plataforma sin depender
                #     de que recuerde/guarde las credenciales para hacer login.
                auth_login(request, admin_user, backend='django.contrib.auth.backends.ModelBackend')

                # 11. Correo de respaldo con las credenciales (por si no las
                #     guarda en pantalla) y aviso de que el usuario Administrador
                #     ya quedó dentro de la plataforma.
                _enviar_email_bienvenida_trial(
                    empresa, admin_user, gerente_user, tecnico_user,
                    admin_password, gerente_password, tecnico_password,
                )

                return redirect('core:trial_exitoso')

            except Exception as e:
                logger.error(f"Error en registro de trial: {e}")
                form.add_error(None, "Ocurrió un error al crear la cuenta. Intenta de nuevo.")
    else:
        form = RegistroTrialForm()

    return render(request, 'registration/solicitar_trial.html', {'form': form})


class ConfigurarAccesoTrialForm(SetPasswordForm):
    """
    SetPasswordForm + un campo de correo editable. Se usa en trial_exitoso para
    que el Administrador ponga su propia clave y, de paso, corrija el correo si
    al registrarse usó uno de relleno solo para pasar el formulario rápido.
    """
    email = forms.EmailField(label='Correo', required=True)

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields['email'].initial = user.email

    def save(self, commit=True):
        self.user.email = self.cleaned_data['email']
        return super().save(commit=commit)


def trial_exitoso(request):
    """
    Muestra las credenciales de los 3 usuarios creados tras el registro de Trial.
    El Administrador ya entró con sesión automática (ver solicitar_trial) y aquí
    puede reemplazar su contraseña generada al azar por una que él elija, y
    corregir su correo si el que puso al registrarse no era el real.
    """
    credenciales = request.session.get('trial_credenciales')
    if not credenciales:
        return redirect('core:solicitar_trial')

    password_configurada = request.session.get('trial_password_configurada', False)
    puede_configurar = (
        request.user.is_authenticated
        and request.user.username == credenciales['admin']['username']
        and not password_configurada
    )

    set_password_form = None
    if puede_configurar:
        if request.method == 'POST':
            set_password_form = ConfigurarAccesoTrialForm(request.user, request.POST)
            if set_password_form.is_valid():
                correo_anterior = request.user.email
                usuario = set_password_form.save()
                update_session_auth_hash(request, usuario)
                request.session['trial_password_configurada'] = True

                correo_cambio = usuario.email != correo_anterior
                if correo_cambio and usuario.empresa:
                    usuario.empresa.email = usuario.email
                    usuario.empresa.save(update_fields=['email'])

                credenciales['admin']['email'] = usuario.email
                request.session['trial_credenciales'] = credenciales
                request.session.modified = True

                if correo_cambio and usuario.empresa:
                    _reenviar_credenciales_trial(usuario.empresa, usuario, credenciales)

                messages.success(
                    request,
                    'Listo, tu contraseña quedó configurada. Para volver a entrar usa tu '
                    'correo y esta clave.'
                )
                return redirect('core:dashboard')
        else:
            set_password_form = ConfigurarAccesoTrialForm(request.user)

    return render(request, 'registration/trial_exitoso.html', {
        'credenciales': credenciales,
        'set_password_form': set_password_form,
        'password_configurada': password_configurada,
    })


def _reenviar_credenciales_trial(empresa, admin_user, credenciales):
    """
    Si el Administrador corrigió su correo en trial_exitoso, reenvía las
    credenciales de Gerencia y Técnico (y la clave temporal original del
    Administrador, por si aún no configuró la propia) al correo correcto —
    las que se mandaron al momento del registro quedaron en un correo que
    puede que nunca haya sido suyo.
    """
    try:
        gerente_user = CustomUser.objects.get(empresa=empresa, rol_usuario='GERENCIA')
        tecnico_user = CustomUser.objects.get(empresa=empresa, rol_usuario='TECNICO')
    except CustomUser.DoesNotExist:
        return

    _enviar_email_bienvenida_trial(
        empresa, admin_user, gerente_user, tecnico_user,
        credenciales['admin']['password'],
        credenciales['gerente']['password'],
        credenciales['tecnico']['password'],
    )


def _enviar_email_bienvenida_trial(empresa, admin_user, gerente_user, tecnico_user,
                                    admin_password, gerente_password, tecnico_password):
    """
    Envía por correo las credenciales de los 3 usuarios del trial, como respaldo
    de la pantalla (que solo se muestra una vez). El Administrador ya quedó con
    sesión iniciada en la plataforma al momento del registro.
    """
    destinatario = empresa.email
    if not destinatario:
        return

    asunto = f"Tu Trial de SAM Metrología está listo — {empresa.nombre}"

    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">{_EMAIL_STYLE}</head>
<body><div class="wrap"><div class="card">
  <div class="hdr">
    <h1>SAM METROLOGÍA</h1>
    <p>Control Digital e Inteligencia Metrológica</p>
  </div>
  <div class="body">
    <span class="badge">✅ Trial de 30 días activo</span>
    <p>Cordial saludo, estimado(a) <strong>{empresa.nombre}</strong>:</p>
    <p>Tu cuenta de prueba ya está lista. Ya iniciamos sesión por ti con el usuario
       <strong>Administrador</strong> en esta misma solicitud — si sigues en esa
       pantalla, ya estás adentro de la plataforma.</p>
    <p>Guarda este correo: aquí quedan tus accesos por si necesitas volver a entrar
       más adelante.</p>
    <table class="det">
      <tr><td>Administrador — usuario</td><td>{admin_user.username}</td></tr>
      <tr><td>Administrador — clave temporal</td><td style="font-family:monospace">{admin_password}</td></tr>
      <tr><td>Gerencia — usuario</td><td>{gerente_user.username}</td></tr>
      <tr><td>Gerencia — clave</td><td style="font-family:monospace">{gerente_password}</td></tr>
      <tr><td>Técnico — usuario</td><td>{tecnico_user.username}</td></tr>
      <tr><td>Técnico — clave</td><td style="font-family:monospace">{tecnico_password}</td></tr>
    </table>
    <p><strong>Importante:</strong> si en tu primer ingreso configuraste tu propia
       contraseña para el Administrador, usa esa en vez de la clave temporal de
       arriba. Con el Administrador puedes entrar con tu correo
       (<strong>{admin_user.email}</strong>) o con el usuario, junto con tu clave.</p>
    <a href="https://app.sammetrologia.com" class="btn">Ir a la plataforma →</a>
    <p>Si tienes alguna duda no dudes en contactarnos.</p>
    <p>Atentamente,</p>
    <div class="sig-name">Equipo Comercial SAM Metrología</div>
    <div class="sig-info">
      SAM Metrología S.A.S<br>
      <a href="https://sammetrologia.com">sammetrologia.com</a><br>
      WhatsApp: +57 324 799 0534 &nbsp;|&nbsp; comercial@sammetrologia.com
    </div>
  </div>
  <div class="ftr"><strong>SAM Metrología | Gestión Metrológica 4.0</strong><br>
    Colombia — Soluciones Avanzadas en Medición</div>
</div></div></body></html>"""

    texto = (
        f"Hola {empresa.nombre},\n\n"
        f"Tu Trial de 30 días de SAM Metrología ya está activo. Ya iniciamos sesión "
        f"por ti con el usuario Administrador.\n\n"
        f"Guarda estos accesos por si necesitas volver a entrar:\n\n"
        f"  Administrador - usuario: {admin_user.username}\n"
        f"  Administrador - clave temporal: {admin_password}\n"
        f"  Gerencia - usuario: {gerente_user.username}\n"
        f"  Gerencia - clave: {gerente_password}\n"
        f"  Técnico - usuario: {tecnico_user.username}\n"
        f"  Técnico - clave: {tecnico_password}\n\n"
        f"Si configuraste tu propia clave al entrar, úsala en vez de la temporal. "
        f"Puedes entrar con tu correo ({admin_user.email}) o con el usuario.\n\n"
        f"Ingresa en: https://app.sammetrologia.com\n\n"
        f"SAM Metrología S.A.S — comercial@sammetrologia.com"
    )

    ok = _send_html_email(asunto, texto, html, [destinatario], from_label=SAM_FROM_LABEL)
    if ok:
        logger.info(f"Email de bienvenida de trial enviado a {destinatario} (empresa='{empresa.nombre}')")
    else:
        logger.error(f"No se pudo enviar el correo de bienvenida de trial a {destinatario}")
