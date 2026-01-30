"""
Tests for Empresa model.

Tests core functionality of the multi-tenant company system.
"""
import pytest
from django.core.exceptions import ValidationError
from core.models import Empresa


@pytest.mark.django_db
@pytest.mark.unit
class TestEmpresaModel:
    """Test suite for Empresa model."""

    def test_crear_empresa_basica(self, empresa_factory):
        """Test creating a basic empresa instance."""
        empresa = empresa_factory(nombre="Test Company SA")

        assert empresa.nombre == "Test Company SA"
        assert empresa.pk is not None
        assert empresa.nit is not None

    def test_empresa_str_representation(self, sample_empresa):
        """Test string representation of empresa."""
        assert str(sample_empresa) == sample_empresa.nombre

    def test_empresa_nit_unique(self, empresa_factory):
        """Test that NIT must be unique."""
        nit = "900123456-7"
        empresa_factory(nit=nit)

        # Try to create another empresa with same NIT
        with pytest.raises(Exception):  # IntegrityError
            empresa_factory(nit=nit)

    def test_empresa_plan_equipos_default(self, empresa_factory):
        """Test default equipment plan limit."""
        empresa = empresa_factory()

        # Should have a plan limit
        assert empresa.limite_equipos_empresa > 0
        assert isinstance(empresa.limite_equipos_empresa, int)

    def test_empresa_email_format(self, empresa_factory):
        """Test email field accepts valid email."""
        empresa = empresa_factory(email="contacto@example.com")

        assert "@" in empresa.email
        assert empresa.email == "contacto@example.com"

    def test_empresa_can_have_logo(self, empresa_factory, sample_image):
        """Test empresa can have logo uploaded."""
        empresa = empresa_factory()
        empresa.logo_empresa = sample_image
        empresa.save()

        assert empresa.logo_empresa is not None
        assert 'test_image' in empresa.logo_empresa.name

    def test_empresa_ordering(self, empresa_factory):
        """Test empresas are ordered by nombre."""
        empresa_factory(nombre="Zebra Company")
        empresa_factory(nombre="Alpha Company")
        empresa_factory(nombre="Beta Company")

        empresas = Empresa.objects.order_by('nombre')

        assert empresas[0].nombre == "Alpha Company"
        assert empresas[1].nombre == "Beta Company"
        assert empresas[2].nombre == "Zebra Company"


@pytest.mark.django_db
@pytest.mark.multitenancy
class TestEmpresaMultitenancy:
    """Test multi-tenant isolation for empresas."""

    def test_multiple_empresas_isolated(self, multiple_empresas):
        """Test that multiple empresas exist independently."""
        assert len(multiple_empresas) == 3

        # Each should have unique NIT
        nits = [e.nit for e in multiple_empresas]
        assert len(nits) == len(set(nits))  # All unique

    def test_empresa_equipment_limit(self, sample_empresa, equipo_factory):
        """Test empresa equipment plan limit."""
        sample_empresa.limite_equipos_empresa = 5
        sample_empresa.save()

        # Create equipos up to limit
        for _ in range(5):
            equipo_factory(empresa=sample_empresa)

        # Should have exactly 5 equipos (using 'equipos' reverse relation)
        equipos_count = sample_empresa.equipos.count()
        assert equipos_count == 5

    def test_empresa_users_relationship(self, sample_empresa, user_factory):
        """Test empresa can have multiple users."""
        # Create 3 users for the empresa
        for _ in range(3):
            user_factory(empresa=sample_empresa)

        # Check users count (using 'usuarios_empresa' reverse relation)
        users_count = sample_empresa.usuarios_empresa.count()
        assert users_count == 3
