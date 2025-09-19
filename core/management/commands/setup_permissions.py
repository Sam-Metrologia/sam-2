# core/management/commands/setup_permissions.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from core.models import CustomUser


class Command(BaseCommand):
    help = 'Crea los permisos necesarios para el sistema'

    def handle(self, *args, **options):
        """
        Crea los permisos personalizados necesarios para el sistema.
        """
        try:
            # Obtener el ContentType para el modelo core
            content_type = ContentType.objects.get_or_create(
                app_label='core',
                model='customuser'
            )[0]

            # Crear el permiso de exportar informes
            permission, created = Permission.objects.get_or_create(
                codename='can_export_reports',
                name='Can export reports',
                content_type=content_type,
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Permiso "can_export_reports" creado exitosamente.')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Permiso "can_export_reports" ya existe.')
                )

            # Verificar que los superusuarios tengan el permiso
            superusers = CustomUser.objects.filter(is_superuser=True)
            for user in superusers:
                if not user.has_perm('core.can_export_reports'):
                    user.user_permissions.add(permission)
                    self.stdout.write(
                        self.style.SUCCESS(f'Permiso otorgado al superusuario: {user.username}')
                    )

            self.stdout.write(
                self.style.SUCCESS('Setup de permisos completado exitosamente.')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error durante setup de permisos: {str(e)}')
            )
            raise