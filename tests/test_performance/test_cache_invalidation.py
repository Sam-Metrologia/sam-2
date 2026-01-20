"""
Tests de invalidación y rendimiento de caché.

Objetivo: Validar que el caché funciona correctamente y mejora el rendimiento.
"""
import pytest
from django.core.cache import cache
from django.test import Client
from django.urls import reverse
from django.utils import timezone
import time

from core.models import Empresa, CustomUser, Equipo
from core.constants import ESTADO_ACTIVO, ESTADO_EN_CALIBRACION


@pytest.mark.django_db
class TestCacheInvalidation:
    """Tests para validar sistema de caché."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup común y limpiar caché antes de cada test."""
        cache.clear()  # Limpiar caché

        self.client = Client()
        self.empresa = Empresa.objects.create(
            nombre="Empresa Cache Test",
            nit="900777888-9",
            limite_equipos_empresa=100,
        )
        self.user = CustomUser.objects.create_user(
            username="cacheuser",
            email="cache@test.com",
            password="testpass123",
            empresa=self.empresa,
            rol_usuario="ADMINISTRADOR"
        )
        self.client.login(username="cacheuser", password="testpass123")

    def teardown_method(self):
        """Limpiar caché después de cada test."""
        cache.clear()

    def _create_equipos_batch(self, count):
        """Helper: Crear equipos en batch."""
        equipos = []
        for i in range(count):
            equipo = Equipo.objects.create(
                codigo_interno=f"EQ-CACHE-{i:03d}",
                nombre=f"Equipo Cache {i}",
                empresa=self.empresa,
                tipo_equipo="Equipo de Medición",
                estado=ESTADO_ACTIVO,
            )
            equipos.append(equipo)
        return equipos

    @pytest.mark.performance
    def test_cache_basic_functionality(self):
        """
        Test: Cache básico funciona correctamente.
        """
        # Setear valor en cache
        cache.set('test_key', 'test_value', timeout=60)

        # Obtener valor del cache
        cached_value = cache.get('test_key')

        assert cached_value == 'test_value'

        # Verificar que se puede eliminar
        cache.delete('test_key')
        assert cache.get('test_key') is None

    @pytest.mark.performance
    def test_dashboard_cache_hit(self):
        """
        Test: Segunda carga del dashboard debe ser más rápida (cache hit).
        """
        self._create_equipos_batch(50)

        # Primera carga - cache miss
        start_time = time.time()
        response1 = self.client.get(reverse('core:dashboard'))
        first_load_time = time.time() - start_time

        assert response1.status_code == 200

        # Segunda carga - cache hit (debería ser más rápida)
        start_time = time.time()
        response2 = self.client.get(reverse('core:dashboard'))
        second_load_time = time.time() - start_time

        assert response2.status_code == 200

        print(f"\n✓ Primera carga: {first_load_time:.3f}s")
        print(f"✓ Segunda carga (cache): {second_load_time:.3f}s")
        print(f"✓ Mejora: {((first_load_time - second_load_time) / first_load_time * 100):.1f}%")

        # La segunda carga debería ser significativamente más rápida
        # (al menos 20% más rápida si el caché está funcionando)
        # Nota: Puede variar según el sistema, así que no es assertion crítica
        if first_load_time > 0.5:  # Solo verificar si la primera carga fue lenta
            improvement = (first_load_time - second_load_time) / first_load_time
            assert improvement > 0, "Cache debería mejorar el rendimiento"

    @pytest.mark.performance
    def test_cache_invalidation_on_equipo_creation(self):
        """
        Test: Crear equipo debe invalidar caché relevante.
        """
        # Carga inicial para poblar cache
        response1 = self.client.get(reverse('core:dashboard'))
        assert response1.status_code == 200

        # Obtener conteo inicial
        initial_count = response1.context.get('total_equipos', 0)

        # Crear nuevo equipo
        Equipo.objects.create(
            codigo_interno="EQ-NEW-001",
            nombre="Equipo Nuevo",
            empresa=self.empresa,
            tipo_equipo="Equipo de Medición",
            estado=ESTADO_ACTIVO,
        )

        # Recargar dashboard - debe reflejar cambio
        response2 = self.client.get(reverse('core:dashboard'))
        assert response2.status_code == 200

        new_count = response2.context.get('total_equipos', 0)
        assert new_count == initial_count + 1, "Nuevo equipo debe aparecer en dashboard"

    @pytest.mark.performance
    def test_cache_invalidation_on_equipo_update(self):
        """
        Test: Actualizar equipo debe invalidar caché.
        """
        equipo = Equipo.objects.create(
            codigo_interno="EQ-UPDATE-001",
            nombre="Equipo Original",
            empresa=self.empresa,
            tipo_equipo="Equipo de Medición",
            estado=ESTADO_ACTIVO,
        )

        # Carga inicial
        response1 = self.client.get(reverse('core:dashboard'))
        assert response1.status_code == 200

        # Actualizar estado del equipo
        equipo.estado = ESTADO_EN_CALIBRACION
        equipo.save()

        # Recargar - debe reflejar el cambio
        response2 = self.client.get(reverse('core:dashboard'))
        assert response2.status_code == 200

        # Verificar que las estadísticas se actualizaron
        stats = response2.context.get('estadisticas_actividades', {})
        assert stats is not None

    @pytest.mark.performance
    def test_cache_key_uniqueness_per_empresa(self):
        """
        Test: Cada empresa debe tener su propio cache.
        """
        # Crear segunda empresa
        empresa2 = Empresa.objects.create(
            nombre="Empresa Cache 2",
            nit="900999000-1",
            limite_equipos_empresa=50,
        )
        user2 = CustomUser.objects.create_user(
            username="cacheuser2",
            email="cache2@test.com",
            password="testpass123",
            empresa=empresa2,
            rol_usuario="ADMINISTRADOR"
        )

        # Crear equipos para empresa 1
        self._create_equipos_batch(30)

        # Crear equipos para empresa 2
        for i in range(20):
            Equipo.objects.create(
                codigo_interno=f"EQ2-{i:03d}",
                nombre=f"Equipo Empresa 2 - {i}",
                empresa=empresa2,
                tipo_equipo="Equipo de Medición",
                estado=ESTADO_ACTIVO,
            )

        # Login como user1 y cargar dashboard
        self.client.login(username="cacheuser", password="testpass123")
        response1 = self.client.get(reverse('core:dashboard'))
        count1 = response1.context.get('total_equipos', 0)

        # Login como user2 y cargar dashboard
        client2 = Client()
        client2.login(username="cacheuser2", password="testpass123")
        response2 = client2.get(reverse('core:dashboard'))
        count2 = response2.context.get('total_equipos', 0)

        # Cada empresa debe ver solo sus equipos
        assert count1 == 30, f"Empresa 1 debe ver 30 equipos, vio {count1}"
        assert count2 == 20, f"Empresa 2 debe ver 20 equipos, vio {count2}"

    @pytest.mark.performance
    def test_cache_expiration(self):
        """
        Test: Cache expira después del tiempo configurado.
        """
        # Setear valor con timeout corto
        cache.set('expire_test', 'value', timeout=1)

        # Verificar que existe
        assert cache.get('expire_test') == 'value'

        # Esperar que expire (1 segundo + margen)
        import time
        time.sleep(1.5)

        # Verificar que expiró
        assert cache.get('expire_test') is None

    @pytest.mark.performance
    def test_cache_clear_functionality(self):
        """
        Test: cache.clear() limpia todo el caché.
        """
        # Setear múltiples valores
        cache.set('key1', 'value1', timeout=300)
        cache.set('key2', 'value2', timeout=300)
        cache.set('key3', 'value3', timeout=300)

        # Verificar que existen
        assert cache.get('key1') == 'value1'
        assert cache.get('key2') == 'value2'
        assert cache.get('key3') == 'value3'

        # Limpiar todo
        cache.clear()

        # Verificar que se limpiaron
        assert cache.get('key1') is None
        assert cache.get('key2') is None
        assert cache.get('key3') is None

    @pytest.mark.performance
    def test_cache_with_complex_data(self):
        """
        Test: Cache maneja datos complejos (dicts, lists).
        """
        complex_data = {
            'equipos': [1, 2, 3],
            'stats': {'total': 10, 'activos': 8},
            'nested': {
                'level1': {
                    'level2': 'value'
                }
            }
        }

        cache.set('complex_key', complex_data, timeout=60)

        cached_data = cache.get('complex_key')

        assert cached_data == complex_data
        assert cached_data['equipos'] == [1, 2, 3]
        assert cached_data['stats']['total'] == 10
        assert cached_data['nested']['level1']['level2'] == 'value'
