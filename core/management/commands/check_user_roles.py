from django.core.management.base import BaseCommand
from core.models import CustomUser

class Command(BaseCommand):
    help = 'Check user roles and access permissions for debugging'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Check specific username',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== USER ROLE DEBUGGING ==='))

        if options['username']:
            users = CustomUser.objects.filter(username=options['username'])
        else:
            users = CustomUser.objects.all()

        for user in users:
            self.stdout.write(f"\n--- Usuario: {user.username} (ID: {user.id}) ---")
            self.stdout.write(f"Nombre completo: {user.get_full_name()}")
            self.stdout.write(f"Email: {user.email}")
            self.stdout.write(f"Activo: {user.is_active}")
            self.stdout.write(f"Superusuario: {user.is_superuser}")
            self.stdout.write(f"Staff: {user.is_staff}")

            # Check rol_usuario field
            rol_usuario = getattr(user, 'rol_usuario', None)
            self.stdout.write(f"rol_usuario: {rol_usuario}")

            # Check empresa association
            if hasattr(user, 'empresa') and user.empresa:
                self.stdout.write(f"Empresa: {user.empresa.nombre} (ID: {user.empresa.id})")
            else:
                self.stdout.write("Empresa: No asignada")

            # Check if user should have gerencia access
            should_have_gerencia = rol_usuario == 'GERENCIA' or user.is_superuser
            self.stdout.write(f"Debería tener acceso gerencia: {should_have_gerencia}")

            self.stdout.write("-" * 40)

        # Check specific users mentioned
        self.stdout.write(self.style.WARNING('\n=== USUARIOS ESPECÍFICOS MENCIONADOS ==='))
        for username in ['CERTI', 'ALMA']:
            try:
                user = CustomUser.objects.get(username=username)
                self.stdout.write(f"\n{username} encontrado:")
                self.stdout.write(f"  - ID: {user.id}")
                self.stdout.write(f"  - rol_usuario: {getattr(user, 'rol_usuario', 'No definido')}")
                self.stdout.write(f"  - is_superuser: {user.is_superuser}")
                self.stdout.write(f"  - empresa: {user.empresa.nombre if user.empresa else 'Sin empresa'}")
            except CustomUser.DoesNotExist:
                self.stdout.write(f"{username}: NO ENCONTRADO")