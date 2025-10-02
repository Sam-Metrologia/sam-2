from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from core.views.dashboard_gerencia_simple import management_permission_required, dashboard_gerencia
from django.http import HttpRequest
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.db import SessionStore

User = get_user_model()

class Command(BaseCommand):
    help = 'Test dashboard access for specific users'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== TESTING DASHBOARD ACCESS ==='))

        # Create a request factory
        factory = RequestFactory()

        for username in ['CERTI', 'ALMA']:
            try:
                user = User.objects.get(username=username)
                self.stdout.write(f"\n--- Testing user: {username} ---")

                # Create a fake request
                request = factory.get('/core/dashboard-gerencia/')
                request.user = user

                # Add session and messages (required by Django views)
                request.session = SessionStore()
                request._messages = FallbackStorage(request)

                # Test the decorator directly
                user_role = getattr(user, 'rol_usuario', 'TECNICO')
                is_management_user = getattr(user, 'is_management_user', False)

                has_management_access = (
                    user.is_superuser or
                    is_management_user or
                    user_role in ['ADMINISTRADOR', 'GERENCIA']
                )

                self.stdout.write(f"User: {user.username}")
                self.stdout.write(f"rol_usuario: {user_role}")
                self.stdout.write(f"is_management_user: {is_management_user}")
                self.stdout.write(f"is_superuser: {user.is_superuser}")
                self.stdout.write(f"should_have_access: {has_management_access}")

                if has_management_access:
                    self.stdout.write(self.style.SUCCESS(f"✅ {username} should have dashboard access"))
                else:
                    self.stdout.write(self.style.ERROR(f"❌ {username} should NOT have dashboard access"))

            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User {username} not found"))

        self.stdout.write(self.style.SUCCESS('\n=== TEST COMPLETED ==='))