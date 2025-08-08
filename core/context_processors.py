# core/context_processors.py

from django.db.models import Count
from django.contrib.auth.models import AnonymousUser
from .models import Equipo, Mantenimiento

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