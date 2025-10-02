# core/middleware.py
# Middleware para rastrear actividad de usuarios y seguridad

from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden
from django.core.exceptions import SuspiciousOperation
import time

User = get_user_model()


class UserActivityMiddleware:
    """
    Middleware para rastrear la última actividad de usuarios autenticados.
    Actualiza la información en cache para optimizar performance.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Solo rastrear usuarios autenticados
        if request.user.is_authenticated:
            self.update_user_activity(request.user)

        return response

    def update_user_activity(self, user):
        """
        Actualiza la última actividad del usuario en cache.
        """
        now = timezone.now()

        # Actualizar en cache (duración: 2 horas)
        cache_key = f'user_activity_{user.id}'
        cache.set(cache_key, {
            'user_id': user.id,
            'username': user.username,
            'last_activity': now.isoformat(),
            'timestamp': now.timestamp()
        }, 7200)  # 2 horas

        # También mantener una lista de usuarios activos en los últimos 15 minutos
        active_users_key = 'active_users_15min'
        active_users = cache.get(active_users_key, {})

        # Limpiar usuarios inactivos (más de 15 minutos)
        cutoff_time = now.timestamp() - 900  # 15 minutos
        active_users = {
            uid: data for uid, data in active_users.items()
            if data.get('timestamp', 0) > cutoff_time
        }

        # Agregar usuario actual
        active_users[str(user.id)] = {
            'user_id': user.id,
            'username': user.username,
            'last_activity': now.isoformat(),
            'timestamp': now.timestamp()
        }

        # Guardar lista actualizada
        cache.set(active_users_key, active_users, 900)  # 15 minutos


class RateLimitMiddleware:
    """
    Middleware básico para rate limiting.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Rate limiting básico por IP
        ip = self.get_client_ip(request)
        cache_key = f'rate_limit_{ip}'

        current_requests = cache.get(cache_key, 0)
        if current_requests > 100:  # 100 requests per minute
            return HttpResponseForbidden("Rate limit exceeded")

        cache.set(cache_key, current_requests + 1, 60)  # 1 minute

        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityHeadersMiddleware:
    """
    Middleware para agregar headers de seguridad adicionales.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Headers de seguridad adicionales
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        return response


class FileUploadSecurityMiddleware:
    """
    Middleware para seguridad en uploads de archivos.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Validación básica de uploads
        if request.method == 'POST' and request.FILES:
            for file_field in request.FILES:
                uploaded_file = request.FILES[file_field]

                # Validar tamaño máximo (configurado en settings)
                max_size = 10 * 1024 * 1024  # 10MB
                if uploaded_file.size > max_size:
                    raise SuspiciousOperation("File too large")

                # Validar tipos de archivo permitidos
                allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf', '.xlsx', '.docx']
                if not any(uploaded_file.name.lower().endswith(ext) for ext in allowed_extensions):
                    raise SuspiciousOperation("File type not allowed")

        response = self.get_response(request)
        return response