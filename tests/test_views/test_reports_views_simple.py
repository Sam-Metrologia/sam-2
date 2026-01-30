"""
Tests simplificados para vistas de reports.py.

Objetivo: Aumentar coverage reports.py a >60%.
"""
import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone
import json

from core.models import Empresa, CustomUser, Equipo, Calibracion
from core.constants import ESTADO_ACTIVO


@pytest.mark.django_db
class TestReportsBasic:
    """Tests básicos para vistas de reports."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup común."""
        self.client = Client()
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test",
            nit="900111222-3",
            limite_equipos_empresa=100,
        )
        self.user = CustomUser.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="testpass123",
            empresa=self.empresa,
            rol_usuario="ADMINISTRADOR",
            is_superuser=True,
        )
        self.client.login(username="testuser", password="testpass123")

    def test_informes_view_loads(self):
        """Test: Vista de informes carga."""
        response = self.client.get(reverse('core:informes'))
        assert response.status_code == 200

    def test_exportar_excel_sin_equipos(self):
        """Test: Exportar Excel sin equipos."""
        response = self.client.get(
            reverse('core:exportar_equipos_excel'),
            {'empresa_id': self.empresa.id}
        )
        assert response.status_code == 200

    def test_exportar_excel_con_equipos(self):
        """Test: Exportar Excel con equipos."""
        for i in range(3):
            Equipo.objects.create(
                codigo_interno=f"EQ-{i}",
                nombre=f"Equipo {i}",
                empresa=self.empresa,
                tipo_equipo="Equipo de Medición",
                estado=ESTADO_ACTIVO,
            )

        response = self.client.get(
            reverse('core:exportar_equipos_excel'),
            {'empresa_id': self.empresa.id}
        )
        assert response.status_code == 200
        assert len(response.content) > 1000

    def test_dashboard_excel(self):
        """Test: Dashboard Excel."""
        response = self.client.get(
            reverse('core:generar_informe_dashboard_excel'),
            {'empresa_id': self.empresa.id}
        )
        assert response.status_code == 200

    def test_plantilla_excel(self):
        """Test: Plantilla Excel."""
        response = self.client.get(reverse('core:descargar_plantilla_excel'))
        assert response.status_code == 200

    def test_hoja_vida_pdf(self):
        """Test: Hoja de vida PDF."""
        equipo = Equipo.objects.create(
            codigo_interno="EQ-001",
            nombre="Equipo PDF",
            empresa=self.empresa,
            tipo_equipo="Equipo de Medición",
            estado=ESTADO_ACTIVO,
        )

        Calibracion.objects.create(
            equipo=equipo,
            fecha_calibracion=timezone.now().date(),
        )

        response = self.client.get(
            reverse('core:generar_hoja_vida_pdf', args=[equipo.pk])
        )
        assert response.status_code == 200

    def test_generar_zip_con_equipos(self):
        """Test: Generar ZIP."""
        for i in range(2):
            Equipo.objects.create(
                codigo_interno=f"EQ-ZIP-{i}",
                nombre=f"Equipo {i}",
                empresa=self.empresa,
                tipo_equipo="Equipo de Medición",
                estado=ESTADO_ACTIVO,
            )

        response = self.client.get(
            reverse('core:generar_informe_zip'),
            {'empresa_id': self.empresa.id, 'parte': 1}
        )
        assert response.status_code in [200, 302]
