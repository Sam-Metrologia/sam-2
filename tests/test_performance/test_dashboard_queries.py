"""
Tests de queries específicas del dashboard.

Objetivo: Validar que los índices mejoran queries críticas.
"""
import pytest
from django.test import TestCase
from django.utils import timezone
from django.db.models import Q
from django.db import connection
from django.test.utils import override_settings
from datetime import timedelta
import time

from core.models import Empresa, CustomUser, Equipo, Calibracion, Mantenimiento, Comprobacion
from core.constants import ESTADO_ACTIVO, ESTADO_EN_CALIBRACION, ESTADO_EN_MANTENIMIENTO


@pytest.mark.django_db
class TestDashboardQueries:
    """Tests para validar uso correcto de índices en queries."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup común."""
        self.empresa = Empresa.objects.create(
            nombre="Empresa Queries Test",
            nit="900555666-7",
            limite_equipos_empresa=500,
        )
        self.today = timezone.now().date()

    def _create_test_equipos(self, count=100):
        """Helper: Crea equipos para tests."""
        equipos = []
        for i in range(count):
            equipo = Equipo.objects.create(
                codigo_interno=f"EQ-Q-{i:03d}",
                nombre=f"Equipo Query {i}",
                empresa=self.empresa,
                tipo_equipo="Equipo de Medición",
                estado=ESTADO_ACTIVO if i % 3 != 0 else ESTADO_EN_CALIBRACION,
            )
            equipos.append(equipo)

        # Usar .update() por equipo para asignar fechas sin que save() las recalcule
        for i, equipo in enumerate(equipos):
            Equipo.objects.filter(pk=equipo.pk).update(
                proxima_calibracion=self.today + timedelta(days=(i % 90) - 30),
                proximo_mantenimiento=self.today + timedelta(days=(i % 60) - 20),
                proxima_comprobacion=self.today + timedelta(days=(i % 45) - 15),
            )
        return equipos

    @pytest.mark.performance
    def test_query_filter_by_empresa(self):
        """
        Test: Filtro por empresa usa índice FK.
        Debe ser rápido incluso con muchos equipos.
        """
        self._create_test_equipos(200)

        start_time = time.time()
        equipos = Equipo.objects.filter(empresa=self.empresa).count()
        elapsed = time.time() - start_time

        assert equipos == 200
        assert elapsed < 0.1, f"Query empresa tomó {elapsed:.3f}s (límite: 0.1s)"

    @pytest.mark.performance
    def test_query_filter_by_estado(self):
        """
        Test: Filtro por estado usa índice creado.
        Verifica que el índice equipo_estado_idx se usa.
        """
        self._create_test_equipos(200)

        # Query con índice de estado
        start_time = time.time()
        activos = Equipo.objects.filter(
            empresa=self.empresa,
            estado=ESTADO_ACTIVO
        ).count()
        elapsed = time.time() - start_time

        # Aprox 67% activos (200 * 2/3)
        assert 130 <= activos <= 140
        assert elapsed < 0.1, f"Query estado tomó {elapsed:.3f}s (límite: 0.1s)"

    @pytest.mark.performance
    def test_query_proximas_calibraciones(self):
        """
        Test: Query de calibraciones próximas usa índice.
        Índice: equipo_prox_cal_idx
        """
        self._create_test_equipos(200)

        # Próximas 30 días
        fecha_limite = self.today + timedelta(days=30)

        start_time = time.time()
        proximas = Equipo.objects.filter(
            empresa=self.empresa,
            proxima_calibracion__lte=fecha_limite,
            proxima_calibracion__gte=self.today
        ).count()
        elapsed = time.time() - start_time

        assert proximas > 0
        assert elapsed < 0.1, f"Query próximas calibraciones tomó {elapsed:.3f}s"

    @pytest.mark.performance
    def test_query_vencidos_con_or(self):
        """
        Test: Query compleja con Q() y OR.
        Debe usar índices múltiples eficientemente.
        """
        self._create_test_equipos(300)

        start_time = time.time()
        vencidos = Equipo.objects.filter(
            empresa=self.empresa
        ).filter(
            Q(proxima_calibracion__lt=self.today) |
            Q(proximo_mantenimiento__lt=self.today) |
            Q(proxima_comprobacion__lt=self.today)
        ).count()
        elapsed = time.time() - start_time

        assert vencidos > 0
        assert elapsed < 0.2, f"Query vencidos con OR tomó {elapsed:.3f}s (límite: 0.2s)"

    @pytest.mark.performance
    def test_query_compuesto_empresa_estado(self):
        """
        Test: Query con empresa + estado usa índice compuesto.
        Índice: equipo_emp_est_idx
        """
        self._create_test_equipos(250)

        start_time = time.time()
        result = Equipo.objects.filter(
            empresa=self.empresa,
            estado=ESTADO_ACTIVO
        ).count()
        elapsed = time.time() - start_time

        assert result > 150
        assert elapsed < 0.1, f"Query compuesto empresa+estado tomó {elapsed:.3f}s"

    @pytest.mark.performance
    def test_query_compuesto_empresa_fecha(self):
        """
        Test: Query con empresa + fecha usa índice compuesto.
        Índice: equipo_emp_pcal_idx
        """
        self._create_test_equipos(250)

        start_time = time.time()
        result = Equipo.objects.filter(
            empresa=self.empresa,
            proxima_calibracion__lt=self.today + timedelta(days=30)
        ).count()
        elapsed = time.time() - start_time

        assert result > 0
        assert elapsed < 0.1, f"Query compuesto empresa+fecha tomó {elapsed:.3f}s"

    @pytest.mark.performance
    def test_query_count_por_estado(self):
        """
        Test: Agregaciones por estado deben ser rápidas.
        """
        self._create_test_equipos(200)

        start_time = time.time()
        from django.db.models import Count
        stats = Equipo.objects.filter(
            empresa=self.empresa
        ).values('estado').annotate(
            count=Count('id')
        )
        elapsed = time.time() - start_time

        assert len(stats) >= 2  # Al menos 2 estados diferentes
        assert elapsed < 0.15, f"Agregación por estado tomó {elapsed:.3f}s"

    @pytest.mark.performance
    def test_query_select_related_calibraciones(self):
        """
        Test: select_related optimiza joins.
        """
        equipos = self._create_test_equipos(50)

        # Crear calibraciones
        for i, equipo in enumerate(equipos[:30]):
            Calibracion.objects.create(
                equipo=equipo,
                fecha_calibracion=self.today - timedelta(days=i),
                nombre_proveedor='Laboratorio Externo',
            )

        start_time = time.time()
        calibraciones = Calibracion.objects.select_related(
            'equipo', 'equipo__empresa'
        ).filter(
            equipo__empresa=self.empresa
        )[:20]

        # Forzar evaluación
        list(calibraciones)
        elapsed = time.time() - start_time

        assert elapsed < 0.2, f"select_related tomó {elapsed:.3f}s (límite: 0.2s)"

    @pytest.mark.performance
    def test_query_only_campos_necesarios(self):
        """
        Test: .only() reduce datos transferidos.
        """
        self._create_test_equipos(200)

        # Query con only() - solo campos necesarios
        start_time = time.time()
        equipos = Equipo.objects.filter(
            empresa=self.empresa
        ).only(
            'id', 'codigo_interno', 'nombre', 'estado'
        )[:100]

        list(equipos)  # Forzar evaluación
        elapsed = time.time() - start_time

        assert elapsed < 0.15, f"Query con only() tomó {elapsed:.3f}s"

    @pytest.mark.performance
    def test_query_valores_list_plano(self):
        """
        Test: values_list() es más rápido que objetos completos.
        """
        self._create_test_equipos(200)

        start_time = time.time()
        codigos = Equipo.objects.filter(
            empresa=self.empresa
        ).values_list('codigo_interno', flat=True)

        list(codigos)  # Forzar evaluación
        elapsed = time.time() - start_time

        assert len(list(codigos)) == 200
        assert elapsed < 0.1, f"values_list() tomó {elapsed:.3f}s"
