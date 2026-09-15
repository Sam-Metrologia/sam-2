"""
Tests para core.tenancy.get_empresa_activa.

Estos tests fijan el contrato clave del refactor multi-sede: hoy, para
cualquier usuario normal, get_empresa_activa(request) debe devolver
EXACTAMENTE lo mismo que request.user.empresa. Si algún cambio futuro rompe
este passthrough para el caso simple (una sola empresa), estos tests deben
fallar.
"""
import pytest
from core.tenancy import get_empresa_activa, get_empresas_seleccionables, SESSION_KEY_EMPRESA_ACTIVA
from tests.factories import EmpresaFactory, UserFactory


class DummyRequest:
    def __init__(self, user, session=None):
        self.user = user
        self.session = session if session is not None else {}


@pytest.mark.django_db
class TestGetEmpresaActiva:

    def test_devuelve_la_empresa_del_usuario(self):
        empresa = EmpresaFactory()
        user = UserFactory(empresa=empresa)
        request = DummyRequest(user)

        assert get_empresa_activa(request) == empresa

    def test_es_identico_a_request_user_empresa(self):
        empresa = EmpresaFactory()
        user = UserFactory(empresa=empresa)
        request = DummyRequest(user)

        assert get_empresa_activa(request) == request.user.empresa

    def test_usuario_sin_empresa_devuelve_none(self):
        user = UserFactory(empresa=None)
        request = DummyRequest(user)

        assert get_empresa_activa(request) is None

    def test_superusuario_sin_empresa_devuelve_none(self):
        user = UserFactory(empresa=None, is_superuser=True, is_staff=True)
        request = DummyRequest(user)

        assert get_empresa_activa(request) is None

    def test_usuario_normal_con_sesion_ignora_sesion_si_no_es_gerente_de_matriz(self):
        """Un usuario normal (sin sedes) nunca debe ver afectado su resultado por la sesión."""
        empresa = EmpresaFactory()
        otra_empresa = EmpresaFactory()
        user = UserFactory(empresa=empresa, rol_usuario='TECNICO')
        request = DummyRequest(user, session={SESSION_KEY_EMPRESA_ACTIVA: otra_empresa.id})

        assert get_empresa_activa(request) == empresa


@pytest.mark.django_db
class TestGetEmpresasSeleccionables:

    def test_usuario_sin_sedes_solo_se_ve_a_si_mismo(self):
        empresa = EmpresaFactory()
        user = UserFactory(empresa=empresa, rol_usuario='TECNICO')

        assert get_empresas_seleccionables(user) == [empresa]

    def test_gerente_de_matriz_ve_matriz_y_sedes(self):
        matriz = EmpresaFactory()
        sede_a = EmpresaFactory(empresa_matriz=matriz)
        sede_b = EmpresaFactory(empresa_matriz=matriz)
        user = UserFactory(empresa=matriz, rol_usuario='GERENCIA')

        resultado = get_empresas_seleccionables(user)

        assert resultado[0] == matriz
        assert set(resultado[1:]) == {sede_a, sede_b}

    def test_administrador_de_matriz_no_ve_sedes(self):
        """Solo GERENCIA puede alternar entre sedes — ADMINISTRADOR no."""
        matriz = EmpresaFactory()
        EmpresaFactory(empresa_matriz=matriz)
        user = UserFactory(empresa=matriz, rol_usuario='ADMINISTRADOR')

        assert get_empresas_seleccionables(user) == [matriz]

    def test_gerente_de_una_sede_no_ve_hermanas(self):
        """El GERENCIA de una sede (no de la matriz) no puede alternar a otras sedes."""
        matriz = EmpresaFactory()
        sede_a = EmpresaFactory(empresa_matriz=matriz)
        EmpresaFactory(empresa_matriz=matriz)
        user = UserFactory(empresa=sede_a, rol_usuario='GERENCIA')

        assert get_empresas_seleccionables(user) == [sede_a]


@pytest.mark.django_db
class TestGetEmpresaActivaMultiSede:

    def test_gerente_de_matriz_sin_seleccion_ve_su_propia_empresa(self):
        matriz = EmpresaFactory()
        EmpresaFactory(empresa_matriz=matriz)
        user = UserFactory(empresa=matriz, rol_usuario='GERENCIA')
        request = DummyRequest(user)

        assert get_empresa_activa(request) == matriz

    def test_gerente_de_matriz_con_sede_elegida_en_sesion_ve_esa_sede(self):
        matriz = EmpresaFactory()
        sede_a = EmpresaFactory(empresa_matriz=matriz)
        user = UserFactory(empresa=matriz, rol_usuario='GERENCIA')
        request = DummyRequest(user, session={SESSION_KEY_EMPRESA_ACTIVA: sede_a.id})

        assert get_empresa_activa(request) == sede_a

    def test_id_en_sesion_que_no_pertenece_al_usuario_se_ignora(self):
        """Nunca confiar ciegamente en lo guardado en sesión: debe validar pertenencia."""
        matriz = EmpresaFactory()
        EmpresaFactory(empresa_matriz=matriz)
        empresa_ajena = EmpresaFactory()
        user = UserFactory(empresa=matriz, rol_usuario='GERENCIA')
        request = DummyRequest(user, session={SESSION_KEY_EMPRESA_ACTIVA: empresa_ajena.id})

        assert get_empresa_activa(request) == matriz

    def test_administrador_de_matriz_con_sede_en_sesion_no_puede_cambiar(self):
        matriz = EmpresaFactory()
        sede_a = EmpresaFactory(empresa_matriz=matriz)
        user = UserFactory(empresa=matriz, rol_usuario='ADMINISTRADOR')
        request = DummyRequest(user, session={SESSION_KEY_EMPRESA_ACTIVA: sede_a.id})

        assert get_empresa_activa(request) == matriz
