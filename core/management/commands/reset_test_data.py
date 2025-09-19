# Comando para limpiar completamente datos de prueba y empezar fresh
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from core.models import *
from django.core.files.storage import default_storage
import logging
import os

User = get_user_model()
logger = logging.getLogger('core')

class Command(BaseCommand):
    help = 'Limpia todos los datos de prueba para empezar fresh (SOLO USAR EN DESARROLLO/TESTING)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirmar que quieres eliminar TODOS los datos (requerido)',
        )
        parser.add_argument(
            '--keep-superuser',
            action='store_true',
            help='Mantener el superusuario principal',
        )
        parser.add_argument(
            '--clean-s3',
            action='store_true',
            help='También limpiar archivos de S3',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.ERROR('PELIGRO: Este comando eliminará TODOS los datos.')
            )
            self.stdout.write('Para confirmar, ejecuta: python manage.py reset_test_data --confirm')
            return

        self.stdout.write(self.style.WARNING('Iniciando limpieza completa de datos...'))

        # 1. Eliminar datos relacionados con equipos
        self.stdout.write('Eliminando equipos y datos relacionados...')

        count_calibraciones = Calibracion.objects.count()
        count_mantenimientos = Mantenimiento.objects.count()
        count_comprobaciones = Comprobacion.objects.count()
        count_bajas = BajaEquipo.objects.count()
        count_equipos = Equipo.objects.count()

        Calibracion.objects.all().delete()
        Mantenimiento.objects.all().delete()
        Comprobacion.objects.all().delete()
        BajaEquipo.objects.all().delete()
        Equipo.objects.all().delete()

        self.stdout.write(f'   {count_calibraciones} calibraciones eliminadas')
        self.stdout.write(f'   {count_mantenimientos} mantenimientos eliminados')
        self.stdout.write(f'   {count_comprobaciones} comprobaciones eliminadas')
        self.stdout.write(f'   {count_bajas} bajas de equipo eliminadas')
        self.stdout.write(f'   {count_equipos} equipos eliminados')

        # 2. Eliminar procedimientos y proveedores
        self.stdout.write('Eliminando procedimientos y proveedores...')

        count_procedimientos = Procedimiento.objects.count()
        count_proveedores = Proveedor.objects.count()

        Procedimiento.objects.all().delete()
        Proveedor.objects.all().delete()

        self.stdout.write(f'   {count_procedimientos} procedimientos eliminados')
        self.stdout.write(f'   {count_proveedores} proveedores eliminados')

        # 3. Eliminar empresas (pero conservar usuarios si se especifica)
        self.stdout.write('Eliminando empresas...')

        count_empresas = Empresa.objects.count()
        Empresa.objects.all().delete()

        self.stdout.write(f'   {count_empresas} empresas eliminadas')

        # 4. Limpiar usuarios (excepto superuser si se especifica)
        self.stdout.write('Limpiando usuarios...')

        if options['keep_superuser']:
            # Mantener solo superusuarios
            usuarios_a_eliminar = User.objects.filter(is_superuser=False)
            count_usuarios = usuarios_a_eliminar.count()
            usuarios_a_eliminar.delete()
            self.stdout.write(f'   {count_usuarios} usuarios eliminados (superusuarios conservados)')
        else:
            count_usuarios = User.objects.count()
            User.objects.all().delete()
            self.stdout.write(f'   {count_usuarios} usuarios eliminados (incluye superusuarios)')

        # 5. Limpiar grupos personalizados (conservar los básicos de Django)
        self.stdout.write('Limpiando grupos personalizados...')

        # Conservar grupos básicos de Django pero eliminar los personalizados
        grupos_django_basicos = ['Administradores', 'Staff']
        grupos_personalizados = Group.objects.exclude(name__in=grupos_django_basicos)
        count_grupos = grupos_personalizados.count()
        grupos_personalizados.delete()

        self.stdout.write(f'   {count_grupos} grupos personalizados eliminados')

        # 6. Limpiar archivos de S3 si se especifica
        if options['clean_s3']:
            self.stdout.write('Limpiando archivos de S3...')
            try:
                import boto3

                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                    region_name=os.environ.get('AWS_S3_REGION_NAME', 'us-east-2')
                )

                bucket_name = os.environ.get('AWS_STORAGE_BUCKET_NAME')

                # Listar y eliminar objetos en el bucket (solo en la carpeta media/)
                response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix='media/')

                if 'Contents' in response:
                    objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]

                    if objects_to_delete:
                        s3_client.delete_objects(
                            Bucket=bucket_name,
                            Delete={'Objects': objects_to_delete}
                        )
                        self.stdout.write(f'   {len(objects_to_delete)} archivos eliminados de S3')
                    else:
                        self.stdout.write('   No hay archivos para eliminar en S3')
                else:
                    self.stdout.write('   No hay archivos para eliminar en S3')

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'   Error limpiando S3: {str(e)}')
                )

        # Resumen final
        self.stdout.write(self.style.SUCCESS('\nLIMPIEZA COMPLETA TERMINADA'))
        self.stdout.write(self.style.SUCCESS('Base de datos limpia y lista para datos nuevos'))

        if options['keep_superuser']:
            self.stdout.write(self.style.WARNING('Superusuarios conservados - puedes hacer login normalmente'))
        else:
            self.stdout.write(self.style.WARNING('Todos los usuarios eliminados - necesitarás crear un nuevo superusuario'))
            self.stdout.write('   Ejecuta: python manage.py createsuperuser')

        self.stdout.write('\nSIGUIENTE PASO:')
        self.stdout.write('   Ahora puedes crear empresas, usuarios y equipos nuevos')
        self.stdout.write('   Todos los archivos se subirán correctamente a S3')