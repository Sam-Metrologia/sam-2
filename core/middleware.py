# core/middleware.py
# Middleware para rate limiting y seguridad

import secrets
import time
import hashlib
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger('core.security')

class RateLimitMiddleware(MiddlewareMixin):
    """
    Middleware para implementar rate limiting basado en configuración.
    Protege contra ataques de fuerza bruta y abuso de recursos.
    """

    def process_request(self, request):
        # Solo aplicar rate limiting si no estamos en DEBUG
        if getattr(settings, 'DEBUG', False):
            return None

        # Obtener configuración de rate limiting
        rate_config = getattr(settings, 'RATE_LIMIT_CONFIG', {})

        # Obtener IP del cliente (considerando proxies)
        client_ip = self.get_client_ip(request)

        # Aplicar diferentes límites según la ruta
        # Para login: solo VERIFICAR el límite aquí; el contador se incrementa
        # en process_response solo si el intento FALLÓ (evita bloquear re-logins legítimos)
        if request.path.startswith('/core/login/') and request.method == 'POST':
            config = rate_config.get('LOGIN_ATTEMPTS', {'limit': 5, 'period': 300})
            return self.check_rate_limit_only(request, client_ip, 'LOGIN_ATTEMPTS', config)
        elif request.method == 'POST' and 'upload' in request.path.lower():
            return self.check_rate_limit(
                request, client_ip, 'UPLOAD_FILES',
                rate_config.get('UPLOAD_FILES', {'limit': 10, 'period': 300})
            )
        elif request.path.startswith('/api/'):
            return self.check_rate_limit(
                request, client_ip, 'API_CALLS',
                rate_config.get('API_CALLS', {'limit': 100, 'period': 3600})
            )

        return None

    def process_response(self, request, response):
        # Solo en producción
        if getattr(settings, 'DEBUG', False):
            return response

        # Incrementar contador de intentos fallidos de login
        # Un login fallido retorna 200 (muestra el formulario con error)
        # Un login exitoso retorna 302 (redirect)
        if (request.path.startswith('/core/login/')
                and request.method == 'POST'
                and response.status_code == 200):
            rate_config = getattr(settings, 'RATE_LIMIT_CONFIG', {})
            config = rate_config.get('LOGIN_ATTEMPTS', {'limit': 5, 'period': 300})
            client_ip = self.get_client_ip(request)
            self._increment_rate_limit(client_ip, 'LOGIN_ATTEMPTS', config.get('period', 300))

        return response

    def get_client_ip(self, request):
        """Obtiene la IP real del cliente considerando proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def check_rate_limit(self, request, client_ip, limit_type, config):
        """Verifica el límite de rate E incrementa el contador (para APIs/uploads)."""
        limit = config.get('limit', 10)
        period = config.get('period', 300)  # 5 minutos por defecto

        # Crear clave de cache única
        cache_key = f"rate_limit_{limit_type}_{client_ip}"

        try:
            # Obtener contador actual
            current_count = cache.get(cache_key, 0)

            if current_count >= limit:
                self._log_rate_limit_exceeded(request, client_ip, limit_type, current_count, limit)
                return self._build_rate_limit_response(request, period)

            # Incrementar contador
            cache.set(cache_key, current_count + 1, period)

        except Exception as e:
            # Si hay error con el cache, permitir la request pero loguear
            logger.error(f"Error in rate limiting: {e}")

        return None

    def check_rate_limit_only(self, request, client_ip, limit_type, config):
        """Solo verifica si se excedió el límite; NO incrementa el contador.
        Usar para login: el contador se incrementa en process_response solo si falló."""
        limit = config.get('limit', 10)
        period = config.get('period', 300)

        cache_key = f"rate_limit_{limit_type}_{client_ip}"

        try:
            current_count = cache.get(cache_key, 0)
            if current_count >= limit:
                self._log_rate_limit_exceeded(request, client_ip, limit_type, current_count, limit)
                return self._build_rate_limit_response(request, period)
        except Exception as e:
            logger.error(f"Error in rate limiting check: {e}")

        return None

    def _increment_rate_limit(self, client_ip, limit_type, period):
        """Incrementa el contador de rate limit para una IP."""
        cache_key = f"rate_limit_{limit_type}_{client_ip}"
        try:
            current_count = cache.get(cache_key, 0)
            cache.set(cache_key, current_count + 1, period)
        except Exception as e:
            logger.error(f"Error incrementing rate limit: {e}")

    def _log_rate_limit_exceeded(self, request, client_ip, limit_type, current_count, limit):
        logger.warning(
            f"Rate limit exceeded for {limit_type}",
            extra={
                'client_ip': client_ip,
                'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
                'path': request.path,
                'limit_type': limit_type,
                'current_count': current_count,
                'limit': limit
            }
        )

    def _build_rate_limit_response(self, request, period):
        if request.path.startswith('/api/') or request.headers.get('Accept', '').startswith('application/json'):
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'detail': f'Too many requests. Try again in {period} seconds.'
            }, status=429)
        else:
            response = HttpResponse(
                f"Too many requests. Please try again in {period} seconds.",
                status=429
            )
            response['Retry-After'] = str(period)
            return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware para añadir headers de seguridad adicionales.
    """

    def process_response(self, request, response):
        # Solo aplicar en producción
        if not getattr(settings, 'DEBUG', False):
            # Headers de seguridad adicionales
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['X-XSS-Protection'] = '1; mode=block'
            response['Referrer-Policy'] = 'same-origin'

            # Cache control para archivos estáticos
            if request.path.startswith('/static/') or request.path.startswith('/media/'):
                response['Cache-Control'] = 'public, max-age=31536000'  # 1 año
            else:
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate'

        return response


class FileUploadSecurityMiddleware(MiddlewareMixin):
    """
    Middleware para verificar uploads de archivos maliciosos.
    """

    DANGEROUS_EXTENSIONS = [
        '.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.vbs', '.js',
        '.jar', '.sh', '.py', '.php', '.asp', '.aspx', '.jsp'
    ]

    def process_request(self, request):
        if request.method == 'POST' and request.FILES:
            for file_key, uploaded_file in request.FILES.items():
                # Verificar extensión peligrosa
                file_name = uploaded_file.name.lower()
                if any(file_name.endswith(ext) for ext in self.DANGEROUS_EXTENSIONS):
                    logger.error(
                        f"Attempted upload of dangerous file: {uploaded_file.name}",
                        extra={
                            'client_ip': self.get_client_ip(request),
                            'user': getattr(request, 'user', 'Anonymous'),
                            'file_name': uploaded_file.name,
                            'file_size': uploaded_file.size
                        }
                    )

                    if request.headers.get('Accept', '').startswith('application/json'):
                        return JsonResponse({
                            'error': 'File type not allowed',
                            'detail': 'The uploaded file type is not permitted for security reasons.'
                        }, status=400)
                    else:
                        return HttpResponse(
                            "File type not allowed for security reasons.",
                            status=400
                        )

        return None

    def get_client_ip(self, request):
        """Obtiene la IP real del cliente."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class TerminosCondicionesMiddleware(MiddlewareMixin):
    """
    Middleware que verifica si el usuario ha aceptado los términos y condiciones actuales.
    Si no los ha aceptado, redirige a la página de aceptación.

    Implementa el requisito legal del contrato (Cláusula 11.1) de que todos los usuarios
    deben aceptar los términos antes de usar la plataforma.
    """

    # Rutas que NO requieren verificación de términos
    RUTAS_EXCLUIDAS = [
        '/core/login/',
        '/core/logout/',
        '/core/terminos-condiciones/',
        '/core/solicitar-trial/',
        '/core/trial-exitoso/',
        '/core/onboarding/',
        '/login/',
        '/logout/',
        '/static/',
        '/media/',
        '/admin/login/',
        '/admin/logout/',
        '/admin/',
    ]

    def process_request(self, request):
        """
        Verifica en cada request si el usuario debe aceptar términos.
        """
        # Si el usuario no está autenticado, no verificar
        if not request.user.is_authenticated:
            return None

        # Verificar si la ruta actual está excluida
        for ruta_excluida in self.RUTAS_EXCLUIDAS:
            if request.path.startswith(ruta_excluida):
                return None

        # Importar modelos aquí para evitar circular imports
        from core.models import AceptacionTerminos, TerminosYCondiciones

        # Verificar si hay términos activos
        terminos_activos = TerminosYCondiciones.get_terminos_activos()
        if not terminos_activos:
            # Si no hay términos configurados, no forzar aceptación
            # (útil durante desarrollo o si el admin aún no configuró términos)
            return None

        # Verificar si el usuario ya aceptó los términos actuales
        if AceptacionTerminos.usuario_acepto_terminos_actuales(request.user):
            # Usuario ya aceptó, permitir acceso
            return None

        # Usuario NO ha aceptado términos actuales
        # Redirigir a página de aceptación (excepto si ya está ahí)
        from django.shortcuts import redirect

        if not request.path.startswith('/core/terminos-condiciones/'):
            logger.info(
                f'Usuario {request.user.username} redirigido a términos. '
                f'Intentaba acceder: {request.path}'
            )
            return redirect('core:aceptar_terminos')

        return None


class SessionActivityMiddleware(MiddlewareMixin):
    """
    Middleware que extiende la sesión automáticamente si hay actividad del usuario.

    - Detecta requests del usuario (GET, POST)
    - Actualiza 'last_activity' en la sesión
    - Extiende la sesión si hay actividad reciente
    - Sesión expira después de 30 minutos de INACTIVIDAD real
    """

    # Tiempo de inactividad antes de cerrar sesión (en segundos)
    INACTIVE_TIMEOUT = 1800  # 30 minutos

    def process_request(self, request):
        if request.user.is_authenticated:
            from django.utils import timezone
            from datetime import timedelta

            now = timezone.now()

            # Obtener última actividad
            last_activity = request.session.get('last_activity')

            if last_activity:
                try:
                    # Convertir string ISO a datetime
                    last_activity_time = timezone.datetime.fromisoformat(last_activity)
                    inactive_time = now - last_activity_time

                    # Si ha estado inactivo más de 30 minutos, dejar que expire
                    if inactive_time.total_seconds() > self.INACTIVE_TIMEOUT:
                        # No hacer nada, dejar que Django maneje la expiración
                        logger.info(
                            f"Sesión inactiva para usuario {request.user.username}. "
                            f"Tiempo inactivo: {inactive_time}"
                        )
                    else:
                        # Hay actividad reciente, extender sesión
                        request.session.set_expiry(self.INACTIVE_TIMEOUT)
                except (ValueError, TypeError) as e:
                    # Error al parsear fecha, establecer nueva
                    logger.warning(f"Error parsing last_activity: {e}")

            # Actualizar última actividad
            request.session['last_activity'] = now.isoformat()

        return None

class CSPNonceMiddleware:
    """Genera un nonce por request para CSP. Añade {{{{ csp_nonce }}}} a scripts inline.
    Una vez todos los templates migren a nonce, quitar 'unsafe-inline' de settings.py CSP.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(16)
        response = self.get_response(request)
        existing_csp = response.get("Content-Security-Policy", "")
        if existing_csp and "script-src" in existing_csp:
            response["Content-Security-Policy"] = existing_csp.replace(
                "'unsafe-inline'",
                f"'nonce-{request.csp_nonce}' 'unsafe-inline'",
            )
        return response
