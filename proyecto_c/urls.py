# proyecto_c/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView # Importa RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('core/', include('core.urls')), # Incluye las URLs de la aplicación 'core'
    
    # Redirige la URL raíz '/' a '/core/'
    path('', RedirectView.as_view(url='/core/', permanent=True)), # ¡NUEVO!
]

# Configuración para servir archivos de medios durante el desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
