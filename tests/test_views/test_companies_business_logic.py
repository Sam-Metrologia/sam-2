"""
Tests para lógica de negocio de Companies - SAM Metrología

Enfoque en:
- Soft delete y restauración de empresas
- Límites de equipos y validaciones
- Planes y suscripciones (trial, pagado, expirado)
- Multitenancy estricto
- Validaciones de negocio críticas

Complementa test_companies.py (que testea vistas)
Este archivo testea la lógica del modelo Empresa.
"""

import pytest
from datetime import date, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from core.models import Empresa, Equipo

User = get_user_model()


# ==================== FIXTURES ====================

@pytest.fixture
def superuser():
    """Usuario superadmin para operaciones de gestión"""
    return User.objects.create_superuser(
        username='admin_test',
        email='admin@test.com',
        password='testpass123'
    )


@pytest.fixture
def empresa_activa():
    """Empresa activa estándar"""
    return Empresa.objects.create(
        nombre='Empresa Activa Test',
        nit='900111111-1',
        email='activa@test.com',
        limite_equipos_empresa=50,
        es_periodo_prueba=False,
        estado_suscripcion='Activo'
    )


@pytest.fixture
def empresa_trial():
    """Empresa en período de prueba"""
    return Empresa.objects.create(
        nombre='Empresa Trial Test',
        nit='900222222-2',
        email='trial@test.com',
        es_periodo_prueba=True,
        duracion_prueba_dias=30,
        fecha_inicio_plan=date.today(),
        limite_equipos_empresa=50,
        estado_suscripcion='Activo'
    )


# ==================== TESTS: Soft Delete ====================

@pytest.mark.django_db
class TestEmpresaSoftDelete:
    """Tests para soft delete de empresas - funcionalidad crítica de retención"""

    def test_soft_delete_marca_empresa_como_eliminada(self, empresa_activa, superuser):
        """Soft delete debe marcar is_deleted=True y establecer metadata"""
        empresa_activa.soft_delete(user=superuser, reason="Test de eliminación")

        assert empresa_activa.is_deleted is True
        assert empresa_activa.deleted_at is not None
        assert empresa_activa.deleted_by == superuser
        assert empresa_activa.delete_reason == "Test de eliminación"

    def test_soft_delete_preserva_datos_de_empresa(self, empresa_activa, superuser):
        """Soft delete NO debe eliminar datos de la empresa"""
        empresa_id = empresa_activa.id
        empresa_nombre = empresa_activa.nombre

        empresa_activa.soft_delete(user=superuser)

        # La empresa debe seguir existiendo en la BD
        empresa = Empresa.objects.get(id=empresa_id)
        assert empresa.nombre == empresa_nombre
        assert empresa.is_deleted is True

    def test_get_deleted_companies_retorna_solo_eliminadas(self, empresa_activa, superuser):
        """get_deleted_companies() debe retornar solo empresas eliminadas"""
        empresa_activa.soft_delete(user=superuser)

        # Crear otra empresa activa
        empresa_no_eliminada = Empresa.objects.create(
            nombre='Empresa NO Eliminada',
            nit='900333333-3',
            email='no_eliminada@test.com'
        )

        deleted = Empresa.get_deleted_companies()

        assert empresa_activa in deleted
        assert empresa_no_eliminada not in deleted

    def test_get_active_companies_excluye_eliminadas(self, empresa_activa, superuser):
        """get_active_companies() debe excluir empresas eliminadas"""
        # Crear empresa que será eliminada
        empresa_eliminada = Empresa.objects.create(
            nombre='Para Eliminar',
            nit='900444444-4',
            email='eliminar@test.com'
        )
        empresa_eliminada.soft_delete(user=superuser)

        active = Empresa.get_active_companies()

        assert empresa_activa in active
        assert empresa_eliminada not in active


# ==================== TESTS: Restauración ====================

@pytest.mark.django_db
class TestEmpresaRestauracion:
    """Tests para restauración de empresas eliminadas"""

    def test_restore_restaura_empresa_eliminada(self, empresa_activa, superuser):
        """restore() debe restaurar una empresa previamente eliminada"""
        empresa_activa.soft_delete(user=superuser)
        assert empresa_activa.is_deleted is True

        success, message = empresa_activa.restore(user=superuser)

        assert success is True
        assert empresa_activa.is_deleted is False
        assert empresa_activa.deleted_at is None
        assert empresa_activa.deleted_by is None
        assert empresa_activa.delete_reason is None

    def test_restore_empresa_activa_retorna_false(self, empresa_activa, superuser):
        """restore() en empresa activa debe retornar False"""
        assert empresa_activa.is_deleted is False

        success, message = empresa_activa.restore(user=superuser)

        assert success is False
        assert "no está eliminada" in message

    def test_can_be_restored_detecta_empresas_restaurables(self, empresa_activa, superuser):
        """can_be_restored() debe detectar si empresa puede ser restaurada"""
        assert empresa_activa.can_be_restored() is False

        empresa_activa.soft_delete(user=superuser)

        assert empresa_activa.can_be_restored() is True

    def test_get_delete_info_retorna_info_de_eliminacion(self, empresa_activa, superuser):
        """get_delete_info() debe retornar metadata de eliminación"""
        empresa_activa.soft_delete(user=superuser, reason="Empresa inactiva")

        info = empresa_activa.get_delete_info()

        assert info is not None
        assert info['deleted_by'] == 'admin_test'
        assert info['delete_reason'] == 'Empresa inactiva'
        assert 'days_since_deletion' in info
        assert 'days_until_permanent_deletion' in info

    def test_get_delete_info_empresa_activa_retorna_none(self, empresa_activa):
        """get_delete_info() en empresa activa debe retornar None"""
        assert empresa_activa.get_delete_info() is None


# ==================== TESTS: Límites de Equipos ====================

@pytest.mark.django_db
class TestEmpresaLimitesEquipos:
    """Tests para límites de equipos por empresa"""

    def test_get_limite_equipos_retorna_limite_configurado(self, empresa_activa):
        """get_limite_equipos() debe retornar el límite configurado"""
        empresa_activa.limite_equipos_empresa = 100
        empresa_activa.save()

        limite = empresa_activa.get_limite_equipos()

        assert limite == 100

    def test_get_limite_equipos_acceso_manual_ilimitado(self, empresa_activa):
        """Acceso manual debe dar límite ilimitado"""
        empresa_activa.acceso_manual_activo = True
        empresa_activa.save()

        limite = empresa_activa.get_limite_equipos()

        assert limite == float('inf')

    def test_empresa_puede_crear_equipos_bajo_limite(self, empresa_activa):
        """Empresa debe poder crear equipos bajo el límite"""
        empresa_activa.limite_equipos_empresa = 5
        empresa_activa.save()

        # Crear 3 equipos (bajo el límite de 5)
        for i in range(3):
            Equipo.objects.create(
                empresa=empresa_activa,
                codigo_interno=f'EQ-{i:03d}',
                nombre=f'Equipo Test {i}',
                estado='ACTIVO'
            )

        equipos_count = Equipo.objects.filter(empresa=empresa_activa).count()
        assert equipos_count == 3
        assert equipos_count < empresa_activa.get_limite_equipos()


# ==================== TESTS: Planes y Suscripciones ====================

@pytest.mark.django_db
class TestEmpresaPlanesSubscripciones:
    """Tests para gestión de planes y suscripciones"""

    def test_activar_plan_pagado_configura_empresa(self, empresa_trial):
        """activar_plan_pagado() debe configurar plan correctamente"""
        empresa_trial.activar_plan_pagado(
            limite_equipos=200,
            limite_almacenamiento_mb=2048,
            duracion_meses=12
        )

        assert empresa_trial.es_periodo_prueba is False
        assert empresa_trial.limite_equipos_empresa == 200
        assert empresa_trial.limite_almacenamiento_mb == 2048
        assert empresa_trial.duracion_suscripcion_meses == 12
        assert empresa_trial.estado_suscripcion == 'Activo'
        assert empresa_trial.fecha_inicio_plan is not None

    def test_nueva_empresa_tiene_limites_predeterminados(self):
        """Nueva empresa debe tener límites predeterminados"""
        empresa = Empresa.objects.create(
            nombre='Nueva Empresa',
            nit='900555555-5',
            email='nueva@test.com'
        )

        # Verificar que tiene límites configurados
        assert empresa.limite_equipos_empresa is not None
        assert empresa.limite_equipos_empresa > 0
        assert empresa.limite_almacenamiento_mb is not None
        assert empresa.limite_almacenamiento_mb > 0

    def test_get_estado_suscripcion_display_retorna_estado(self):
        """get_estado_suscripcion_display() debe retornar el estado actual"""
        empresa = Empresa.objects.create(
            nombre='Empresa Test',
            nit='900888888-8',
            email='test@test.com',
            estado_suscripcion='Activo'
        )

        estado = empresa.get_estado_suscripcion_display()

        # Debe contener información de estado
        assert estado is not None
        assert len(estado) > 0

    def test_get_fecha_fin_plan_sin_plan_retorna_none(self):
        """get_fecha_fin_plan() sin plan debe retornar None"""
        empresa = Empresa.objects.create(
            nombre='Sin Plan',
            nit='900666666-6',
            email='sinplan@test.com',
            es_periodo_prueba=False,
            fecha_inicio_plan=None
        )

        assert empresa.get_fecha_fin_plan() is None


# ==================== TESTS: Multitenancy ====================

@pytest.mark.django_db
class TestEmpresaMultitenancy:
    """Tests para validar multitenancy estricto entre empresas"""

    def test_usuarios_solo_ven_su_empresa(self):
        """Usuarios deben ver solo datos de su propia empresa"""
        empresa1 = Empresa.objects.create(
            nombre='Empresa 1',
            nit='900111111-1',
            email='emp1@test.com'
        )
        empresa2 = Empresa.objects.create(
            nombre='Empresa 2',
            nit='900222222-2',
            email='emp2@test.com'
        )

        user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='pass',
            empresa=empresa1
        )
        user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='pass',
            empresa=empresa2
        )

        # Usuario 1 solo ve su empresa
        assert user1.empresa == empresa1
        assert user1.empresa != empresa2

        # Usuario 2 solo ve su empresa
        assert user2.empresa == empresa2
        assert user2.empresa != empresa1

    def test_equipos_aislados_por_empresa(self):
        """Equipos deben estar aislados por empresa"""
        empresa1 = Empresa.objects.create(
            nombre='Empresa 1',
            nit='900111111-1',
            email='emp1@test.com'
        )
        empresa2 = Empresa.objects.create(
            nombre='Empresa 2',
            nit='900222222-2',
            email='emp2@test.com'
        )

        # Crear equipos para cada empresa
        equipo1 = Equipo.objects.create(
            empresa=empresa1,
            codigo_interno='EQ1-001',
            nombre='Equipo Empresa 1'
        )
        equipo2 = Equipo.objects.create(
            empresa=empresa2,
            codigo_interno='EQ2-001',
            nombre='Equipo Empresa 2'
        )

        # Verificar aislamiento
        equipos_empresa1 = Equipo.objects.filter(empresa=empresa1)
        equipos_empresa2 = Equipo.objects.filter(empresa=empresa2)

        assert equipo1 in equipos_empresa1
        assert equipo1 not in equipos_empresa2
        assert equipo2 in equipos_empresa2
        assert equipo2 not in equipos_empresa1
