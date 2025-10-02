from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from core.models import CustomUser

class Command(BaseCommand):
    help = 'Check user permissions for calibration management'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== CHECKING USER PERMISSIONS ==='))

        # Check permissions for users CERTI and ALMA
        for username in ['CERTI', 'ALMA']:
            try:
                user = CustomUser.objects.get(username=username)
                self.stdout.write(f"\n--- Usuario: {username} ---")
                self.stdout.write(f"Superusuario: {user.is_superuser}")
                self.stdout.write(f"Staff: {user.is_staff}")
                self.stdout.write(f"Activo: {user.is_active}")
                self.stdout.write(f"Rol: {getattr(user, 'rol_usuario', 'No definido')}")

                # Check calibration permissions
                calibration_perms = [
                    'core.add_calibracion',
                    'core.change_calibracion',
                    'core.delete_calibracion',
                    'core.view_calibracion',
                ]

                self.stdout.write("\nPermisos de calibración:")
                for perm in calibration_perms:
                    has_perm = user.has_perm(perm)
                    status = "SI" if has_perm else "NO"
                    self.stdout.write(f"  {perm}: {status}")

                # Check groups
                groups = user.groups.all()
                self.stdout.write(f"\nGrupos: {[g.name for g in groups] if groups.exists() else 'Ninguno'}")

                # Check user permissions
                user_perms = user.user_permissions.all()
                self.stdout.write(f"Permisos individuales: {user_perms.count()}")
                for perm in user_perms:
                    self.stdout.write(f"  - {perm.content_type.app_label}.{perm.codename}")

            except CustomUser.DoesNotExist:
                self.stdout.write(f"Usuario {username} no encontrado")

        # List all available calibration permissions
        self.stdout.write(self.style.WARNING('\n=== PERMISOS DISPONIBLES PARA CALIBRACION ==='))
        cal_perms = Permission.objects.filter(content_type__model='calibracion')
        for perm in cal_perms:
            self.stdout.write(f"- {perm.content_type.app_label}.{perm.codename}: {perm.name}")

        self.stdout.write(self.style.SUCCESS('\n=== CHECK COMPLETED ==='))