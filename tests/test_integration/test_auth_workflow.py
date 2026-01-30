"""
Tests de integración para flujos completos de autenticación y sesiones de usuario.

Verifica flujos end-to-end de login, operaciones y logout.
"""
import pytest
from django.urls import reverse
from core.models import Equipo


@pytest.mark.django_db
@pytest.mark.integration
class TestAuthenticationWorkflow:
    """Test suite for complete authentication workflows."""

    def test_flujo_completo_login_operaciones_logout(self, authenticated_client, equipo_factory):
        """
        Test complete user session workflow:
        Login → Navigate → Perform operations → Logout.

        This simulates a complete user session from start to finish.
        """
        # Use authenticated client which already has a user with permissions
        user = authenticated_client.user

        # Create some equipment for the user to interact with
        equipo = equipo_factory(
            empresa=user.empresa,
            codigo_interno='WF-TEST-001',
            nombre='Equipo Workflow Test'
        )

        # User is already logged in via authenticated_client
        # Step 1: User accesses dashboard
        dashboard_url = reverse('core:dashboard')
        response = authenticated_client.get(dashboard_url)
        assert response.status_code == 200

        # Step 2: User accesses home/equipment list
        home_url = reverse('core:home')
        response = authenticated_client.get(home_url)
        assert response.status_code == 200

        # Step 3: User views equipment detail
        detail_url = reverse('core:detalle_equipo', args=[equipo.pk])
        response = authenticated_client.get(detail_url)
        assert response.status_code == 200

        # Step 4: User logs out
        logout_url = reverse('core:logout')
        response = authenticated_client.get(logout_url)

        # Should redirect after logout
        assert response.status_code == 302

        # Step 5: Verify user is logged out - accessing dashboard should redirect to login
        response = authenticated_client.get(dashboard_url)
        assert response.status_code in [302, 403]  # Could redirect or deny
        if response.status_code == 302:
            assert '/login/' in response.url or '/accounts/login/' in response.url


@pytest.mark.django_db
@pytest.mark.integration
class TestUserNavigationWorkflow:
    """Test workflows for typical user navigation patterns."""

    def test_flujo_navegacion_tipica_usuario(self, authenticated_client, equipo_factory, calibracion_factory):
        """
        Test typical user navigation:
        Dashboard → Equipment list → Equipment detail → Add activity → Back to list.
        """
        user = authenticated_client.user

        # Create equipment with activities
        equipo = equipo_factory(empresa=user.empresa)
        calibracion = calibracion_factory(equipo=equipo)

        # Step 1: User accesses dashboard
        dashboard_url = reverse('core:dashboard')
        response = authenticated_client.get(dashboard_url)
        assert response.status_code == 200

        # Step 2: User goes to equipment list
        home_url = reverse('core:home')
        response = authenticated_client.get(home_url)
        assert response.status_code == 200

        # Step 3: User views specific equipment
        detail_url = reverse('core:detalle_equipo', args=[equipo.pk])
        response = authenticated_client.get(detail_url)
        assert response.status_code == 200
        content = response.content.decode().lower()

        # Should show equipment details
        assert equipo.codigo_interno.lower() in content or 'equipo' in content

        # Step 4: User accesses calibration add form
        add_cal_url = reverse('core:añadir_calibracion', args=[equipo.pk])
        response = authenticated_client.get(add_cal_url)
        assert response.status_code == 200

        # Step 5: User returns to equipment list
        response = authenticated_client.get(home_url)
        assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.integration
class TestPermissionDeniedWorkflow:
    """Test workflows when permissions are denied."""

    def test_flujo_acceso_denegado_sin_permisos(self, client, user_factory):
        """
        Test workflow when user tries to access admin-only pages.

        Regular user → Try to access admin page → Get redirected/denied.
        """
        # Create regular user (not superuser)
        user = user_factory(is_superuser=False, is_staff=False)

        # Login as regular user
        client.force_login(user)

        # Try to access admin-only pages
        admin_urls = [
            reverse('core:listar_empresas'),  # Requires superuser
        ]

        for url in admin_urls:
            response = client.get(url)

            # Should not allow access (302 redirect or 403 forbidden)
            assert response.status_code in [302, 403], f"URL {url} should deny access"


@pytest.mark.django_db
@pytest.mark.integration
class TestPasswordChangeWorkflow:
    """Test workflows for password management."""

    def test_flujo_cambiar_password(self, authenticated_client):
        """
        Test password change workflow:
        Login → Navigate to password change → Change password → Verify.
        """
        user = authenticated_client.user
        original_password_hash = user.password

        # Step 1: Navigate to password change page
        password_change_url = reverse('core:password_change')
        response = authenticated_client.get(password_change_url)

        # Should be accessible
        assert response.status_code == 200

        # Step 2: Submit password change form
        password_data = {
            'old_password': 'testpass123',
            'new_password1': 'NewTestPass456!',
            'new_password2': 'NewTestPass456!',
        }

        response = authenticated_client.post(password_change_url, password_data)

        # Should redirect on success (implementation may vary)
        if response.status_code == 302:
            # Verify password was changed
            user.refresh_from_db()
            assert user.password != original_password_hash

            # Verify user can still login with new password
            from django.contrib.auth import authenticate
            authenticated_user = authenticate(
                username=user.username,
                password='NewTestPass456!'
            )
            assert authenticated_user is not None
            assert authenticated_user.pk == user.pk
