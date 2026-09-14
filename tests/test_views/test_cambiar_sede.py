"""
Tests para la vista core.views.base.cambiar_sede (selector de sede en el navbar).
"""
import pytest
from django.urls import reverse

from core.tenancy import SESSION_KEY_EMPRESA_ACTIVA
from tests.factories import EmpresaFactory, UserFactory


@pytest.mark.django_db
class TestCambiarSede:

    def test_gerente_de_matriz_puede_cambiar_a_una_sede(self, client):
        matriz = EmpresaFactory()
        sede_a = EmpresaFactory(empresa_matriz=matriz)
        user = UserFactory(empresa=matriz, rol_usuario='GERENCIA')
        client.force_login(user)

        response = client.post(reverse('core:cambiar_sede'), {'empresa_id': sede_a.id})

        assert response.status_code == 302
        assert client.session[SESSION_KEY_EMPRESA_ACTIVA] == sede_a.id

    def test_gerente_de_matriz_puede_volver_a_la_matriz(self, client):
        matriz = EmpresaFactory()
        sede_a = EmpresaFactory(empresa_matriz=matriz)
        user = UserFactory(empresa=matriz, rol_usuario='GERENCIA')
        client.force_login(user)
        session = client.session
        session[SESSION_KEY_EMPRESA_ACTIVA] = sede_a.id
        session.save()

        response = client.post(reverse('core:cambiar_sede'), {'empresa_id': matriz.id})

        assert response.status_code == 302
        assert client.session[SESSION_KEY_EMPRESA_ACTIVA] == matriz.id

    def test_no_puede_elegir_una_empresa_ajena(self, client):
        matriz = EmpresaFactory()
        EmpresaFactory(empresa_matriz=matriz)
        empresa_ajena = EmpresaFactory()
        user = UserFactory(empresa=matriz, rol_usuario='GERENCIA')
        client.force_login(user)

        response = client.post(reverse('core:cambiar_sede'), {'empresa_id': empresa_ajena.id})

        assert response.status_code == 302
        assert SESSION_KEY_EMPRESA_ACTIVA not in client.session

    def test_usuario_normal_no_puede_cambiar_de_sede(self, client):
        """Un TECNICO no tiene sedes entre las que elegir, aunque mande un id válido de otra empresa."""
        empresa = EmpresaFactory()
        otra_empresa = EmpresaFactory()
        user = UserFactory(empresa=empresa, rol_usuario='TECNICO')
        client.force_login(user)

        response = client.post(reverse('core:cambiar_sede'), {'empresa_id': otra_empresa.id})

        assert response.status_code == 302
        assert SESSION_KEY_EMPRESA_ACTIVA not in client.session

    def test_id_invalido_no_rompe_la_vista(self, client):
        matriz = EmpresaFactory()
        EmpresaFactory(empresa_matriz=matriz)
        user = UserFactory(empresa=matriz, rol_usuario='GERENCIA')
        client.force_login(user)

        response = client.post(reverse('core:cambiar_sede'), {'empresa_id': 'no-es-un-numero'})

        assert response.status_code == 302
        assert SESSION_KEY_EMPRESA_ACTIVA not in client.session

    def test_requiere_login(self, client):
        response = client.post(reverse('core:cambiar_sede'), {'empresa_id': 1})
        assert response.status_code == 302
        assert reverse('core:login') in response.url

    def test_get_no_permitido(self, client):
        matriz = EmpresaFactory()
        EmpresaFactory(empresa_matriz=matriz)
        user = UserFactory(empresa=matriz, rol_usuario='GERENCIA')
        client.force_login(user)

        response = client.get(reverse('core:cambiar_sede'))

        assert response.status_code == 405

    def test_redirige_a_next_si_es_una_ruta_local_valida(self, client):
        matriz = EmpresaFactory()
        sede_a = EmpresaFactory(empresa_matriz=matriz)
        user = UserFactory(empresa=matriz, rol_usuario='GERENCIA')
        client.force_login(user)

        response = client.post(reverse('core:cambiar_sede'), {
            'empresa_id': sede_a.id,
            'next': '/dashboard/',
        })

        assert response.url == '/dashboard/'

    def test_ignora_next_externo_y_cae_a_dashboard(self, client):
        """Nunca debe redirigir a un host externo (open redirect)."""
        matriz = EmpresaFactory()
        sede_a = EmpresaFactory(empresa_matriz=matriz)
        user = UserFactory(empresa=matriz, rol_usuario='GERENCIA')
        client.force_login(user)

        response = client.post(reverse('core:cambiar_sede'), {
            'empresa_id': sede_a.id,
            'next': 'https://evil.example.com/phishing',
        })

        assert response.url == reverse('core:dashboard')


@pytest.mark.django_db
class TestSedeContextProcessor:

    def test_usuario_sin_sedes_no_ve_selector(self, client):
        empresa = EmpresaFactory()
        user = UserFactory(empresa=empresa, rol_usuario='TECNICO')
        client.force_login(user)

        response = client.get(reverse('core:dashboard'))

        assert response.context['empresas_seleccionables'] == []

    def test_gerente_de_matriz_ve_selector_con_sedes(self, client):
        matriz = EmpresaFactory()
        sede_a = EmpresaFactory(empresa_matriz=matriz)
        user = UserFactory(empresa=matriz, rol_usuario='GERENCIA')
        client.force_login(user)

        response = client.get(reverse('core:dashboard'))

        seleccionables = response.context['empresas_seleccionables']
        assert set(seleccionables) == {matriz, sede_a}
        assert response.context['sede_activa'] == matriz
