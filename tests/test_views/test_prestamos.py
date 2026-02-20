# tests/test_views/test_prestamos.py
# Tests para el sistema de préstamos de equipos

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from core.models import (
    Empresa, Equipo, PrestamoEquipo, AgrupacionPrestamo
)
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


class PrestamoEquipoModelTest(TestCase):
    """Tests para el modelo PrestamoEquipo"""

    def setUp(self):
        """Configuración inicial para los tests"""
        # Crear empresa de prueba
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test",
            nit="123456789",
            email="test@empresa.com",
            limite_equipos_empresa=10,
            limite_almacenamiento_mb=1000
        )

        # Crear usuario de prueba
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            empresa=self.empresa
        )

        # Crear equipo de prueba
        self.equipo = Equipo.objects.create(
            empresa=self.empresa,
            codigo_interno='TEST-001',
            nombre='Termómetro Test',
            estado='Activo'
        )

    def test_crear_prestamo(self):
        """Test: Crear un préstamo básico"""
        prestamo = PrestamoEquipo.objects.create(
            equipo=self.equipo,
            empresa=self.empresa,
            nombre_prestatario='Juan Pérez',
            cedula_prestatario='1234567890',
            cargo_prestatario='Técnico',
            email_prestatario='juan@empresa.com',
            telefono_prestatario='3001234567',
            fecha_devolucion_programada=date.today() + timedelta(days=7),
            estado_prestamo='ACTIVO',
            prestado_por=self.user
        )

        self.assertEqual(prestamo.nombre_prestatario, 'Juan Pérez')
        self.assertEqual(prestamo.estado_prestamo, 'ACTIVO')
        self.assertIsNone(prestamo.fecha_devolucion_real)

    def test_prestamo_esta_vencido(self):
        """Test: Detectar préstamo vencido"""
        # Crear préstamo con fecha de devolución en el pasado
        prestamo = PrestamoEquipo.objects.create(
            equipo=self.equipo,
            empresa=self.empresa,
            nombre_prestatario='María García',
            fecha_devolucion_programada=date.today() - timedelta(days=5),
            estado_prestamo='ACTIVO',
            prestado_por=self.user
        )

        self.assertTrue(prestamo.esta_vencido)

    def test_prestamo_no_vencido(self):
        """Test: Préstamo no vencido (fecha futura)"""
        prestamo = PrestamoEquipo.objects.create(
            equipo=self.equipo,
            empresa=self.empresa,
            nombre_prestatario='Pedro López',
            fecha_devolucion_programada=date.today() + timedelta(days=10),
            estado_prestamo='ACTIVO',
            prestado_por=self.user
        )

        self.assertFalse(prestamo.esta_vencido)

    def test_dias_en_prestamo(self):
        """Test: Calcular días en préstamo"""
        # Crear préstamo hace 3 días
        fecha_prestamo = timezone.now() - timedelta(days=3)
        prestamo = PrestamoEquipo.objects.create(
            equipo=self.equipo,
            empresa=self.empresa,
            nombre_prestatario='Ana Martínez',
            fecha_prestamo=fecha_prestamo,
            estado_prestamo='ACTIVO',
            prestado_por=self.user
        )

        # Debe ser aproximadamente 3 días (puede ser 2 o 3 dependiendo de la hora)
        self.assertGreaterEqual(prestamo.dias_en_prestamo, 2)
        self.assertLessEqual(prestamo.dias_en_prestamo, 4)

    def test_devolver_prestamo(self):
        """Test: Devolver un préstamo"""
        prestamo = PrestamoEquipo.objects.create(
            equipo=self.equipo,
            empresa=self.empresa,
            nombre_prestatario='Carlos Ruiz',
            estado_prestamo='ACTIVO',
            prestado_por=self.user
        )

        # Datos de verificación de entrada
        verificacion_entrada = {
            'fecha_verificacion': timezone.now().isoformat(),
            'verificado_por': 'Técnico Receptor',
            'resultado_general': 'Aprobado',
            'observaciones': 'Equipo en buen estado'
        }

        # Devolver el equipo
        prestamo.devolver(
            user=self.user,
            verificacion_entrada_datos=verificacion_entrada,
            observaciones='Devolución sin novedad'
        )

        # Verificar estado
        self.assertEqual(prestamo.estado_prestamo, 'DEVUELTO')
        self.assertIsNotNone(prestamo.fecha_devolucion_real)
        self.assertEqual(prestamo.recibido_por, self.user)


class AgrupacionPrestamoModelTest(TestCase):
    """Tests para el modelo AgrupacionPrestamo"""

    def setUp(self):
        """Configuración inicial"""
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test",
            nit="123456789",
            email="test@empresa.com"
        )

        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            empresa=self.empresa
        )

    def test_crear_agrupacion(self):
        """Test: Crear agrupación de préstamos"""
        agrupacion = AgrupacionPrestamo.objects.create(
            nombre='Set Termómetros',
            prestatario_nombre='Laura Sánchez',
            empresa=self.empresa
        )

        self.assertEqual(agrupacion.nombre, 'Set Termómetros')
        self.assertEqual(agrupacion.prestatario_nombre, 'Laura Sánchez')
        self.assertIsNotNone(agrupacion.fecha_creacion)


class PrestamoEquipoFormTest(TestCase):
    """Tests para los formularios de préstamos"""

    def setUp(self):
        """Configuración inicial"""
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test",
            nit="123456789",
            email="test@empresa.com"
        )

        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            empresa=self.empresa
        )

        self.equipo = Equipo.objects.create(
            empresa=self.empresa,
            codigo_interno='TEST-001',
            nombre='Equipo Test',
            estado='Activo'
        )

    def test_no_duplicar_prestamo_activo(self):
        """Test CRÍTICO: No permitir préstamo duplicado del mismo equipo"""
        from core.forms import PrestamoEquipoForm

        # Crear un préstamo activo
        PrestamoEquipo.objects.create(
            equipo=self.equipo,
            empresa=self.empresa,
            nombre_prestatario='Usuario 1',
            estado_prestamo='ACTIVO',
            prestado_por=self.user
        )

        # Intentar crear otro préstamo del mismo equipo
        form_data = {
            'equipo': self.equipo.id,
            'nombre_prestatario': 'Usuario 2',
            'fecha_devolucion_programada': date.today() + timedelta(days=7)
        }

        form = PrestamoEquipoForm(data=form_data)

        # El formulario NO debe ser válido
        self.assertFalse(form.is_valid())
        self.assertIn('equipo', form.errors)

    def test_permitir_prestamo_si_equipo_devuelto(self):
        """Test: Permitir préstamo si el equipo ya fue devuelto"""
        from core.forms import PrestamoEquipoForm

        # Crear un préstamo devuelto
        prestamo_anterior = PrestamoEquipo.objects.create(
            equipo=self.equipo,
            empresa=self.empresa,
            nombre_prestatario='Usuario 1',
            estado_prestamo='DEVUELTO',
            fecha_devolucion_real=timezone.now(),
            prestado_por=self.user
        )

        # Ahora debería permitir crear un nuevo préstamo
        form_data = {
            'equipo': self.equipo.id,
            'nombre_prestatario': 'Usuario 2',
            'fecha_devolucion_programada': date.today() + timedelta(days=7),
            # Campos de verificación requeridos
            'estado_fisico_salida': 'Bueno',
            'funcionalidad_salida': 'Conforme'
        }

        form = PrestamoEquipoForm(data=form_data, empresa=self.equipo.empresa)

        # El formulario DEBE ser válido
        self.assertTrue(form.is_valid())


class PrestamoViewsTest(TestCase):
    """Tests para las vistas del sistema de préstamos"""

    def setUp(self):
        """Configuración inicial"""
        # Crear empresas
        self.empresa1 = Empresa.objects.create(
            nombre="Empresa 1",
            nit="111111111",
            email="empresa1@test.com"
        )

        self.empresa2 = Empresa.objects.create(
            nombre="Empresa 2",
            nit="222222222",
            email="empresa2@test.com"
        )

        # Crear usuarios
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='pass123',
            empresa=self.empresa1
        )

        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='pass123',
            empresa=self.empresa2
        )

        # Asignar permisos
        content_type = ContentType.objects.get_for_model(PrestamoEquipo)
        permisos = Permission.objects.filter(content_type=content_type)

        self.user1.user_permissions.add(*permisos)
        self.user2.user_permissions.add(*permisos)

        # Crear equipos
        self.equipo1 = Equipo.objects.create(
            empresa=self.empresa1,
            codigo_interno='EMP1-001',
            nombre='Equipo Empresa 1',
            estado='Activo'
        )

        self.equipo2 = Equipo.objects.create(
            empresa=self.empresa2,
            codigo_interno='EMP2-001',
            nombre='Equipo Empresa 2',
            estado='Activo'
        )

        # Crear préstamos
        self.prestamo1 = PrestamoEquipo.objects.create(
            equipo=self.equipo1,
            empresa=self.empresa1,
            nombre_prestatario='Prestatario 1',
            estado_prestamo='ACTIVO',
            prestado_por=self.user1
        )

        self.prestamo2 = PrestamoEquipo.objects.create(
            equipo=self.equipo2,
            empresa=self.empresa2,
            nombre_prestatario='Prestatario 2',
            estado_prestamo='ACTIVO',
            prestado_por=self.user2
        )

        self.client = Client()

    def test_multi_tenant_listar_prestamos(self):
        """Test CRÍTICO: Usuario solo ve préstamos de su empresa"""
        # Login como user1
        self.client.login(username='user1', password='pass123')

        response = self.client.get(reverse('core:listar_prestamos'))

        # Debe ser exitoso
        self.assertEqual(response.status_code, 200)

        # Debe contener el préstamo de su empresa
        self.assertContains(response, 'EMP1-001')

        # NO debe contener el préstamo de la otra empresa
        self.assertNotContains(response, 'EMP2-001')

    def test_multi_tenant_detalle_prestamo(self):
        """Test CRÍTICO: Usuario no puede ver préstamo de otra empresa"""
        # Login como user1
        self.client.login(username='user1', password='pass123')

        # Intentar acceder al préstamo de empresa2
        response = self.client.get(
            reverse('core:detalle_prestamo', kwargs={'pk': self.prestamo2.pk})
        )

        # Debe retornar 404 o 403 (no encontrado o prohibido)
        self.assertIn(response.status_code, [404, 403])

    def test_acceso_dashboard_sin_permiso(self):
        """Test: Usuario sin permiso no puede acceder"""
        # Crear usuario sin permisos
        user_sin_permiso = User.objects.create_user(
            username='sinpermiso',
            email='sinpermiso@test.com',
            password='pass123',
            empresa=self.empresa1
        )

        self.client.login(username='sinpermiso', password='pass123')

        response = self.client.get(reverse('core:dashboard_prestamos'))

        # Debe redirigir o denegar acceso
        self.assertNotEqual(response.status_code, 200)

    def test_crear_prestamo_view(self):
        """Test: Crear préstamo desde la vista"""
        self.client.login(username='user1', password='pass123')

        # Crear nuevo equipo para el préstamo
        equipo_nuevo = Equipo.objects.create(
            empresa=self.empresa1,
            codigo_interno='EMP1-002',
            nombre='Equipo Nuevo',
            estado='Activo'
        )

        form_data = {
            'equipo': equipo_nuevo.id,
            'nombre_prestatario': 'Nuevo Prestatario',
            'cedula_prestatario': '9876543210',
            'cargo_prestatario': 'Ingeniero',
            'email_prestatario': 'nuevo@test.com',
            'telefono_prestatario': '3009876543',
            'fecha_devolucion_programada': (date.today() + timedelta(days=15)).strftime('%Y-%m-%d'),
            'observaciones_prestamo': 'Test de creación',
            # Campos de verificación de salida (requeridos)
            'estado_fisico_salida': 'Bueno',
            'funcionalidad_salida': 'Conforme'
        }

        response = self.client.post(reverse('core:crear_prestamo'), data=form_data)

        # Verificar que se creó
        self.assertTrue(
            PrestamoEquipo.objects.filter(
                equipo=equipo_nuevo,
                nombre_prestatario='Nuevo Prestatario'
            ).exists()
        )


class DashboardIntegrationTest(TestCase):
    """Tests para la integración del dashboard"""

    def setUp(self):
        """Configuración inicial"""
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test",
            nit="123456789",
            email="test@empresa.com"
        )

        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            empresa=self.empresa
        )

        # Asignar permisos
        content_type = ContentType.objects.get_for_model(PrestamoEquipo)
        permisos = Permission.objects.filter(content_type=content_type)
        self.user.user_permissions.add(*permisos)

        self.client = Client()

    def test_dashboard_muestra_estadisticas_prestamos(self):
        """Test: Dashboard muestra estadísticas de préstamos"""
        # Crear algunos préstamos
        equipo1 = Equipo.objects.create(
            empresa=self.empresa,
            codigo_interno='TEST-001',
            nombre='Equipo 1',
            estado='Activo'
        )

        PrestamoEquipo.objects.create(
            equipo=equipo1,
            empresa=self.empresa,
            nombre_prestatario='Prestatario Test',
            estado_prestamo='ACTIVO',
            prestado_por=self.user
        )

        self.client.login(username='testuser', password='testpass123')

        response = self.client.get(reverse('core:dashboard'))

        # Debe ser exitoso
        self.assertEqual(response.status_code, 200)

        # Debe contener las variables de contexto
        self.assertIn('total_prestamos_activos', response.context)

        # El contador debe ser 1
        self.assertEqual(response.context['total_prestamos_activos'], 1)

    def test_dashboard_sin_prestamos(self):
        """Test: Dashboard funciona sin préstamos"""
        self.client.login(username='testuser', password='testpass123')

        response = self.client.get(reverse('core:dashboard'))

        # Debe ser exitoso
        self.assertEqual(response.status_code, 200)

        # Las estadísticas deben ser 0
        self.assertEqual(response.context.get('total_prestamos_activos', 0), 0)
        self.assertEqual(response.context.get('prestamos_vencidos_count', 0), 0)
        self.assertEqual(response.context.get('devoluciones_proximas_count', 0), 0)


class RegressionTest(TestCase):
    """Test de regresión: Verificar que el sistema existente sigue funcionando"""

    def setUp(self):
        """Configuración básica"""
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test",
            nit="123456789",
            email="test@empresa.com"
        )

        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            empresa=self.empresa
        )

        self.client = Client()

    def test_equipo_model_sin_cambios(self):
        """Test: Modelo Equipo no fue modificado"""
        equipo = Equipo.objects.create(
            empresa=self.empresa,
            codigo_interno='REG-001',
            nombre='Equipo Regresión',
            estado='Activo'
        )

        # Verificar que los estados originales funcionan
        self.assertIn(equipo.estado, ['Activo', 'Inactivo', 'De Baja',
                                       'En Calibración', 'En Mantenimiento',
                                       'En Reparación'])

    def test_dashboard_funciona_sin_prestamos(self):
        """Test: Dashboard funciona correctamente sin módulo de préstamos"""
        self.client.login(username='testuser', password='testpass123')

        response = self.client.get(reverse('core:dashboard'))

        # El dashboard debe cargar correctamente
        self.assertEqual(response.status_code, 200)

        # Debe contener las métricas tradicionales
        self.assertIn('total_equipos', response.context)
        self.assertIn('equipos_activos', response.context)
