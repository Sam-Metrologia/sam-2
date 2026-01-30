"""
Tests de rendimiento para dashboard.

Objetivo: Medir impacto de índices BD en queries del dashboard.
Benchmarks con 100, 200, 500 equipos.
"""
import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import time

from core.models import Empresa, CustomUser, Equipo
from core.constants import ESTADO_ACTIVO, ESTADO_EN_CALIBRACION


@pytest.mark.django_db
class TestDashboardPerformance:
    """Tests de rendimiento del dashboard con diferentes cargas."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup común para todos los tests."""
        self.client = Client()
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test Performance",
            nit="900123456-7",
            limite_equipos_empresa=1000,  # Suficiente para benchmarks
        )
        self.user = CustomUser.objects.create_user(
            username="perfuser",
            email="perf@test.com",
            password="testpass123",
            empresa=self.empresa,
            rol_usuario="ADMINISTRADOR"
        )
        self.client.login(username="perfuser", password="testpass123")

    def _create_equipos_batch(self, count, with_dates=True):
        """
        Helper: Crea equipos en batch para benchmarks.

        Args:
            count: Número de equipos a crear
            with_dates: Si incluir fechas de calibración/mantenimiento

        Returns:
            list: Lista de equipos creados
        """
        equipos = []
        today = timezone.now().date()

        for i in range(count):
            equipo = Equipo.objects.create(
                codigo_interno=f"EQ-PERF-{i:04d}",
                nombre=f"Equipo Performance {i}",
                empresa=self.empresa,
                tipo_equipo="Equipo de Medición",
                estado=ESTADO_ACTIVO if i % 10 != 0 else ESTADO_EN_CALIBRACION,
                marca="Test Brand",
                modelo=f"Model-{i % 5}",
            )

            if with_dates:
                # 20% vencidos, 30% próximos, 50% al día
                if i % 5 == 0:  # 20% vencidos
                    equipo.proxima_calibracion = today - timedelta(days=30)
                    equipo.proximo_mantenimiento = today - timedelta(days=15)
                elif i % 5 == 1:  # 30% próximos (dentro de 30 días)
                    equipo.proxima_calibracion = today + timedelta(days=15)
                    equipo.proximo_mantenimiento = today + timedelta(days=20)
                else:  # 50% al día
                    equipo.proxima_calibracion = today + timedelta(days=90)
                    equipo.proximo_mantenimiento = today + timedelta(days=60)

                equipo.save()

            equipos.append(equipo)

        return equipos

    @pytest.mark.performance
    def test_dashboard_with_100_equipos(self):
        """
        Benchmark: Dashboard con 100 equipos.
        Límite aceptable: < 2 segundos.
        """
        # Crear 100 equipos
        self._create_equipos_batch(100)

        # Medir tiempo de carga del dashboard
        start_time = time.time()
        response = self.client.get(reverse('core:dashboard'))
        elapsed = time.time() - start_time

        assert response.status_code == 200
        assert elapsed < 2.0, f"Dashboard con 100 equipos tomó {elapsed:.2f}s (límite: 2s)"

        print(f"\n✓ Dashboard (100 equipos): {elapsed:.3f}s")

    @pytest.mark.performance
    def test_dashboard_with_200_equipos(self):
        """
        Benchmark: Dashboard con 200 equipos.
        Límite aceptable: < 3 segundos.
        """
        # Crear 200 equipos
        self._create_equipos_batch(200)

        # Medir tiempo de carga del dashboard
        start_time = time.time()
        response = self.client.get(reverse('core:dashboard'))
        elapsed = time.time() - start_time

        assert response.status_code == 200
        assert elapsed < 3.0, f"Dashboard con 200 equipos tomó {elapsed:.2f}s (límite: 3s)"

        print(f"\n✓ Dashboard (200 equipos): {elapsed:.3f}s")

    @pytest.mark.performance
    def test_dashboard_with_500_equipos(self):
        """
        Benchmark: Dashboard con 500 equipos.
        Límite aceptable: < 5 segundos.
        """
        # Crear 500 equipos
        self._create_equipos_batch(500)

        # Medir tiempo de carga del dashboard
        start_time = time.time()
        response = self.client.get(reverse('core:dashboard'))
        elapsed = time.time() - start_time

        assert response.status_code == 200
        assert elapsed < 5.0, f"Dashboard con 500 equipos tomó {elapsed:.2f}s (límite: 5s)"

        print(f"\n✓ Dashboard (500 equipos): {elapsed:.3f}s")

    @pytest.mark.performance
    def test_dashboard_estadisticas_actividades(self):
        """
        Test: Rendimiento del bloque de estadísticas de actividades.
        Límite: < 1 segundo con 200 equipos.
        """
        # Crear 200 equipos con fechas variadas
        self._create_equipos_batch(200, with_dates=True)

        # Medir tiempo del dashboard (incluye estadísticas)
        start_time = time.time()
        response = self.client.get(reverse('core:dashboard'))
        elapsed = time.time() - start_time

        assert response.status_code == 200
        assert elapsed < 2.0, f"Estadísticas con 200 equipos tomó {elapsed:.2f}s"

        # Verificar que las estadísticas de actividades están en el contexto
        assert 'calibraciones_vencidas' in response.context
        assert 'mantenimientos_vencidos' in response.context
        assert 'comprobaciones_vencidas' in response.context

        print(f"\n✓ Estadísticas actividades (200 equipos): {elapsed:.3f}s")

    @pytest.mark.performance
    def test_dashboard_filtro_empresa(self):
        """
        Test: Rendimiento con filtro de empresa aplicado.
        Límite: < 1.5 segundos con 300 equipos.
        """
        # Crear 300 equipos
        self._create_equipos_batch(300)

        # Medir tiempo con filtro de empresa
        start_time = time.time()
        response = self.client.get(reverse('core:dashboard'), {'empresa_id': self.empresa.id})
        elapsed = time.time() - start_time

        assert response.status_code == 200
        assert elapsed < 1.5, f"Dashboard filtrado tomó {elapsed:.2f}s (límite: 1.5s)"

        print(f"\n✓ Dashboard filtrado (300 equipos): {elapsed:.3f}s")

    @pytest.mark.performance
    def test_equipos_vencidos_query_performance(self):
        """
        Test: Query de equipos vencidos con índices.
        Límite: < 0.5 segundos con 400 equipos.
        """
        today = timezone.now().date()

        # Crear 400 equipos, 25% vencidos
        equipos = self._create_equipos_batch(400, with_dates=False)
        # Usar .update() para evitar que save() recalcule las fechas
        vencido_ids = [equipos[i].pk for i in range(0, len(equipos), 4)]
        Equipo.objects.filter(pk__in=vencido_ids).update(
            proxima_calibracion=today - timedelta(days=10)
        )

        # Medir query de vencidos
        start_time = time.time()
        from django.db.models import Q
        vencidos = Equipo.objects.filter(
            empresa=self.empresa
        ).filter(
            Q(proxima_calibracion__lt=today) |
            Q(proximo_mantenimiento__lt=today) |
            Q(proxima_comprobacion__lt=today)
        ).count()
        elapsed = time.time() - start_time

        assert vencidos == 100  # 25% de 400
        assert elapsed < 0.5, f"Query vencidos tomó {elapsed:.3f}s (límite: 0.5s)"

        print(f"\n✓ Query equipos vencidos (400 equipos): {elapsed:.3f}s - {vencidos} resultados")
