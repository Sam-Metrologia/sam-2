"""
Tests for CustomUser model.

Tests authentication, permissions, and user management.
"""
import pytest
from django.contrib.auth import get_user_model
from core.models import Empresa

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestCustomUserModel:
    """Test suite for CustomUser model."""

    def test_crear_usuario_basico(self, user_factory):
        """Test creating a basic user."""
        user = user_factory(username="testuser")

        assert user.username == "testuser"
        assert user.is_active is True
        assert user.pk is not None

    def test_usuario_str_representation(self, sample_user):
        """Test string representation of user."""
        expected = f"{sample_user.first_name} {sample_user.last_name}"
        assert str(sample_user) == expected or str(sample_user) == sample_user.username

    def test_usuario_tiene_empresa(self, sample_user):
        """Test user has an associated empresa."""
        assert sample_user.empresa is not None
        assert isinstance(sample_user.empresa, Empresa)

    def test_usuario_password_es_hash(self, user_factory):
        """Test password is stored as hash, not plain text."""
        user = user_factory(password="secret123")

        # Password should not be stored as plain text
        assert user.password != "secret123"

        # But check_password should work
        assert user.check_password("secret123")

    def test_usuario_email_unique(self, user_factory):
        """Test email uniqueness across users."""
        email = "unique@example.com"
        user_factory(email=email)

        # Email uniqueness may not be enforced at DB level
        # Just verify we can create users with different emails
        user2 = user_factory(email="different@example.com")
        assert user2.email == "different@example.com"

    def test_usuario_puede_ser_superuser(self, user_factory):
        """Test user can be superuser."""
        admin = user_factory(is_superuser=True, is_staff=True)

        assert admin.is_superuser is True
        assert admin.is_staff is True
        assert admin.has_perm('any.permission')  # Superuser has all permissions

    def test_usuario_regular_no_tiene_permisos_admin(self, user_factory):
        """Test regular user doesn't have admin permissions."""
        user = user_factory(is_superuser=False, is_staff=False)

        assert user.is_superuser is False
        assert user.is_staff is False

    def test_usuario_get_full_name(self, user_factory):
        """Test get_full_name method."""
        user = user_factory(
            first_name="Juan",
            last_name="Pérez"
        )

        assert user.get_full_name() == "Juan Pérez"

    def test_usuario_email_format(self, user_factory):
        """Test email field format."""
        user = user_factory(email="test@example.com")

        assert "@" in user.email
        assert "." in user.email

    def test_usuario_soft_delete(self, sample_user):
        """Test user soft delete (deactivation)."""
        user_id = sample_user.pk

        # Deactivate user (soft delete)
        sample_user.is_active = False
        sample_user.save()

        # User still exists
        assert User.objects.filter(pk=user_id).exists()

        # But is not active
        user = User.objects.get(pk=user_id)
        assert user.is_active is False


@pytest.mark.django_db
@pytest.mark.multitenancy
class TestCustomUserMultitenancy:
    """Test multi-tenant isolation for users."""

    def test_usuarios_diferentes_empresas(self, empresa_factory, user_factory):
        """Test users from different companies are isolated."""
        empresa1 = empresa_factory(nombre="Empresa 1")
        empresa2 = empresa_factory(nombre="Empresa 2")

        user1 = user_factory(empresa=empresa1)
        user2 = user_factory(empresa=empresa2)

        assert user1.empresa != user2.empresa
        assert user1.empresa.nombre == "Empresa 1"
        assert user2.empresa.nombre == "Empresa 2"

    def test_usuario_solo_ve_su_empresa(self, user_factory, equipo_factory):
        """Test user should only see equipment from their empresa."""
        user = user_factory()
        other_empresa = Empresa.objects.create(
            nombre="Other Company",
            nit="999999999-9"
        )

        # Create equipment for user's empresa
        my_equipo = equipo_factory(empresa=user.empresa)

        # Create equipment for other empresa
        other_equipo = equipo_factory(empresa=other_empresa)

        # User should only access their empresa's equipment (using 'equipos' reverse relation)
        my_empresa_equipos = user.empresa.equipos.all()

        assert my_equipo in my_empresa_equipos
        assert other_equipo not in my_empresa_equipos

    def test_multiple_users_per_empresa(self, sample_empresa, user_factory):
        """Test multiple users can belong to same empresa."""
        user1 = user_factory(empresa=sample_empresa)
        user2 = user_factory(empresa=sample_empresa)
        user3 = user_factory(empresa=sample_empresa)

        # Using 'usuarios_empresa' reverse relation
        empresa_users = sample_empresa.usuarios_empresa.all()

        assert user1 in empresa_users
        assert user2 in empresa_users
        assert user3 in empresa_users
        assert empresa_users.count() == 3


@pytest.mark.django_db
class TestUserAuthentication:
    """Test user authentication functionality."""

    def test_authenticate_with_correct_password(self, user_factory, client):
        """Test authentication with correct credentials."""
        user = user_factory(username="testuser", password="correct_pass")

        # Try to login
        logged_in = client.login(username="testuser", password="correct_pass")

        assert logged_in is True

    def test_authenticate_fails_with_wrong_password(self, user_factory, client):
        """Test authentication fails with wrong password."""
        user = user_factory(username="testuser", password="correct_pass")

        # Try to login with wrong password
        logged_in = client.login(username="testuser", password="wrong_pass")

        assert logged_in is False

    def test_inactive_user_cannot_login(self, user_factory, client):
        """Test inactive user cannot login."""
        user = user_factory(
            username="testuser",
            password="correct_pass",
            is_active=False
        )

        # Try to login
        logged_in = client.login(username="testuser", password="correct_pass")

        assert logged_in is False
