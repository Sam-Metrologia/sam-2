# core/middleware.py
# Middleware para rate limiting y seguridad

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
        if request.path.startswith('/login/'):
            return self.check_rate_limit(
                request, client_ip, 'LOGIN_ATTEMPTS',
                rate_config.get('LOGIN_ATTEMPTS', {'limit': 5, 'period': 300})
            )
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

    def get_client_ip(self, request):
        """Obtiene la IP real del cliente considerando proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def check_rate_limit(self, request, client_ip, limit_type, config):
        """Verifica si se ha excedido el límite de rate."""
        limit = config.get('limit', 10)
        period = config.get('period', 300)  # 5 minutos por defecto

        # Crear clave de cache única
        cache_key = f"rate_limit_{limit_type}_{client_ip}"

        try:
            # Obtener contador actual
            current_count = cache.get(cache_key, 0)

            if current_count >= limit:
                # Loguear intento de abuso
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

                # Retornar respuesta de rate limiting
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

            # Incrementar contador
            cache.set(cache_key, current_count + 1, period)

        except Exception as e:
            # Si hay error con el cache, permitir la request pero loguear
            logger.error(f"Error in rate limiting: {e}")

        return None


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