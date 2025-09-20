# core/tests/test_models.py
# Tests básicos para modelos críticos

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from decimal import Decimal
from core.models import Empresa, Equipo, Calibracion, Mantenimiento, Comprobacion

User = get_user_model()


class EmpresaModelTest(TestCase):
    """Tests para el modelo Empresa y funciones de almacenamiento."""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test",
            nit="123456789",
            limite_equipos_empresa=10,
            limite_almacenamiento_mb=100
        )

    def test_empresa_creation(self):
        """Test creación básica de empresa."""
        self.assertEqual(self.empresa.nombre, "Empresa Test")
        self.assertEqual(self.empresa.limite_equipos_empresa, 10)
        self.assertEqual(self.empresa.limite_almacenamiento_mb, 100)

    def test_get_limite_equipos(self):
        """Test cálculo de límite de equipos."""
        # Empresa normal
        self.assertEqual(self.empresa.get_limite_equipos(), 10)

        # Empresa con acceso manual
        self.empresa.acceso_manual_activo = True
        self.assertEqual(self.empresa.get_limite_equipos(), float('inf'))

    def test_storage_calculation_empty(self):
        """Test cálculo de almacenamiento con empresa vacía."""
        usage = self.empresa.get_total_storage_used_mb()
        self.assertEqual(usage, 0.0)

        percentage = self.empresa.get_storage_usage_percentage()
        self.assertEqual(percentage, 0.0)

    def test_storage_status_classes(self):
        """Test clases CSS de estado de almacenamiento."""
        # Mock del método get_storage_usage_percentage
        original_method = self.empresa.get_storage_usage_percentage

        # Test 90%+ = rojo
        self.empresa.get_storage_usage_percentage = lambda: 95.0
        self.assertIn('text-red-700', self.empresa.get_storage_status_class())

        # Test 75%+ = amarillo
        self.empresa.get_storage_usage_percentage = lambda: 80.0
        self.assertIn('text-yellow-700', self.empresa.get_storage_status_class())

        # Test 50%+ = naranja
        self.empresa.get_storage_usage_percentage = lambda: 60.0
        self.assertIn('text-orange-700', self.empresa.get_storage_status_class())

        # Test <50% = verde
        self.empresa.get_storage_usage_percentage = lambda: 30.0
        self.assertIn('text-green-700', self.empresa.get_storage_status_class())

        # Restore original method
        self.empresa.get_storage_usage_percentage = original_method


class CustomUserModelTest(TestCase):
    """Tests para el modelo CustomUser."""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test User",
            nit="987654321"
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            empresa=self.empresa
        )

    def test_user_creation(self):
        """Test creación de usuario con empresa."""
        self.assertEqual(self.user.username, "testuser")
        self.assertEqual(self.user.empresa, self.empresa)

    def test_has_export_permission_false(self):
        """Test permiso de exportación cuando no lo tiene."""
        self.assertFalse(self.user.has_export_permission)

    def test_has_export_permission_true(self):
        """Test permiso de exportación cuando sí lo tiene."""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        # Crear el permiso si no existe
        content_type = ContentType.objects.get_for_model(Equipo)
        permission, created = Permission.objects.get_or_create(
            codename='can_export_reports',
            content_type=content_type,
            defaults={'name': 'Can export reports'}
        )

        # Asignar permiso al usuario
        self.user.user_permissions.add(permission)

        # Verificar que tiene el permiso
        self.assertTrue(self.user.has_export_permission)


class EquipoModelTest(TestCase):
    """Tests para el modelo Equipo."""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test Equipo",
            nit="555666777"
        )
        self.equipo = Equipo.objects.create(
            codigo_interno="EQ001",
            nombre="Equipo Test",
            empresa=self.empresa,
            tipo_equipo="Equipo de Medición",
            marca="Test Brand",
            modelo="Test Model"
        )

    def test_equipo_creation(self):
        """Test creación básica de equipo."""
        self.assertEqual(self.equipo.codigo_interno, "EQ001")
        self.assertEqual(self.equipo.empresa, self.empresa)
        self.assertEqual(self.equipo.estado, "Activo")  # Estado por defecto

    def test_equipo_str(self):
        """Test representación string del equipo."""
        expected = f"{self.equipo.codigo_interno} - {self.equipo.nombre}"
        self.assertEqual(str(self.equipo), expected)

    def test_relaciones_actividades(self):
        """Test relaciones con actividades (calibraciones, etc)."""
        # Crear actividades relacionadas
        calibracion = Calibracion.objects.create(
            equipo=self.equipo,
            fecha_calibracion="2023-01-15",
            resultado="Aprobado"
        )

        mantenimiento = Mantenimiento.objects.create(
            equipo=self.equipo,
            fecha_mantenimiento="2023-02-15",
            tipo_mantenimiento="Preventivo"
        )

        comprobacion = Comprobacion.objects.create(
            equipo=self.equipo,
            fecha_comprobacion="2023-03-15",
            resultado="Aprobado"
        )

        # Verificar relaciones inversas
        self.assertEqual(self.equipo.calibraciones.count(), 1)
        self.assertEqual(self.equipo.mantenimientos.count(), 1)
        self.assertEqual(self.equipo.comprobaciones.count(), 1)

        # Verificar objetos específicos
        self.assertEqual(self.equipo.calibraciones.first(), calibracion)
        self.assertEqual(self.equipo.mantenimientos.first(), mantenimiento)
        self.assertEqual(self.equipo.comprobaciones.first(), comprobacion)


class ValidationServiceTest(TestCase):
    """Tests para servicios de validación críticos."""

    def setUp(self):
        self.empresa1 = Empresa.objects.create(
            nombre="Empresa 1",
            nit="111111111"
        )
        self.empresa2 = Empresa.objects.create(
            nombre="Empresa 2",
            nit="222222222"
        )

    def test_codigo_interno_unique_per_company(self):
        """Test que el código interno sea único por empresa."""
        # Crear equipo en empresa 1
        equipo1 = Equipo.objects.create(
            codigo_interno="TEST001",
            nombre="Equipo 1",
            empresa=self.empresa1,
            tipo_equipo="Equipo de Medición"
        )

        # Debe poder crear equipo con mismo código en empresa 2
        equipo2 = Equipo.objects.create(
            codigo_interno="TEST001",
            nombre="Equipo 2",
            empresa=self.empresa2,
            tipo_equipo="Equipo de Medición"
        )

        self.assertEqual(equipo1.codigo_interno, equipo2.codigo_interno)
        self.assertNotEqual(equipo1.empresa, equipo2.empresa)

    def test_limite_equipos_validation(self):
        """Test validación de límite de equipos por empresa."""
        # Configurar límite de 2 equipos
        self.empresa1.limite_equipos_empresa = 2
        self.empresa1.save()

        # Crear 2 equipos (dentro del límite)
        for i in range(2):
            Equipo.objects.create(
                codigo_interno=f"LIM{i:03d}",
                nombre=f"Equipo Límite {i}",
                empresa=self.empresa1,
                tipo_equipo="Equipo de Medición"
            )

        # Verificar que se crearon correctamente
        equipos_count = Equipo.objects.filter(empresa=self.empresa1).count()
        self.assertEqual(equipos_count, 2)

        # Verificar que alcanzó el límite
        limite = self.empresa1.get_limite_equipos()
        self.assertEqual(equipos_count, limite)