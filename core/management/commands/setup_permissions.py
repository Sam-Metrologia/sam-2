# core/management/commands/setup_permissions.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from core.models import CustomUser


class Command(BaseCommand):
    help = 'Sincroniza permisos Django de todos los usuarios según su rol_usuario'

    def handle(self, *args, **options):
        try:
            from core.views.registro import asignar_permisos_por_rol

            usuarios = CustomUser.objects.filter(is_superuser=False).select_related('empresa')
            total = usuarios.count()
            actualizados = 0

            self.stdout.write(f'Sincronizando permisos para {total} usuarios...')

            for user in usuarios:
                asignar_permisos_por_rol(user)
                cnt = user.user_permissions.count()
                self.stdout.write(
                    f'  {user.username} ({user.rol_usuario}) -> {cnt} permisos'
                )
                actualizados += 1

            self.stdout.write(
                self.style.SUCCESS(f'Listo. {actualizados}/{total} usuarios sincronizados.')
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            raise
