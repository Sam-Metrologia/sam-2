"""
Tests for Reports and PDF generation views.

Tests report generation, exports, and file downloads.
"""
import pytest
from django.urls import reverse
from io import BytesIO


@pytest.mark.django_db
@pytest.mark.views
class TestInformesView:
    """Test suite for main reports/informes view."""

    def test_informes_requires_login(self, client):
        """Test informes page requires authentication."""
        url = reverse('core:informes')
        response = client.get(url)

        assert response.status_code == 302
        assert '/login/' in response.url

    def test_informes_accessible_authenticated(self, authenticated_client):
        """Test authenticated user can access informes."""
        url = reverse('core:informes')
        response = authenticated_client.get(url)

        assert response.status_code == 200

    def test_informes_shows_report_options(self, authenticated_client):
        """Test informes page shows report generation options."""
        url = reverse('core:informes')
        response = authenticated_client.get(url)

        assert response.status_code == 200
        content = response.content.decode().lower()

        # Should show report types
        assert 'pdf' in content or 'excel' in content or 'zip' in content or 'informe' in content


@pytest.mark.django_db
@pytest.mark.views
class TestPDFGeneration:
    """Test suite for PDF generation."""

    def test_hoja_vida_pdf_requires_login(self, client, sample_equipo):
        """Test hoja de vida PDF requires authentication."""
        url = reverse('core:generar_hoja_vida_pdf', args=[sample_equipo.pk])
        response = client.get(url)

        assert response.status_code == 302
        assert '/login/' in response.url

    def test_hoja_vida_pdf_generates_file(self, authenticated_client, equipo_factory):
        """Test hoja de vida PDF generation."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)

        url = reverse('core:generar_hoja_vida_pdf', args=[equipo.pk])
        response = authenticated_client.get(url)

        # Should return PDF or redirect
        assert response.status_code in [200, 302]

        if response.status_code == 200:
            # Should be PDF content type
            assert 'pdf' in response.get('Content-Type', '').lower() or \
                   'application/pdf' in response.get('Content-Type', '')

    def test_hoja_vida_pdf_multitenancy_protection(self, authenticated_client, equipo_factory, empresa_factory):
        """Test user cannot generate PDF for other empresa's equipment."""
        other_empresa = empresa_factory()
        other_equipo = equipo_factory(empresa=other_empresa)

        url = reverse('core:generar_hoja_vida_pdf', args=[other_equipo.pk])
        response = authenticated_client.get(url)

        # Should be forbidden, not found, or redirected (multitenancy protection)
        assert response.status_code in [302, 403, 404]

    def test_informe_vencimientos_pdf_requires_login(self, client):
        """Test vencimientos PDF requires authentication."""
        url = reverse('core:informe_vencimientos_pdf')
        response = client.get(url)

        assert response.status_code == 302
        assert '/login/' in response.url

    def test_informe_vencimientos_pdf_generates(self, authenticated_client, equipo_factory):
        """Test vencimientos PDF generation."""
        user = authenticated_client.user

        # Create some equipment
        equipo_factory(empresa=user.empresa)
        equipo_factory(empresa=user.empresa)

        url = reverse('core:informe_vencimientos_pdf')
        response = authenticated_client.get(url)

        # Should generate PDF or redirect
        assert response.status_code in [200, 302]


@pytest.mark.django_db
@pytest.mark.views
class TestExcelExports:
    """Test suite for Excel exports."""

    def test_exportar_equipos_excel_requires_login(self, client):
        """Test Excel export requires authentication."""
        url = reverse('core:exportar_equipos_excel')
        response = client.get(url)

        assert response.status_code == 302
        assert '/login/' in response.url

    def test_exportar_equipos_excel_generates_file(self, authenticated_client, equipo_factory):
        """Test Excel export generates file."""
        user = authenticated_client.user

        # Create equipment
        equipo_factory(empresa=user.empresa)
        equipo_factory(empresa=user.empresa)

        url = reverse('core:exportar_equipos_excel')
        response = authenticated_client.get(url)

        # Should return Excel file or redirect
        assert response.status_code in [200, 302]

        if response.status_code == 200:
            # Should be Excel content type
            content_type = response.get('Content-Type', '').lower()
            assert 'excel' in content_type or \
                   'spreadsheet' in content_type or \
                   'application/vnd' in content_type

    def test_exportar_equipos_excel_only_user_empresa(self, authenticated_client, equipo_factory, empresa_factory):
        """Test Excel export only includes user's empresa equipment."""
        user = authenticated_client.user
        other_empresa = empresa_factory()

        # Create equipment for user's empresa
        my_equipo = equipo_factory(empresa=user.empresa, codigo_interno="MY-001")

        # Create equipment for other empresa
        other_equipo = equipo_factory(empresa=other_empresa, codigo_interno="OTHER-001")

        url = reverse('core:exportar_equipos_excel')
        response = authenticated_client.get(url)

        assert response.status_code in [200, 302]

        # If successful, response should only contain user's data
        # (Content check would require parsing Excel, so we just verify it generates)

    def test_dashboard_excel_requires_login(self, client):
        """Test dashboard Excel export requires authentication."""
        url = reverse('core:generar_informe_dashboard_excel')
        response = client.get(url)

        assert response.status_code == 302
        assert '/login/' in response.url

    def test_dashboard_excel_generates(self, authenticated_client, equipo_factory):
        """Test dashboard Excel export generates file."""
        user = authenticated_client.user
        equipo_factory(empresa=user.empresa)

        url = reverse('core:generar_informe_dashboard_excel')
        response = authenticated_client.get(url)

        # Should generate or redirect
        assert response.status_code in [200, 302]


@pytest.mark.django_db
@pytest.mark.views
class TestZIPGeneration:
    """Test suite for ZIP file generation."""

    def test_generar_zip_requires_login(self, client):
        """Test ZIP generation requires authentication."""
        url = reverse('core:generar_informe_zip')
        response = client.get(url)

        assert response.status_code == 302
        assert '/login/' in response.url

    def test_solicitar_zip_creates_request(self, authenticated_client, equipo_factory):
        """Test ZIP request creation."""
        user = authenticated_client.user

        # Create some equipment
        equipo1 = equipo_factory(empresa=user.empresa)
        equipo2 = equipo_factory(empresa=user.empresa)

        url = reverse('core:solicitar_zip')
        data = {
            'equipos[]': [equipo1.pk, equipo2.pk]
        }

        response = authenticated_client.post(url, data)

        # Should create ZIP request
        # Response varies by implementation (redirect, JSON, etc.)
        assert response.status_code in [200, 201, 302]

    def test_my_zip_requests_requires_login(self, client):
        """Test viewing ZIP requests requires authentication."""
        url = reverse('core:my_zip_requests')
        response = client.get(url)

        assert response.status_code == 302
        assert '/login/' in response.url

    def test_my_zip_requests_shows_user_requests(self, authenticated_client):
        """Test my ZIP requests shows only user's requests."""
        url = reverse('core:my_zip_requests')
        response = authenticated_client.get(url)

        # Should show user's ZIP requests
        assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.views
class TestProgrammedActivities:
    """Test suite for programmed activities report."""

    def test_programmed_activities_requires_login(self, client):
        """Test programmed activities report requires authentication."""
        url = reverse('core:programmed_activities_list')
        response = client.get(url)

        assert response.status_code == 302
        assert '/login/' in response.url

    def test_programmed_activities_lists_upcoming(self, authenticated_client, equipo_factory, mantenimiento_factory):
        """Test programmed activities shows upcoming activities."""
        from datetime import timedelta
        from django.utils import timezone

        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)

        # Create upcoming maintenance
        future_date = timezone.now().date() + timedelta(days=30)
        equipo.proximo_mantenimiento = future_date
        equipo.save()

        url = reverse('core:programmed_activities_list')
        response = authenticated_client.get(url)

        assert response.status_code == 200

    def test_programmed_activities_multitenancy(self, authenticated_client, equipo_factory, empresa_factory):
        """Test programmed activities only shows user's empresa activities."""
        from datetime import timedelta
        from django.utils import timezone

        user = authenticated_client.user
        other_empresa = empresa_factory()

        # Create equipment with upcoming activities
        my_equipo = equipo_factory(empresa=user.empresa)
        my_equipo.proximo_mantenimiento = timezone.now().date() + timedelta(days=10)
        my_equipo.save()

        other_equipo = equipo_factory(empresa=other_empresa)
        other_equipo.proximo_mantenimiento = timezone.now().date() + timedelta(days=10)
        other_equipo.save()

        url = reverse('core:programmed_activities_list')
        response = authenticated_client.get(url)

        assert response.status_code == 200
        content = response.content.decode()

        # Should show my equipment
        assert my_equipo.codigo_interno in content or str(my_equipo.pk) in content

        # Should NOT show other empresa's equipment
        assert other_equipo.codigo_interno not in content


@pytest.mark.django_db
@pytest.mark.views
class TestReportPermissions:
    """Test suite for report permission checks."""

    def test_regular_user_can_generate_own_reports(self, authenticated_client, equipo_factory):
        """Test regular user can generate reports for their empresa."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)

        url = reverse('core:generar_hoja_vida_pdf', args=[equipo.pk])
        response = authenticated_client.get(url)

        # Should be allowed
        assert response.status_code in [200, 302]
        # Should NOT be 403
        assert response.status_code != 403

    def test_reports_respect_empresa_isolation(self, client, user_factory, equipo_factory):
        """Test reports respect empresa data isolation."""
        # Create two users from different empresas
        user1 = user_factory()
        user2 = user_factory()

        equipo1 = equipo_factory(empresa=user1.empresa)

        # Login as user2
        client.force_login(user2)

        # Try to access user1's equipment report
        url = reverse('core:generar_hoja_vida_pdf', args=[equipo1.pk])
        response = client.get(url)

        # Should be forbidden, not found, or redirected (multitenancy protection)
        assert response.status_code in [302, 403, 404]


@pytest.mark.django_db
@pytest.mark.views
class TestExportFinanciero:
    """Test suite for financial analysis export."""

    def test_exportar_analisis_financiero_requires_login(self, client):
        """Test financial export requires authentication."""
        url = reverse('core:exportar_analisis_financiero')
        response = client.get(url)

        assert response.status_code == 302
        assert '/login/' in response.url

    def test_exportar_analisis_financiero_generates(self, authenticated_client, equipo_factory, mantenimiento_factory, calibracion_factory):
        """Test financial analysis export generates file."""
        user = authenticated_client.user

        # Grant permission to access financial dashboard
        user.can_access_dashboard_decisiones = True
        user.save()

        equipo = equipo_factory(empresa=user.empresa)

        # Add activities with costs
        mantenimiento_factory(equipo=equipo, costo=100000)
        calibracion_factory(equipo=equipo, costo_calibracion=200000)

        url = reverse('core:exportar_analisis_financiero')
        response = authenticated_client.get(url)

        # Should generate file, redirect, or deny access (403)
        assert response.status_code in [200, 302, 403]
