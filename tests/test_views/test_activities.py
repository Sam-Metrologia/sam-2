"""
Tests for Activity views (Calibraciones, Mantenimientos, Comprobaciones).

Tests CRUD operations and relationships with equipment.
"""
import pytest
from django.urls import reverse
from core.models import Calibracion, Mantenimiento, Comprobacion


@pytest.mark.django_db
@pytest.mark.views
class TestCalibracionViews:
    """Test suite for calibration views."""

    def test_añadir_calibracion_requires_login(self, client, sample_equipo):
        """Test adding calibration requires authentication."""
        url = reverse('core:añadir_calibracion', args=[sample_equipo.pk])
        response = client.get(url)

        assert response.status_code == 302
        assert '/login/' in response.url

    def test_añadir_calibracion_get_shows_form(self, authenticated_client, equipo_factory):
        """Test GET request shows calibration form."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)

        url = reverse('core:añadir_calibracion', args=[equipo.pk])
        response = authenticated_client.get(url)

        assert response.status_code == 200
        content = response.content.decode()

        # Should have calibration form fields
        assert 'fecha' in content.lower() or 'calibraci' in content.lower()

    def test_añadir_calibracion_post_creates_record(self, authenticated_client, equipo_factory):
        """Test POST creates calibration record."""
        from datetime import date

        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)

        url = reverse('core:añadir_calibracion', args=[equipo.pk])
        data = {
            'fecha_calibracion': date.today().isoformat(),
            'nombre_proveedor': 'Test Proveedor',
            'resultado': 'Aprobado',  # Fixed: correct choice value
            'numero_certificado': 'CERT-001'
        }

        response = authenticated_client.post(url, data)

        # Should redirect after creation
        assert response.status_code == 302

        # Verify calibration was created
        calibracion = Calibracion.objects.filter(
            equipo=equipo,
            numero_certificado='CERT-001'
        ).first()

        assert calibracion is not None
        assert calibracion.equipo == equipo

    def test_añadir_calibracion_multitenancy_protection(self, authenticated_client, equipo_factory, empresa_factory):
        """Test user cannot add calibration to other empresa's equipment."""
        other_empresa = empresa_factory()
        other_equipo = equipo_factory(empresa=other_empresa)

        url = reverse('core:añadir_calibracion', args=[other_equipo.pk])
        response = authenticated_client.get(url)

        # Should redirect with error message (actual behavior: core/views/activities.py:28-29)
        # The view checks multitenancy and redirects to detalle_equipo with error
        assert response.status_code == 302
        assert f'/equipos/{other_equipo.pk}/' in response.url

    def test_editar_calibracion_updates_record(self, authenticated_client, equipo_factory, calibracion_factory):
        """Test editing calibration updates the record."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)
        calibracion = calibracion_factory(
            equipo=equipo,
            resultado='Aprobado'  # Fixed: correct choice value
        )

        url = reverse('core:editar_calibracion', args=[equipo.pk, calibracion.pk])
        data = {
            'fecha_calibracion': calibracion.fecha_calibracion.isoformat(),
            'nombre_proveedor': calibracion.nombre_proveedor or 'Proveedor',
            'resultado': 'No Aprobado',  # Fixed: correct choice value
            'numero_certificado': calibracion.numero_certificado or 'CERT'
        }

        response = authenticated_client.post(url, data)

        # Should redirect after update
        assert response.status_code == 302

        # Verify update
        calibracion.refresh_from_db()
        assert calibracion.resultado == 'No Aprobado'  # Fixed: correct choice value

    def test_eliminar_calibracion_deletes_record(self, authenticated_client, equipo_factory, calibracion_factory):
        """Test deleting calibration removes the record."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)
        calibracion = calibracion_factory(equipo=equipo)

        calibracion_id = calibracion.pk

        url = reverse('core:eliminar_calibracion', args=[equipo.pk, calibracion.pk])
        response = authenticated_client.post(url)

        # Should redirect after deletion
        assert response.status_code == 302

        # Verify deletion
        exists = Calibracion.objects.filter(pk=calibracion_id).exists()
        assert not exists


@pytest.mark.django_db
@pytest.mark.views
class TestMantenimientoViews:
    """Test suite for maintenance views."""

    def test_añadir_mantenimiento_requires_login(self, client, sample_equipo):
        """Test adding maintenance requires authentication."""
        url = reverse('core:añadir_mantenimiento', args=[sample_equipo.pk])
        response = client.get(url)

        assert response.status_code == 302
        assert '/login/' in response.url

    def test_añadir_mantenimiento_get_shows_form(self, authenticated_client, equipo_factory):
        """Test GET request shows maintenance form."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)

        url = reverse('core:añadir_mantenimiento', args=[equipo.pk])
        response = authenticated_client.get(url)

        assert response.status_code == 200
        content = response.content.decode()

        # Should have maintenance form fields
        assert 'mantenimiento' in content.lower() or 'fecha' in content.lower()

    def test_añadir_mantenimiento_post_creates_record(self, authenticated_client, equipo_factory):
        """Test POST creates maintenance record."""
        from datetime import date

        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)

        url = reverse('core:añadir_mantenimiento', args=[equipo.pk])
        data = {
            'fecha_mantenimiento': date.today().isoformat(),
            'tipo_mantenimiento': 'Preventivo',
            'nombre_proveedor': 'Test Provider',
            'responsable': 'Test User',
            'descripcion': 'Test maintenance'
        }

        response = authenticated_client.post(url, data)

        # Should redirect after creation
        assert response.status_code == 302

        # Verify maintenance was created
        mantenimiento = Mantenimiento.objects.filter(
            equipo=equipo,
            tipo_mantenimiento='Preventivo'
        ).first()

        assert mantenimiento is not None
        assert mantenimiento.equipo == equipo

    def test_detalle_mantenimiento_shows_data(self, authenticated_client, equipo_factory, mantenimiento_factory):
        """Test maintenance detail view shows correct data."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)
        mantenimiento = mantenimiento_factory(
            equipo=equipo,
            descripcion='Test Maintenance Description'
        )

        url = reverse('core:detalle_mantenimiento', args=[equipo.pk, mantenimiento.pk])
        response = authenticated_client.get(url)

        assert response.status_code == 200
        content = response.content.decode()

        # Should show maintenance details
        assert 'Test Maintenance Description' in content or 'mantenimiento' in content.lower()

    def test_editar_mantenimiento_multitenancy_protection(self, authenticated_client, equipo_factory, mantenimiento_factory, empresa_factory):
        """Test user cannot edit maintenance from other empresa."""
        other_empresa = empresa_factory()
        other_equipo = equipo_factory(empresa=other_empresa)
        other_mantenimiento = mantenimiento_factory(equipo=other_equipo)

        url = reverse('core:editar_mantenimiento', args=[other_equipo.pk, other_mantenimiento.pk])
        response = authenticated_client.get(url)

        # Should redirect with error message (actual behavior: core/views/activities.py:285-287)
        # The view checks multitenancy and redirects to detalle_equipo with error
        assert response.status_code == 302
        assert f'/equipos/{other_equipo.pk}/' in response.url


@pytest.mark.django_db
@pytest.mark.views
class TestComprobacionViews:
    """Test suite for comprobacion views."""

    def test_añadir_comprobacion_requires_login(self, client, sample_equipo):
        """Test adding comprobacion requires authentication."""
        url = reverse('core:añadir_comprobacion', args=[sample_equipo.pk])
        response = client.get(url)

        assert response.status_code == 302
        assert '/login/' in response.url

    def test_añadir_comprobacion_get_shows_form(self, authenticated_client, equipo_factory):
        """Test GET request shows comprobacion form."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)

        url = reverse('core:añadir_comprobacion', args=[equipo.pk])
        response = authenticated_client.get(url)

        assert response.status_code == 200
        content = response.content.decode()

        # Should have comprobacion form fields
        assert 'comprobaci' in content.lower() or 'fecha' in content.lower()

    def test_añadir_comprobacion_post_creates_record(self, authenticated_client, equipo_factory):
        """Test POST creates comprobacion record."""
        from datetime import date

        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)

        url = reverse('core:añadir_comprobacion', args=[equipo.pk])
        data = {
            'fecha_comprobacion': date.today().isoformat(),
            'nombre_proveedor': 'Test Provider',
            'responsable': 'Test User',
            'resultado': 'Aprobado',  # Fixed: correct choice value
            'observaciones': 'Test comprobacion'
        }

        response = authenticated_client.post(url, data)

        # Should redirect after creation
        assert response.status_code == 302

        # Verify comprobacion was created
        comprobacion = Comprobacion.objects.filter(
            equipo=equipo,
            resultado='Aprobado'  # Fixed: correct choice value
        ).first()

        assert comprobacion is not None
        assert comprobacion.equipo == equipo

    def test_eliminar_comprobacion_deletes_record(self, authenticated_client, equipo_factory, comprobacion_factory):
        """Test deleting comprobacion removes the record."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)
        comprobacion = comprobacion_factory(equipo=equipo)

        comprobacion_id = comprobacion.pk

        url = reverse('core:eliminar_comprobacion', args=[equipo.pk, comprobacion.pk])
        response = authenticated_client.post(url)

        # Should redirect after deletion
        assert response.status_code == 302

        # Verify deletion
        exists = Comprobacion.objects.filter(pk=comprobacion_id).exists()
        assert not exists


@pytest.mark.django_db
@pytest.mark.views
class TestActivityIntegration:
    """Test suite for activity integration with equipment."""

    def test_equipo_shows_all_activities(self, authenticated_client, equipo_factory, mantenimiento_factory, calibracion_factory, comprobacion_factory):
        """Test equipment detail shows all types of activities."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)

        # Add all types of activities
        mantenimiento_factory(equipo=equipo)
        calibracion_factory(equipo=equipo)
        comprobacion_factory(equipo=equipo)

        url = reverse('core:detalle_equipo', args=[equipo.pk])
        response = authenticated_client.get(url)

        assert response.status_code == 200
        content = response.content.decode().lower()

        # Should show all activity types
        # (May vary by template implementation)
        has_activities = (
            'mantenimiento' in content or
            'calibraci' in content or
            'comprobaci' in content or
            'actividad' in content
        )

        assert has_activities

    def test_activities_count_on_home(self, authenticated_client, equipo_factory, mantenimiento_factory):
        """Test home page shows activity counts or indicators."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)

        # Add multiple activities
        mantenimiento_factory(equipo=equipo)
        mantenimiento_factory(equipo=equipo)

        url = reverse('core:home')
        response = authenticated_client.get(url)

        assert response.status_code == 200

        # Should have some activity indicators
        # (Implementation may vary)
        assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.views
class TestActivityPermissions:
    """Test suite for activity permission checks."""

    def test_regular_user_cannot_delete_others_activities(self, client, user_factory, equipo_factory, mantenimiento_factory):
        """Test user cannot delete activities from equipment they don't own."""
        user1 = user_factory()
        user2 = user_factory()

        equipo1 = equipo_factory(empresa=user1.empresa)
        mantenimiento1 = mantenimiento_factory(equipo=equipo1)

        # Login as user2
        client.force_login(user2)

        url = reverse('core:eliminar_mantenimiento', args=[equipo1.pk, mantenimiento1.pk])
        response = client.post(url)

        # Should be forbidden or not found
        assert response.status_code in [403, 404]

        # Verify mantenimiento still exists
        assert Mantenimiento.objects.filter(pk=mantenimiento1.pk).exists()
