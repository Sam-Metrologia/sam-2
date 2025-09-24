# core/tests.py
# Test suite básico para modelos críticos de SAM Metrología

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.urls import reverse
from datetime import date, timedelta
from decimal import Decimal

from .models import Empresa, Equipo, Calibracion, Mantenimiento, Comprobacion

User = get_user_model()


class EmpresaModelTest(TestCase):
    """Tests para el modelo Empresa"""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test",
            nit="123456789-0",
            email="test@empresa.com",
            limite_equipos_empresa=10,
            limite_almacenamiento_mb=1024
        )

    def test_empresa_creation(self):
        """Test de creación básica de empresa"""
        self.assertEqual(self.empresa.nombre, "Empresa Test")
        self.assertEqual(self.empresa.nit, "123456789-0")
        self.assertEqual(self.empresa.limite_equipos_empresa, 10)
        self.assertFalse(self.empresa.es_periodo_prueba)

    def test_get_limite_equipos_normal(self):
        """Test límite de equipos en estado normal"""
        limite = self.empresa.get_limite_equipos()
        self.assertEqual(limite, 10)

    def test_get_limite_equipos_acceso_manual(self):
        """Test límite infinito con acceso manual"""
        self.empresa.acceso_manual_activo = True
        self.empresa.save()
        limite = self.empresa.get_limite_equipos()
        self.assertEqual(limite, float('inf'))

    def test_get_limite_equipos_periodo_prueba(self):
        """Test límite en período de prueba"""
        self.empresa.es_periodo_prueba = True
        self.empresa.fecha_inicio_plan = timezone.now().date()
        self.empresa.save()
        limite = self.empresa.get_limite_equipos()
        self.assertEqual(limite, self.empresa.TRIAL_EQUIPOS)  # 50

    def test_empresa_str_representation(self):
        """Test representación string de empresa"""
        self.assertEqual(str(self.empresa), "Empresa Test")


class EquipoModelTest(TestCase):
    """Tests para el modelo Equipo"""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test",
            nit="123456789-0"
        )
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            empresa=self.empresa
        )
        self.equipo = Equipo.objects.create(
            codigo_interno="EQ001",
            nombre="Equipo Test",
            marca="Marca Test",
            modelo="Modelo Test",
            serie="12345",
            empresa=self.empresa,
            frecuencia_calibracion_meses=12,
            estado='Activo'
        )

    def test_equipo_creation(self):
        """Test de creación básica de equipo"""
        self.assertEqual(self.equipo.codigo_interno, "EQ001")
        self.assertEqual(self.equipo.nombre, "Equipo Test")
        self.assertEqual(self.equipo.empresa, self.empresa)
        self.assertEqual(self.equipo.estado, 'Activo')

    def test_calcular_proxima_calibracion_sin_historial(self):
        """Test cálculo de próxima calibración sin historial"""
        self.equipo.calcular_proxima_calibracion()
        # Sin calibraciones previas, debe ser None o basado en fecha de registro
        self.assertIsNone(self.equipo.proxima_calibracion)

    def test_calcular_proxima_calibracion_con_historial(self):
        """Test cálculo con historial de calibración"""
        fecha_cal = date.today() - timedelta(days=30)
        Calibracion.objects.create(
            equipo=self.equipo,
            fecha_calibracion=fecha_cal,
            resultado='Conforme',
            realizada_por=self.user
        )

        self.equipo.calcular_proxima_calibracion()
        # Debe calcular 12 meses después de la última calibración
        from dateutil.relativedelta import relativedelta
        expected_date = fecha_cal + relativedelta(months=12)
        self.assertEqual(self.equipo.proxima_calibracion, expected_date)

    def test_equipo_str_representation(self):
        """Test representación string de equipo"""
        expected = f"{self.equipo.codigo_interno} - {self.equipo.nombre}"
        self.assertEqual(str(self.equipo), expected)


class CalibracionModelTest(TestCase):
    """Tests para el modelo Calibracion"""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test",
            nit="123456789-0"
        )
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            empresa=self.empresa
        )
        self.equipo = Equipo.objects.create(
            codigo_interno="EQ001",
            nombre="Equipo Test",
            marca="Marca Test",
            modelo="Modelo Test",
            serie="12345",
            empresa=self.empresa,
            frecuencia_calibracion_meses=12,
            estado='Activo'
        )

    def test_calibracion_creation(self):
        """Test de creación básica de calibración"""
        calibracion = Calibracion.objects.create(
            equipo=self.equipo,
            fecha_calibracion=date.today(),
            resultado='Conforme',
            realizada_por=self.user
        )

        self.assertEqual(calibracion.equipo, self.equipo)
        self.assertEqual(calibracion.resultado, 'Conforme')
        self.assertEqual(calibracion.realizada_por, self.user)
        self.assertEqual(calibracion.fecha_calibracion, date.today())


class ViewsBasicTest(TestCase):
    """Tests básicos para views críticas"""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test",
            nit="123456789-0"
        )
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            empresa=self.empresa
        )
        self.client = Client()

    def test_login_view_get(self):
        """Test que la vista de login carga correctamente"""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_requires_login(self):
        """Test que el dashboard requiere autenticación"""
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_dashboard_authenticated_access(self):
        """Test acceso al dashboard autenticado"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_equipos_list_authenticated(self):
        """Test lista de equipos con usuario autenticado"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:equipos'))
        self.assertEqual(response.status_code, 200)


class ModelIntegrationTest(TestCase):
    """Tests de integración entre modelos"""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test",
            nit="123456789-0",
            limite_equipos_empresa=5
        )
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            empresa=self.empresa
        )

    def test_empresa_equipos_relationship(self):
        """Test relación empresa-equipos"""
        equipo1 = Equipo.objects.create(
            codigo_interno="EQ001",
            nombre="Equipo 1",
            marca="Test",
            modelo="Test",
            serie="12345",
            empresa=self.empresa,
            estado='Activo'
        )

        equipo2 = Equipo.objects.create(
            codigo_interno="EQ002",
            nombre="Equipo 2",
            marca="Test",
            modelo="Test",
            serie="54321",
            empresa=self.empresa,
            estado='Inactivo'
        )

        # Verificar relación inversa
        equipos = self.empresa.equipos.all()
        self.assertIn(equipo1, equipos)
        self.assertIn(equipo2, equipos)
        self.assertEqual(equipos.count(), 2)

        # Verificar filtrado por estado
        equipos_activos = self.empresa.equipos.filter(estado='Activo')
        self.assertEqual(equipos_activos.count(), 1)
        self.assertEqual(equipos_activos.first(), equipo1)


class PerformanceTest(TestCase):
    """Tests básicos de performance"""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test",
            nit="123456789-0"
        )
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            empresa=self.empresa
        )

    def test_bulk_equipment_creation(self):
        """Test creación en bulk de equipos para verificar performance"""
        equipos = []
        for i in range(20):
            equipos.append(Equipo(
                codigo_interno=f"EQ{i+1:03d}",
                nombre=f"Equipo {i+1}",
                marca="Test Brand",
                modelo="Test Model",
                serie=f"SN{i+1:05d}",
                empresa=self.empresa,
                estado='Activo',
                frecuencia_calibracion_meses=12
            ))

        # Usar bulk_create para performance
        Equipo.objects.bulk_create(equipos)

        # Verificar que se crearon correctamente
        self.assertEqual(self.empresa.equipos.count(), 20)

    def test_storage_calculation_performance(self):
        """Test básico de performance del cálculo de almacenamiento"""
        # Crear algunos equipos de prueba
        for i in range(5):
            Equipo.objects.create(
                codigo_interno=f"EQ{i+1:03d}",
                nombre=f"Equipo {i+1}",
                marca="Test",
                modelo="Test",
                serie=f"SN{i+1}",
                empresa=self.empresa,
                estado='Activo'
            )

        # Verificar que el método no falla
        storage = self.empresa.get_total_storage_used_mb()
        self.assertIsInstance(storage, (int, float))
        self.assertGreaterEqual(storage, 0)
