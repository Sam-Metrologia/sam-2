# core/context_processors.py

from django.db.models import Count
from django.contrib.auth.models import AnonymousUser

# Importa los modelos necesarios
# Asegúrate de que los modelos Equipo y Mantenimiento existen en core/models.py
from .models import Equipo, Mantenimiento

# Este es un procesador de contexto para agregar datos de la empresa
# que son accesibles en todas las plantillas.
def company_data(request):
    """
    Agrega datos de la empresa al contexto de la plantilla.
    Por ejemplo, el nombre de la empresa.
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
        # Si el usuario no está autenticado, no hay mensajes no leídos.
        return {
            'unread_messages_count': 0
        }

    # Aquí iría la lógica real para contar los mensajes no leídos.
    # Por ahora, devolvemos 0 para evitar errores si no está implementado.
    # Por ejemplo, podrías usar algo como esto si tuvieras un modelo de Mensaje:
    # count = Mensaje.objects.filter(destinatario=request.user, leido=False).count()
    
    return {
        'unread_messages_count': 0
    }
