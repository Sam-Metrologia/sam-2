import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from core.models import TerminosYCondiciones

t = TerminosYCondiciones.objects.first()

with open('temp_contrato.html', 'w', encoding='utf-8') as f:
    f.write(t.contenido_html)

print('Contenido exportado a temp_contrato.html')
print(f'Longitud: {len(t.contenido_html)} caracteres')
