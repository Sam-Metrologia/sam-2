"""
Tests para core.views.admin.usuarios_por_empresa — vista de usuarios
agrupados por empresa, con el estado de cada empresa (activa / eliminada
en gracia / pendiente de purga) y los usuarios huérfanos aparte.
"""
import pytest
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone

from tests.factories import EmpresaFactory, UserFactory


def _soft_delete_hace(empresa, dias):
    empresa.soft_delete(reason='Test')
    empresa.deleted_at = timezone.now() - timedelta(days=dias)
    empresa.save(update_fields=['deleted_at'])


@pytest.mark.django_db
class TestUsuariosPorEmpresaAcceso:

    def test_requiere_login(self, client):
        response = client.get(reverse('core:usuarios_por_empresa'))
        assert response.status_code == 302

    def test_usuario_normal_no_puede_acceder(self, client):
        empresa = EmpresaFactory()
        user = UserFactory(empresa=empresa, is_superuser=False)
        client.force_login(user)
        response = client.get(reverse('core:usuarios_por_empresa'))
        assert response.status_code == 302

    def test_superusuario_ve_la_pagina(self, client):
        user = UserFactory(is_superuser=True, is_staff=True)
        client.force_login(user)
        response = client.get(reverse('core:usuarios_por_empresa'))
        assert response.status_code == 200


@pytest.mark.django_db
class TestAgrupacionYEstados:

    def _superusuario(self, client):
        user = UserFactory(is_superuser=True, is_staff=True)
        client.force_login(user)
        return user

    def test_agrupa_usuarios_por_empresa(self, client):
        self._superusuario(client)
        empresa_a = EmpresaFactory(nombre='Empresa A')
        empresa_b = EmpresaFactory(nombre='Empresa B')
        UserFactory(empresa=empresa_a)
        UserFactory(empresa=empresa_a)
        UserFactory(empresa=empresa_b)

        response = client.get(reverse('core:usuarios_por_empresa'))

        empresas_en_grupos = [g['empresa'] for g in response.context['pagina_grupos'].object_list]
        assert empresa_a in empresas_en_grupos
        assert empresa_b in empresas_en_grupos
        grupo_a = next(g for g in response.context['pagina_grupos'].object_list if g['empresa'] == empresa_a)
        assert len(grupo_a['usuarios']) == 2

    def test_empresa_activa_se_marca_correctamente(self, client):
        self._superusuario(client)
        empresa = EmpresaFactory()
        UserFactory(empresa=empresa)

        response = client.get(reverse('core:usuarios_por_empresa'))

        grupo = next(g for g in response.context['pagina_grupos'].object_list if g['empresa'] == empresa)
        assert grupo['estado']['clave'] == 'activa'

    def test_empresa_eliminada_en_gracia_muestra_dias_restantes(self, client):
        self._superusuario(client)
        empresa = EmpresaFactory()
        UserFactory(empresa=empresa)
        _soft_delete_hace(empresa, 100)  # 80 días restantes de 180

        response = client.get(reverse('core:usuarios_por_empresa'))

        grupo = next(g for g in response.context['pagina_grupos'].object_list if g['empresa'] == empresa)
        assert grupo['estado']['clave'] == 'gracia'
        assert '80' in grupo['estado']['label']

    def test_empresa_pendiente_de_purga(self, client):
        self._superusuario(client)
        empresa = EmpresaFactory()
        UserFactory(empresa=empresa)
        _soft_delete_hace(empresa, 200)  # ya pasó 180, pero el cron no ha corrido

        response = client.get(reverse('core:usuarios_por_empresa'))

        grupo = next(g for g in response.context['pagina_grupos'].object_list if g['empresa'] == empresa)
        assert grupo['estado']['clave'] == 'purga'

    def test_empresa_sin_usuarios_no_aparece(self, client):
        self._superusuario(client)
        empresa_vacia = EmpresaFactory()

        response = client.get(reverse('core:usuarios_por_empresa'))

        empresas_en_grupos = [g['empresa'] for g in response.context['pagina_grupos'].object_list]
        assert empresa_vacia not in empresas_en_grupos

    def test_usuarios_huerfanos_aparecen_aparte(self, client):
        self._superusuario(client)
        huerfano = UserFactory(empresa=None, is_superuser=False)

        response = client.get(reverse('core:usuarios_por_empresa'))

        assert huerfano in response.context['huerfanos']
        assert response.context['total_huerfanos'] >= 1

    def test_filtro_estado_activa_excluye_eliminadas(self, client):
        self._superusuario(client)
        empresa_activa = EmpresaFactory()
        UserFactory(empresa=empresa_activa)
        empresa_eliminada = EmpresaFactory()
        UserFactory(empresa=empresa_eliminada)
        _soft_delete_hace(empresa_eliminada, 50)

        response = client.get(reverse('core:usuarios_por_empresa'), {'estado': 'activa'})

        empresas_en_grupos = [g['empresa'] for g in response.context['pagina_grupos'].object_list]
        assert empresa_activa in empresas_en_grupos
        assert empresa_eliminada not in empresas_en_grupos
        assert response.context['huerfanos'] == []

    def test_filtro_sin_empresa_solo_muestra_huerfanos(self, client):
        self._superusuario(client)
        empresa = EmpresaFactory()
        UserFactory(empresa=empresa)
        huerfano = UserFactory(empresa=None, is_superuser=False)

        response = client.get(reverse('core:usuarios_por_empresa'), {'estado': 'sin_empresa'})

        assert len(response.context['pagina_grupos'].object_list) == 0
        assert huerfano in response.context['huerfanos']

    def test_busqueda_por_nombre_de_empresa(self, client):
        self._superusuario(client)
        empresa_buscada = EmpresaFactory(nombre='Laboratorio Especial XYZ')
        UserFactory(empresa=empresa_buscada)
        otra_empresa = EmpresaFactory(nombre='Otra Cosa')
        UserFactory(empresa=otra_empresa)

        response = client.get(reverse('core:usuarios_por_empresa'), {'q': 'Especial XYZ'})

        empresas_en_grupos = [g['empresa'] for g in response.context['pagina_grupos'].object_list]
        assert empresa_buscada in empresas_en_grupos
        assert otra_empresa not in empresas_en_grupos
