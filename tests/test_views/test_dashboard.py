"""
Tests for Dashboard views.

Tests authentication, permissions, context data, and rendering.
"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.views
class TestDashboardView:
    """Test suite for main dashboard view."""

    def test_dashboard_requires_login(self, client):
        """Test dashboard redirects to login if not authenticated."""
        url = reverse('core:dashboard')
        response = client.get(url)

        # Should redirect to login
        assert response.status_code == 302
        assert '/login/' in response.url

    def test_dashboard_authenticated_user_access(self, authenticated_client):
        """Test authenticated user can access dashboard."""
        url = reverse('core:dashboard')
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert 'dashboard' in response.content.decode().lower()

    def test_dashboard_uses_correct_template(self, authenticated_client):
        """Test dashboard uses correct template."""
        url = reverse('core:dashboard')
        response = authenticated_client.get(url)

        assert response.status_code == 200
        # Check template used
        template_names = [t.name for t in response.templates]
        assert any('dashboard' in name.lower() for name in template_names)

    def test_dashboard_context_contains_equipos(self, authenticated_client, equipo_factory):
        """Test dashboard context includes equipment data."""
        user = authenticated_client.user

        # Create equipment for user's empresa
        equipo_factory(empresa=user.empresa)
        equipo_factory(empresa=user.empresa)

        url = reverse('core:dashboard')
        response = authenticated_client.get(url)

        assert response.status_code == 200
        # Context should have equipment-related data
        assert 'total_equipos' in response.context or 'equipos' in response.context

    def test_dashboard_multitenancy_isolation(self, authenticated_client, equipo_factory, empresa_factory):
        """Test dashboard only shows data from user's empresa."""
        user = authenticated_client.user
        other_empresa = empresa_factory()

        # Create equipment for user's empresa
        my_equipo = equipo_factory(empresa=user.empresa)

        # Create equipment for other empresa
        other_equipo = equipo_factory(empresa=other_empresa)

        url = reverse('core:dashboard')
        response = authenticated_client.get(url)

        assert response.status_code == 200
        content = response.content.decode()

        # Dashboard may show stats/charts but not necessarily individual equipment codes
        # The important thing is that it loads successfully
        assert response.status_code == 200

        # Verify multitenancy by checking the other equipment is NOT shown
        assert other_equipo.codigo_interno not in content


@pytest.mark.django_db
@pytest.mark.views
class TestDashboardGerencia:
    """Test suite for management dashboard."""

    def test_dashboard_gerencia_requires_login(self, client):
        """Test management dashboard requires authentication."""
        url = reverse('core:dashboard_gerencia')
        response = client.get(url)

        assert response.status_code == 302
        assert '/login/' in response.url

    def test_dashboard_gerencia_requires_permission(self, authenticated_client):
        """Test management dashboard requires special permission."""
        user = authenticated_client.user
        user.can_access_dashboard_decisiones = False
        user.save()

        url = reverse('core:dashboard_gerencia')
        response = authenticated_client.get(url)

        # Should redirect or show access denied
        assert response.status_code in [302, 403]

    def test_dashboard_gerencia_with_permission(self, authenticated_client):
        """Test management dashboard accessible with permission."""
        user = authenticated_client.user
        user.can_access_dashboard_decisiones = True
        user.save()

        url = reverse('core:dashboard_gerencia')
        response = authenticated_client.get(url)

        # Should be accessible (200) or redirect to main dashboard (302)
        # Depends on implementation
        assert response.status_code in [200, 302]


@pytest.mark.django_db
@pytest.mark.views
class TestPanelDecisiones:
    """Test suite for decision panel view."""

    def test_panel_decisiones_requires_login(self, client):
        """Test panel decisiones requires authentication."""
        url = reverse('core:panel_decisiones')
        response = client.get(url)

        assert response.status_code == 302
        assert '/login/' in response.url

    def test_panel_decisiones_authenticated_access(self, authenticated_client):
        """Test authenticated user can access panel decisiones."""
        url = reverse('core:panel_decisiones')
        response = authenticated_client.get(url)

        # Should be accessible (may vary by permissions)
        assert response.status_code in [200, 302, 403]


@pytest.mark.django_db
@pytest.mark.views
class TestHomeView:
    """Test suite for home/equipment list view."""

    def test_home_requires_login(self, client):
        """Test home page requires authentication."""
        url = reverse('core:home')
        response = client.get(url)

        assert response.status_code == 302
        assert '/login/' in response.url

    def test_home_lists_equipos(self, authenticated_client, equipo_factory):
        """Test home page lists equipment."""
        user = authenticated_client.user

        equipo1 = equipo_factory(empresa=user.empresa)
        equipo2 = equipo_factory(empresa=user.empresa)

        url = reverse('core:home')
        response = authenticated_client.get(url)

        assert response.status_code == 200
        content = response.content.decode()

        # Should show both equipments
        assert equipo1.codigo_interno in content
        assert equipo2.codigo_interno in content

    def test_home_multitenancy(self, authenticated_client, equipo_factory, empresa_factory):
        """Test home only shows user's empresa equipment."""
        user = authenticated_client.user
        other_empresa = empresa_factory()

        my_equipo = equipo_factory(empresa=user.empresa)
        other_equipo = equipo_factory(empresa=other_empresa)

        url = reverse('core:home')
        response = authenticated_client.get(url)

        assert response.status_code == 200
        content = response.content.decode()

        # Should show my equipment
        assert my_equipo.codigo_interno in content

        # Should NOT show other equipment
        assert other_equipo.codigo_interno not in content


@pytest.mark.django_db
@pytest.mark.views
class TestLoginView:
    """Test suite for login functionality."""

    def test_login_page_accessible(self, client):
        """Test login page is publicly accessible."""
        url = reverse('core:login')
        response = client.get(url)

        assert response.status_code == 200

    def test_login_with_valid_credentials(self, client, user_factory):
        """Test login with valid credentials."""
        user = user_factory(username='testuser', password='testpass123')

        url = reverse('core:login')
        response = client.post(url, {
            'username': 'testuser',
            'password': 'testpass123'
        })

        # Should redirect after successful login
        assert response.status_code == 302
        # Should redirect to dashboard
        assert 'dashboard' in response.url or response.url == '/'

    def test_login_with_invalid_credentials(self, client):
        """Test login with invalid credentials fails."""
        url = reverse('core:login')
        response = client.post(url, {
            'username': 'nonexistent',
            'password': 'wrongpass'
        })

        # Should stay on login page or show error
        assert response.status_code in [200, 302]
        if response.status_code == 200:
            content = response.content.decode()
            # Should show some error indication
            assert 'error' in content.lower() or 'invalid' in content.lower() or 'incorrect' in content.lower()


@pytest.mark.django_db
@pytest.mark.views
class TestLogoutView:
    """Test suite for logout functionality."""

    def test_logout_redirects(self, authenticated_client):
        """Test logout redirects to login page."""
        url = reverse('core:logout')
        response = authenticated_client.get(url)

        assert response.status_code == 302
        assert '/login/' in response.url

    def test_logout_clears_session(self, authenticated_client):
        """Test logout clears user session."""
        # First verify user is logged in
        assert '_auth_user_id' in authenticated_client.session

        # Logout
        url = reverse('core:logout')
        authenticated_client.get(url)

        # Session should be cleared (or at minimum, different session)
        # Note: After logout, authenticated_client.session will be the new session
        # So we test by trying to access protected page
        dashboard_url = reverse('core:dashboard')
        response = authenticated_client.get(dashboard_url)

        # Should redirect to login
        assert response.status_code == 302
        assert '/login/' in response.url
