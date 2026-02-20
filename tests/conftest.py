"""
Global pytest configuration and fixtures for SAM Platform tests.
"""
import pytest
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import timedelta
import os


# ============================================================================
# FIXTURES: Cache Cleanup
# ============================================================================

@pytest.fixture(autouse=True)
def clear_cache():
    """Limpia el cache entre tests para evitar interferencia."""
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()


# ============================================================================
# FIXTURES: Test Clients
# ============================================================================

@pytest.fixture
def client():
    """
    Django test client for making requests.

    Usage:
        def test_something(client):
            response = client.get('/some-url/')
            assert response.status_code == 200
    """
    return Client()


@pytest.fixture
def authenticated_client(db, user_factory):
    """
    Client with authenticated regular user with full CRUD permissions.

    This user has all necessary permissions to perform CRUD operations
    on calibraciones, mantenimientos, comprobaciones, equipos, etc.
    This reflects a real-world scenario where authenticated users
    have appropriate permissions to use the application.

    Usage:
        def test_dashboard(authenticated_client):
            response = authenticated_client.get('/dashboard/')
            assert response.status_code == 200
    """
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType

    client = Client()
    user = user_factory()

    # Grant all necessary permissions for activities (calibraciones, mantenimientos, comprobaciones)
    # This is realistic because in production, users need these permissions to use the views
    permission_codenames = [
        # Calibracion permissions
        'add_calibracion',
        'change_calibracion',
        'delete_calibracion',
        'view_calibracion',
        # Mantenimiento permissions
        'add_mantenimiento',
        'change_mantenimiento',
        'delete_mantenimiento',
        'view_mantenimiento',
        # Comprobacion permissions
        'add_comprobacion',
        'change_comprobacion',
        'delete_comprobacion',
        'view_comprobacion',
        # Equipo permissions
        'add_equipo',
        'change_equipo',
        'delete_equipo',
        'view_equipo',
        # BajaEquipo permissions
        'add_bajaequipo',
        'change_bajaequipo',
        'delete_bajaequipo',
        'view_bajaequipo',
        # Empresa permissions
        'view_empresa',
        'change_empresa',
    ]

    # Assign permissions to user
    permissions = Permission.objects.filter(codename__in=permission_codenames)
    user.user_permissions.set(permissions)

    client.force_login(user)
    client.user = user  # Attach user for easy access
    return client


@pytest.fixture
def admin_client(db):
    """
    Client authenticated as superuser.

    Usage:
        def test_admin_panel(admin_client):
            response = admin_client.get('/admin/')
            assert response.status_code == 200
    """
    from tests.factories import UserFactory

    client = Client()
    admin_user = UserFactory(
        is_superuser=True,
        is_staff=True,
        username='admin_test'
    )
    client.force_login(admin_user)
    client.user = admin_user
    return client


# ============================================================================
# FIXTURES: Factories
# ============================================================================

@pytest.fixture
def empresa_factory(db):
    """Factory for creating Empresa instances."""
    from tests.factories import EmpresaFactory
    return EmpresaFactory


@pytest.fixture
def user_factory(db):
    """Factory for creating CustomUser instances."""
    from tests.factories import UserFactory
    return UserFactory


@pytest.fixture
def equipo_factory(db):
    """Factory for creating Equipo instances."""
    from tests.factories import EquipoFactory
    return EquipoFactory


@pytest.fixture
def mantenimiento_factory(db):
    """Factory for creating Mantenimiento instances."""
    from tests.factories import MantenimientoFactory
    return MantenimientoFactory


@pytest.fixture
def calibracion_factory(db):
    """Factory for creating Calibracion instances."""
    from tests.factories import CalibracionFactory
    return CalibracionFactory


@pytest.fixture
def comprobacion_factory(db):
    """Factory for creating Comprobacion instances."""
    from tests.factories import ComprobacionFactory
    return ComprobacionFactory


# ============================================================================
# FIXTURES: Test Data
# ============================================================================

@pytest.fixture
def sample_empresa(db, empresa_factory):
    """Single Empresa instance for testing."""
    return empresa_factory()


@pytest.fixture
def sample_user(db, user_factory):
    """Single CustomUser instance for testing."""
    return user_factory()


@pytest.fixture
def sample_equipo(db, equipo_factory):
    """Single Equipo instance for testing."""
    return equipo_factory()


@pytest.fixture
def multiple_empresas(db, empresa_factory):
    """Create 3 different companies for multitenancy tests."""
    return [empresa_factory() for _ in range(3)]


@pytest.fixture
def multiple_equipos(db, equipo_factory, sample_empresa):
    """Create 5 equipos for the same empresa."""
    return [equipo_factory(empresa=sample_empresa) for _ in range(5)]


# ============================================================================
# FIXTURES: File Uploads
# ============================================================================

@pytest.fixture
def sample_image():
    """
    Sample image file for testing uploads.

    Usage:
        def test_logo_upload(sample_image):
            empresa.logo = sample_image
            empresa.save()
    """
    # Create a simple 1x1 PNG
    image_content = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return SimpleUploadedFile(
        name='test_image.png',
        content=image_content,
        content_type='image/png'
    )


@pytest.fixture
def sample_pdf():
    """Sample PDF file for testing document uploads."""
    pdf_content = b'%PDF-1.4\n%Test PDF\n%%EOF'
    return SimpleUploadedFile(
        name='test_document.pdf',
        content=pdf_content,
        content_type='application/pdf'
    )


# ============================================================================
# FIXTURES: Settings and Configuration
# ============================================================================

@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """
    Use temporary directory for media files during tests.
    Automatically applied to all tests.
    """
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.MEDIA_ROOT.mkdir(exist_ok=True)
    return settings.MEDIA_ROOT


@pytest.fixture(autouse=True)
def email_backend(settings):
    """
    Use in-memory email backend for all tests.
    Emails won't be sent but can be inspected.
    """
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'


@pytest.fixture
def disable_cache(settings):
    """
    Disable cache for specific tests.

    Usage:
        @pytest.mark.usefixtures('disable_cache')
        def test_without_cache():
            ...
    """
    settings.CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }


@pytest.fixture
def aws_credentials(settings, monkeypatch):
    """Mock AWS credentials for S3 tests."""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    settings.AWS_S3_REGION_NAME = 'us-east-1'


# ============================================================================
# FIXTURES: Time/Date Helpers
# ============================================================================

@pytest.fixture
def freeze_time():
    """
    Freeze time for testing date-dependent logic.

    Usage:
        def test_vencimiento(freeze_time):
            with freeze_time('2025-01-01'):
                # Code that uses timezone.now()
    """
    from freezegun import freeze_time as _freeze_time
    return _freeze_time


@pytest.fixture
def today():
    """Current date for testing."""
    return timezone.now().date()


@pytest.fixture
def tomorrow():
    """Tomorrow's date for testing."""
    return timezone.now().date() + timedelta(days=1)


@pytest.fixture
def yesterday():
    """Yesterday's date for testing."""
    return timezone.now().date() - timedelta(days=1)


@pytest.fixture
def next_week():
    """Date one week from now."""
    return timezone.now().date() + timedelta(days=7)


@pytest.fixture
def last_month():
    """Date one month ago."""
    return timezone.now().date() - timedelta(days=30)


# ============================================================================
# FIXTURES: Email Testing
# ============================================================================

@pytest.fixture
def mailbox():
    """
    Access to sent emails during tests.

    Usage:
        def test_notification_email(mailbox):
            send_notification()
            assert len(mailbox) == 1
            assert 'Calibración' in mailbox[0].subject
    """
    from django.core import mail
    mail.outbox = []
    return mail.outbox


# ============================================================================
# FIXTURES: Database Helpers
# ============================================================================

@pytest.fixture
def clear_database(db):
    """
    Clear all test data from database.
    Use when you need a truly clean state.

    Usage:
        def test_with_clean_db(clear_database):
            # Start with completely empty database
            ...
    """
    from django.apps import apps

    # Get all models
    models = apps.get_models()

    # Delete all instances
    for model in models:
        model.objects.all().delete()


# ============================================================================
# PYTEST CONFIGURATION HOOKS
# ============================================================================

def pytest_configure(config):
    """Configure pytest before running tests."""
    # Set test mode environment variable
    os.environ['TESTING'] = 'True'

    # Configure Django settings for tests
    from django.conf import settings

    # Use faster password hasher for tests
    settings.PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]

    # Disable migrations for faster tests
    # Uncomment if tests are too slow:
    # settings.MIGRATION_MODULES = {
    #     'core': None,
    # }


def pytest_unconfigure(config):
    """Cleanup after all tests."""
    os.environ.pop('TESTING', None)


# ============================================================================
# CUSTOM MARKERS
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """
    Automatically add markers to tests based on location/name.
    """
    for item in items:
        # Add 'unit' marker to tests in test_models
        if "test_models" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
            item.add_marker(pytest.mark.models)

        # Add 'views' marker to tests in test_views
        if "test_views" in str(item.fspath):
            item.add_marker(pytest.mark.views)

        # Add 'services' marker to tests in test_services
        if "test_services" in str(item.fspath):
            item.add_marker(pytest.mark.services)

        # Add 'integration' marker to tests in test_integration
        if "test_integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
