# Comando para crear datos de prueba nuevos con archivos funcionando
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from core.models import *
from django.core.files.base import ContentFile
from django.utils import timezone
import logging
from datetime import datetime, timedelta

User = get_user_model()
logger = logging.getLogger('core')

class Command(BaseCommand):
    help = 'Crea datos de prueba nuevos con archivos funcionando correctamente'

    def add_arguments(self, parser):
        parser.add_argument(
            '--with-files',
            action='store_true',
            help='Crear archivos de prueba (logos, documentos)',
        )

    def handle(self, *args, **options):
        with_files = options['with_files']

        self.stdout.write(self.style.SUCCESS('Creando datos de prueba nuevos...'))

        # 1. Crear grupos de permisos
        self.stdout.write('Creando grupos de permisos...')

        grupo_admin_empresa, created = Group.objects.get_or_create(
            name='Administrador Empresa',
            defaults={'name': 'Administrador Empresa'}
        )

        grupo_usuario_empresa, created = Group.objects.get_or_create(
            name='Usuario Empresa',
            defaults={'name': 'Usuario Empresa'}
        )

        self.stdout.write('   Grupos de permisos creados')

        # 2. Crear empresas de prueba
        self.stdout.write('Creando empresas de prueba...')

        empresas_data = [
            {
                'nombre': 'MetroTech Solutions',
                'nit': '900123456-7',
                'direccion': 'Calle 100 #15-20, Bogotá',
                'telefono': '+57 1 234-5678',
                'email': 'info@metrotech.com',
                'limite_equipos_empresa': 50,
                'limite_almacenamiento_mb': 2000,
                'duracion_suscripcion_meses': 12,
            },
            {
                'nombre': 'Precision Instruments Corp',
                'nit': '800987654-3',
                'direccion': 'Carrera 50 #25-30, Medellín',
                'telefono': '+57 4 987-6543',
                'email': 'contacto@precision.com',
                'limite_equipos_empresa': 25,
                'limite_almacenamiento_mb': 1500,
                'duracion_suscripcion_meses': 6,
            },
            {
                'nombre': 'Industrial Calibration SA',
                'nit': '700555666-1',
                'direccion': 'Avenida 3N #25-40, Cali',
                'telefono': '+57 2 555-6666',
                'email': 'admin@induscal.com',
                'limite_equipos_empresa': 75,
                'limite_almacenamiento_mb': 3000,
                'duracion_suscripcion_meses': 24,
            }
        ]

        empresas_creadas = []
        for empresa_data in empresas_data:
            empresa, created = Empresa.objects.get_or_create(
                nit=empresa_data['nit'],
                defaults={
                    **empresa_data,
                    'fecha_inicio_plan': timezone.now().date(),
                    'estado_suscripcion': 'activa',
                    'acceso_manual_activo': True
                }
            )

            # Crear logo de prueba si se especifica
            if with_files:
                # Crear un archivo de imagen simple (1x1 pixel PNG)
                png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
                logo_file = ContentFile(png_data, name=f'logo_{empresa.nombre.lower().replace(" ", "_")}.png')
                empresa.logo_empresa = logo_file
                empresa.save()

            empresas_creadas.append(empresa)

        self.stdout.write(f'   {len(empresas_creadas)} empresas creadas')

        # 3. Crear usuarios de prueba
        self.stdout.write('Creando usuarios de prueba...')

        usuarios_data = [
            {
                'username': 'admin_metrotech',
                'email': 'admin@metrotech.com',
                'first_name': 'Carlos',
                'last_name': 'Administrador',
                'empresa': empresas_creadas[0],
                'grupo': grupo_admin_empresa,
                'is_staff': True
            },
            {
                'username': 'usuario_metrotech',
                'email': 'usuario@metrotech.com',
                'first_name': 'Ana',
                'last_name': 'Técnica',
                'empresa': empresas_creadas[0],
                'grupo': grupo_usuario_empresa,
                'is_staff': False
            },
            {
                'username': 'admin_precision',
                'email': 'admin@precision.com',
                'first_name': 'Luis',
                'last_name': 'Gerente',
                'empresa': empresas_creadas[1],
                'grupo': grupo_admin_empresa,
                'is_staff': True
            },
            {
                'username': 'admin_induscal',
                'email': 'admin@induscal.com',
                'first_name': 'María',
                'last_name': 'Directora',
                'empresa': empresas_creadas[2],
                'grupo': grupo_admin_empresa,
                'is_staff': True
            }
        ]

        usuarios_creados = []
        for usuario_data in usuarios_data:
            grupo = usuario_data.pop('grupo')
            empresa = usuario_data.pop('empresa')

            usuario, created = User.objects.get_or_create(
                username=usuario_data['username'],
                defaults={
                    **usuario_data,
                    'password': 'test123456'  # Contraseña de prueba
                }
            )

            if created:
                usuario.set_password('test123456')

            usuario.empresa = empresa
            usuario.groups.clear()
            usuario.groups.add(grupo)
            usuario.save()

            usuarios_creados.append(usuario)

        self.stdout.write(f'   {len(usuarios_creados)} usuarios creados')

        # 4. Crear proveedores de prueba
        self.stdout.write('Creando proveedores de prueba...')

        proveedores_data = [
            {
                'nombre_empresa': 'Fluke Corporation',
                'tipo_servicio': 'Calibración',
                'nombre_contacto': 'John Smith',
                'numero_contacto': '+1 425-347-6100',
                'correo_electronico': 'info@fluke.com',
                'pagina_web': 'https://www.fluke.com',
                'alcance': 'Instrumentos de medición eléctrica',
                'servicio_prestado': 'Calibración de multímetros y equipos eléctricos'
            },
            {
                'nombre_empresa': 'Keysight Technologies',
                'tipo_servicio': 'Calibración',
                'nombre_contacto': 'Maria Garcia',
                'numero_contacto': '+1 707-577-2663',
                'correo_electronico': 'contact@keysight.com',
                'pagina_web': 'https://www.keysight.com',
                'alcance': 'Equipos de medición de alta frecuencia',
                'servicio_prestado': 'Calibración de osciloscopios y analizadores'
            },
            {
                'nombre_empresa': 'Tektronix Inc',
                'tipo_servicio': 'Mantenimiento',
                'nombre_contacto': 'Carlos Rodriguez',
                'numero_contacto': '+1 503-627-7111',
                'correo_electronico': 'support@tek.com',
                'pagina_web': 'https://www.tek.com',
                'alcance': 'Equipos de medición electrónica',
                'servicio_prestado': 'Mantenimiento preventivo y correctivo'
            }
        ]

        proveedores_creados = []
        for i, proveedor_data in enumerate(proveedores_data):
            empresa = empresas_creadas[i % len(empresas_creadas)]
            proveedor_data['empresa'] = empresa

            proveedor, created = Proveedor.objects.get_or_create(
                nombre_empresa=proveedor_data['nombre_empresa'],
                empresa=empresa,
                defaults=proveedor_data
            )
            proveedores_creados.append(proveedor)

        self.stdout.write(f'   {len(proveedores_creados)} proveedores creados')

        # 5. Crear equipos de prueba
        self.stdout.write('Creando equipos de prueba...')

        tipos_equipo = ['Multímetro', 'Osciloscopio', 'Generador de funciones', 'Analizador de espectro', 'Calibrador']

        equipos_creados = []
        for i, empresa in enumerate(empresas_creadas):
            for j in range(3):  # 3 equipos por empresa
                equipo_data = {
                    'codigo_interno': f'EQ-{empresa.nombre[:3].upper()}-{j+1:03d}',
                    'nombre': f'{tipos_equipo[j % len(tipos_equipo)]} {j+1}',
                    'tipo_equipo': 'Equipo de Medición',
                    'marca': ['Fluke', 'Keysight', 'Tektronix'][j % 3],
                    'modelo': f'Model-{1000 + j}',
                    'numero_serie': f'SN{empresa.id}{j:04d}',
                    'ubicacion': f'Laboratorio {j+1}',
                    'estado': 'Activo',
                    'empresa': empresa,
                    'fecha_adquisicion': timezone.now().date() - timedelta(days=365),
                    'rango_medida': '0-100V',
                    'resolucion': '0.1V',
                    'error_maximo_permisible': '±0.5%',
                    'responsable': f'Técnico {j+1}',
                }

                equipo = Equipo.objects.create(**equipo_data)

                # Crear imagen de equipo de prueba si se especifica
                if with_files:
                    imagen_file = ContentFile(png_data, name=f'equipo_{equipo.codigo_interno.lower()}.png')
                    equipo.imagen_equipo = imagen_file
                    equipo.save()

                equipos_creados.append(equipo)

        self.stdout.write(f'   {len(equipos_creados)} equipos creados')

        # Resumen final
        self.stdout.write(self.style.SUCCESS('\nDATOS DE PRUEBA CREADOS EXITOSAMENTE'))
        self.stdout.write(f'Resumen:')
        self.stdout.write(f'   • {len(empresas_creadas)} empresas')
        self.stdout.write(f'   • {len(usuarios_creados)} usuarios')
        self.stdout.write(f'   • {len(proveedores_creados)} proveedores')
        self.stdout.write(f'   • {len(equipos_creados)} equipos')

        if with_files:
            self.stdout.write(f'   • Archivos de prueba incluidos (logos e imágenes)')
        else:
            self.stdout.write(f'   • Sin archivos - ejecuta con --with-files para incluir logos')

        self.stdout.write(f'\nUsuarios de prueba (contraseña: test123456):')
        for usuario in usuarios_creados:
            self.stdout.write(f'   • {usuario.username} - {usuario.empresa.nombre}')

        self.stdout.write(f'\nTodo listo para hacer pruebas!')