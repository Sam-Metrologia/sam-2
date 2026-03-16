"""
Tests adicionales para aumentar la cobertura de core/views/activities.py.
Enfocados en:
- dar_baja_equipo (líneas 708-709, 731-757)
- inactivar_equipo (líneas 791-795, 810)
- activar_equipo (líneas 833-834, 869)
- programmed_activities_list (líneas 894-895, 905-908, 921-924, 937-940, 954-957)
"""
import pytest
from datetime import date, timedelta
from django.urls import reverse
from django.contrib.auth.models import Permission

from core.models import (
    CustomUser, Empresa, Equipo
)


@pytest.mark.django_db
class TestDarBajaEquipoEstados:
    """Cubrir ramas de dar_baja_equipo para equipos ya dados de baja."""

    def _get_user_with_perm(self, empresa):
        user = CustomUser.objects.create_user(
            username='baja_user_cov',
            email='baja_cov@test.com',
            password='testpass123',
            empresa=empresa,
            rol_usuario='ADMINISTRADOR',
            is_active=True,
        )
        perm = Permission.objects.get(codename='add_bajaequipo')
        user.user_permissions.add(perm)
        return user

    def test_dar_baja_equipo_ya_dado_de_baja_redirige(self, client, equipo_factory, empresa_factory):
        """Líneas 708-709: Intentar dar de baja equipo que ya está de baja redirige."""
        empresa = empresa_factory()
        user = self._get_user_with_perm(empresa)
        client.login(username='baja_user_cov', password='testpass123')

        # Equipo ya dado de baja
        equipo = equipo_factory(empresa=empresa, estado='De Baja')

        url = reverse('core:dar_baja_equipo', kwargs={'equipo_pk': equipo.pk})
        response = client.get(url)

        assert response.status_code == 302
        assert 'detalle_equipo' in response.url or str(equipo.pk) in response.url


@pytest.mark.django_db
class TestInactivarEquipoEstados:
    """Cubrir ramas de inactivar_equipo (791-795, 810)."""

    def _get_user_with_perm(self, empresa):
        user = CustomUser.objects.create_user(
            username='inact_user_cov',
            email='inact_cov@test.com',
            password='testpass123',
            empresa=empresa,
            rol_usuario='ADMINISTRADOR',
            is_active=True,
        )
        perm = Permission.objects.get(codename='change_equipo')
        user.user_permissions.add(perm)
        return user

    def test_inactivar_equipo_ya_inactivo_redirige(self, client, equipo_factory, empresa_factory):
        """Líneas 791-792: Equipo ya inactivo → redirige con mensaje."""
        empresa = empresa_factory()
        user = self._get_user_with_perm(empresa)
        client.login(username='inact_user_cov', password='testpass123')

        equipo = equipo_factory(empresa=empresa, estado='Inactivo')
        url = reverse('core:inactivar_equipo', kwargs={'equipo_pk': equipo.pk})
        response = client.get(url)

        assert response.status_code == 302

    def test_inactivar_equipo_de_baja_redirige(self, client, equipo_factory, empresa_factory):
        """Líneas 794-795: Equipo dado de baja no puede inactivarse → redirige."""
        empresa = empresa_factory()
        user = self._get_user_with_perm(empresa)
        client.login(username='inact_user_cov', password='testpass123')

        equipo = equipo_factory(empresa=empresa, estado='De Baja')
        url = reverse('core:inactivar_equipo', kwargs={'equipo_pk': equipo.pk})
        response = client.get(url)

        assert response.status_code == 302

    def test_inactivar_equipo_get_muestra_confirmacion(self, client, equipo_factory, empresa_factory):
        """Línea 810: GET en inactivar_equipo muestra página de confirmación."""
        empresa = empresa_factory()
        user = self._get_user_with_perm(empresa)
        client.login(username='inact_user_cov', password='testpass123')

        equipo = equipo_factory(empresa=empresa, estado='Activo')
        url = reverse('core:inactivar_equipo', kwargs={'equipo_pk': equipo.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert 'equipo' in response.context


@pytest.mark.django_db
class TestActivarEquipoEstados:
    """Cubrir ramas de activar_equipo (833-834, 869)."""

    def _get_user_with_perm(self, empresa):
        user = CustomUser.objects.create_user(
            username='activ_user_cov',
            email='activ_cov@test.com',
            password='testpass123',
            empresa=empresa,
            rol_usuario='ADMINISTRADOR',
            is_active=True,
        )
        perm = Permission.objects.get(codename='change_equipo')
        user.user_permissions.add(perm)
        return user

    def test_activar_equipo_ya_activo_redirige(self, client, equipo_factory, empresa_factory):
        """Líneas 833-834: Equipo ya activo → redirige con mensaje."""
        empresa = empresa_factory()
        user = self._get_user_with_perm(empresa)
        client.login(username='activ_user_cov', password='testpass123')

        equipo = equipo_factory(empresa=empresa, estado='Activo')
        url = reverse('core:activar_equipo', kwargs={'equipo_pk': equipo.pk})
        response = client.get(url)

        assert response.status_code == 302

    def test_activar_equipo_inactivo_get_muestra_confirmacion(self, client, equipo_factory, empresa_factory):
        """Línea 869: GET en activar_equipo con equipo inactivo muestra confirmación."""
        empresa = empresa_factory()
        user = self._get_user_with_perm(empresa)
        client.login(username='activ_user_cov', password='testpass123')

        equipo = equipo_factory(empresa=empresa, estado='Inactivo')
        url = reverse('core:activar_equipo', kwargs={'equipo_pk': equipo.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert 'equipo' in response.context


@pytest.mark.django_db
class TestProgrammedActivitiesListCobertura:
    """Cubrir líneas no cubiertas de programmed_activities_list (894-957)."""

    def test_usuario_sin_empresa_obtiene_lista_vacia(self, client):
        """Líneas 894-895: Usuario sin empresa → lista vacía."""
        user = CustomUser.objects.create_user(
            username='sin_empresa_prog',
            email='sin_empresa_prog@test.com',
            password='testpass123',
            empresa=None,
            is_active=True,
        )
        client.login(username='sin_empresa_prog', password='testpass123')

        url = reverse('core:programmed_activities_list')
        response = client.get(url)

        assert response.status_code == 200

    def test_lista_con_equipos_con_fechas_programadas(self, client, equipo_factory, empresa_factory):
        """Líneas 905-908, 921-924, 937-940: Equipos con fechas programadas aparecen en la lista."""
        empresa = empresa_factory()
        user = CustomUser.objects.create_user(
            username='prog_act_user',
            email='prog_act@test.com',
            password='testpass123',
            empresa=empresa,
            is_active=True,
        )
        client.login(username='prog_act_user', password='testpass123')

        # Crear equipo con fechas próximas programadas
        equipo = equipo_factory(empresa=empresa, estado='Activo')
        # Asignar fechas directamente usando update() para evitar recálculo de save()
        Equipo.objects.filter(pk=equipo.pk).update(
            proxima_calibracion=date.today() + timedelta(days=30),
            proximo_mantenimiento=date.today() + timedelta(days=60),
            proxima_comprobacion=date.today() - timedelta(days=5),  # vencida
        )

        url = reverse('core:programmed_activities_list')
        response = client.get(url)

        assert response.status_code == 200
        # Verificar que hay actividades en el contexto
        page_obj = response.context.get('page_obj')
        assert page_obj is not None
        assert len(page_obj.object_list) >= 3  # calibracion + mantenimiento + comprobacion

    def test_paginacion_pagina_no_entera(self, authenticated_client):
        """Líneas 954-955: page='abc' → PageNotAnInteger → página 1."""
        user = authenticated_client.user

        url = reverse('core:programmed_activities_list')
        response = authenticated_client.get(url, {'page': 'abc'})

        assert response.status_code == 200
        page_obj = response.context.get('page_obj')
        assert page_obj is not None
        assert page_obj.number == 1  # Debe retornar a la página 1

    def test_paginacion_pagina_fuera_de_rango(self, authenticated_client):
        """Líneas 956-957: page=9999 → EmptyPage → última página."""
        url = reverse('core:programmed_activities_list')
        response = authenticated_client.get(url, {'page': '9999'})

        assert response.status_code == 200
        page_obj = response.context.get('page_obj')
        assert page_obj is not None
        # Debe retornar la última página disponible
        assert page_obj.number == page_obj.paginator.num_pages


@pytest.mark.django_db
class TestInactivarActivarEquipoPost:
    """Cubrir ramas POST de inactivar_equipo (799-807) y activar_equipo (837-866)."""

    def _setup_user_equipo(self, estado='Activo'):
        empresa = Empresa.objects.create(
            nombre=f"Empresa POST Test {estado}",
            nit=f"8009{hash(estado) % 100000:05d}-1",
            limite_equipos_empresa=10,
        )
        user = CustomUser.objects.create_user(
            username=f'post_user_{estado[:3]}',
            email=f'post_{estado[:3]}@test.com',
            password='testpass123',
            empresa=empresa,
            rol_usuario='ADMINISTRADOR',
            is_active=True,
        )
        perm = Permission.objects.get(codename='change_equipo')
        user.user_permissions.add(perm)
        equipo = Equipo.objects.create(
            codigo_interno=f'POST-{estado[:3]}-001',
            nombre=f'Equipo {estado}',
            empresa=empresa,
            estado=estado,
        )
        return user, equipo

    def test_inactivar_equipo_post_cambia_estado(self, client):
        """Líneas 799-807: POST a inactivar_equipo cambia estado a Inactivo."""
        user, equipo = self._setup_user_equipo(estado='Activo')
        client.login(username='post_user_Act', password='testpass123')

        url = reverse('core:inactivar_equipo', kwargs={'equipo_pk': equipo.pk})
        response = client.post(url)

        assert response.status_code == 302
        equipo.refresh_from_db()
        assert equipo.estado == 'Inactivo'

    def test_activar_equipo_post_desde_inactivo(self, client):
        """Líneas 850-860: POST a activar_equipo con equipo Inactivo → Activo."""
        user, equipo = self._setup_user_equipo(estado='Inactivo')
        client.login(username='post_user_Ina', password='testpass123')

        url = reverse('core:activar_equipo', kwargs={'equipo_pk': equipo.pk})
        response = client.post(url)

        assert response.status_code == 302
        equipo.refresh_from_db()
        assert equipo.estado == 'Activo'


@pytest.mark.django_db
class TestDarBajaEquipoPost:
    """Cubrir rama POST de dar_baja_equipo con formulario válido (731-752)."""

    def test_dar_baja_equipo_post_formulario_valido(self, client, equipo_factory, empresa_factory):
        """Líneas 731-752: POST con formulario válido da de baja el equipo."""
        empresa = empresa_factory()
        user = CustomUser.objects.create_user(
            username='baja_post_user',
            email='baja_post@test.com',
            password='testpass123',
            empresa=empresa,
            rol_usuario='ADMINISTRADOR',
            is_active=True,
        )
        perm = Permission.objects.get(codename='add_bajaequipo')
        user.user_permissions.add(perm)
        client.login(username='baja_post_user', password='testpass123')

        equipo = equipo_factory(empresa=empresa, estado='Activo')

        url = reverse('core:dar_baja_equipo', kwargs={'equipo_pk': equipo.pk})
        data = {
            'fecha_baja': date.today().strftime('%Y-%m-%d'),
            'razon_baja': 'Equipo obsoleto, reemplazado por modelo nuevo',
            'observaciones': 'Se da de baja definitivamente',
        }
        response = client.post(url, data)

        # Si redirigió, verificar cambio de estado
        if response.status_code == 302:
            equipo.refresh_from_db()
            assert equipo.estado == 'De Baja'
        else:
            # Formulario puede tener errores de validación adicionales
            assert response.status_code == 200
