# core/management/commands/crear_grupo_empresa.py
# Comando para crear un grupo con permisos completos para usuarios de empresa

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from core.models import Equipo, Calibracion, Mantenimiento, Comprobacion, Proveedor, Procedimiento


class Command(BaseCommand):
    help = 'Crea un grupo "Usuario Empresa" con permisos completos para revisar funcionalidades de empresa'

    def handle(self, *args, **options):
        # Crear o obtener el grupo
        grupo, created = Group.objects.get_or_create(name='Usuario Empresa')

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Grupo "{grupo.name}" creado exitosamente.')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Grupo "{grupo.name}" ya existe. Actualizando permisos...')
            )

        # Definir permisos necesarios por modelo
        permisos_config = {
            Equipo: ['view', 'add', 'change', 'delete', 'can_export_reports'],
            Calibracion: ['view', 'add', 'change', 'delete'],
            Mantenimiento: ['view', 'add', 'change', 'delete'],
            Comprobacion: ['view', 'add', 'change', 'delete'],
            Proveedor: ['view', 'add', 'change', 'delete'],
            Procedimiento: ['view', 'add', 'change', 'delete'],
        }

        permisos_agregados = 0

        for modelo, acciones in permisos_config.items():
            content_type = ContentType.objects.get_for_model(modelo)

            for accion in acciones:
                # Construir codename del permiso
                if accion.startswith('can_'):
                    codename = accion  # Permisos custom como can_export_reports
                else:
                    codename = f'{accion}_{modelo._meta.model_name}'

                try:
                    permiso = Permission.objects.get(
                        codename=codename,
                        content_type=content_type
                    )

                    # Agregar permiso al grupo si no lo tiene
                    if not grupo.permissions.filter(id=permiso.id).exists():
                        grupo.permissions.add(permiso)
                        permisos_agregados += 1
                        self.stdout.write(f'  [OK] Agregado: {modelo._meta.verbose_name} - {accion}')

                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'  [ERROR] Permiso no encontrado: {codename} para {modelo._meta.verbose_name}')
                    )

        # Agregar permisos adicionales específicos de la app
        permisos_adicionales = [
            # Permisos para vistas de empresa
            'view_empresa',
            'change_empresa',
            # Permisos para usuarios (solo view para ver compañeros)
            'view_customuser',
        ]

        for codename in permisos_adicionales:
            try:
                permiso = Permission.objects.get(codename=codename)
                if not grupo.permissions.filter(id=permiso.id).exists():
                    grupo.permissions.add(permiso)
                    permisos_agregados += 1
                    self.stdout.write(f'  [OK] Agregado permiso adicional: {codename}')
            except Permission.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'  [ERROR] Permiso adicional no encontrado: {codename}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\n[EXITO] Configuracion completada:')
        )
        self.stdout.write(f'   - Grupo: {grupo.name}')
        self.stdout.write(f'   - Permisos agregados: {permisos_agregados}')
        self.stdout.write(f'   - Total de permisos: {grupo.permissions.count()}')

        self.stdout.write(
            self.style.SUCCESS(f'\n[INSTRUCCIONES] Como usar:')
        )
        self.stdout.write('   1. Vaya al admin de Django (/admin/)')
        self.stdout.write('   2. Seleccione "Usuarios" (Custom Users)')
        self.stdout.write('   3. Edite el usuario deseado')
        self.stdout.write('   4. En "Grupos", seleccione "Usuario Empresa"')
        self.stdout.write('   5. Guarde los cambios')
        self.stdout.write('')
        self.stdout.write(
            self.style.WARNING('[IMPORTANTE] Este usuario podra:')
        )
        self.stdout.write('   - Ver, crear, editar y eliminar equipos')
        self.stdout.write('   - Gestionar calibraciones, mantenimientos y comprobaciones')
        self.stdout.write('   - Administrar proveedores y procedimientos')
        self.stdout.write('   - Descargar informes y reportes ZIP')
        self.stdout.write('   - Ver datos de su empresa unicamente')