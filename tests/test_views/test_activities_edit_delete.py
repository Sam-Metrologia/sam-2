"""
Tests para editar/eliminar calibraciones, mantenimientos y comprobaciones.

Cubre líneas no cubiertas de activities.py:
- editar_calibracion GET (132) + POST válido (128-130)
- eliminar_calibracion GET (163-175) + POST (157-162)
- editar_mantenimiento GET (285) + POST válido (263-279) + superuser (260)
- eliminar_mantenimiento GET (321-328) + POST (310-315) + superuser (304)
- detalle_mantenimiento GET (340-355) + superuser (341)
- editar_comprobacion GET (464-466) + POST válido (448-459) + superuser (439)
- eliminar_comprobacion GET (501-508) + POST (491-495) + superuser (485)
- añadir_calibracion form inválido (66-84) + superuser (26)
- añadir_mantenimiento form inválido (222-237) + superuser (193)
- añadir_comprobacion form inválido (402-417) + superuser (373)
"""
import pytest
from datetime import date, timedelta
from django.urls import reverse

from core.models import Calibracion, Mantenimiento, Comprobacion


# =============================================================================
# EDITAR CALIBRACIÓN
# =============================================================================

@pytest.mark.django_db
class TestEditarCalibracionCobertura:
    """Cubrir editar_calibracion (109, 128-134)."""

    def test_get_editar_calibracion_muestra_formulario(
        self, authenticated_client, calibracion_factory, equipo_factory
    ):
        """GET muestra el formulario de edición."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)
        calibracion = calibracion_factory(equipo=equipo)

        url = reverse('core:editar_calibracion', kwargs={'equipo_pk': equipo.pk, 'pk': calibracion.pk})
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert 'form' in response.context
        assert 'calibracion' in response.context

    def test_post_editar_calibracion_valido_redirige(
        self, authenticated_client, calibracion_factory, equipo_factory
    ):
        """POST con form válido actualiza la calibración y redirige."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)
        calibracion = calibracion_factory(equipo=equipo)

        url = reverse('core:editar_calibracion', kwargs={'equipo_pk': equipo.pk, 'pk': calibracion.pk})
        data = {
            'fecha_calibracion': (date.today() - timedelta(days=10)).strftime('%Y-%m-%d'),
            'resultado': 'Aprobado',
            'nombre_proveedor': 'Laboratorio Actualizado SA',
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == 302
        calibracion.refresh_from_db()
        assert calibracion.resultado == 'Aprobado'
        assert calibracion.nombre_proveedor == 'Laboratorio Actualizado SA'

    def test_get_editar_calibracion_superuser(
        self, admin_client, calibracion_factory, equipo_factory
    ):
        """Superuser puede editar calibración de cualquier empresa (línea 109)."""
        equipo = equipo_factory()  # empresa distinta al superuser
        calibracion = calibracion_factory(equipo=equipo)

        url = reverse('core:editar_calibracion', kwargs={'equipo_pk': equipo.pk, 'pk': calibracion.pk})
        response = admin_client.get(url)

        assert response.status_code == 200


# =============================================================================
# ELIMINAR CALIBRACIÓN
# =============================================================================

@pytest.mark.django_db
class TestEliminarCalibracionCobertura:
    """Cubrir eliminar_calibracion (152, 163-175)."""

    def test_get_eliminar_calibracion_muestra_confirmacion(
        self, authenticated_client, calibracion_factory, equipo_factory
    ):
        """GET muestra página de confirmación."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)
        calibracion = calibracion_factory(equipo=equipo)

        url = reverse('core:eliminar_calibracion', kwargs={'equipo_pk': equipo.pk, 'pk': calibracion.pk})
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert 'object_name' in response.context

    def test_post_eliminar_calibracion_exitoso(
        self, authenticated_client, calibracion_factory, equipo_factory
    ):
        """POST elimina la calibración y redirige."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)
        calibracion = calibracion_factory(equipo=equipo)
        calibracion_pk = calibracion.pk

        url = reverse('core:eliminar_calibracion', kwargs={'equipo_pk': equipo.pk, 'pk': calibracion.pk})
        response = authenticated_client.post(url)

        assert response.status_code == 302
        assert not Calibracion.objects.filter(pk=calibracion_pk).exists()

    def test_get_eliminar_calibracion_superuser(
        self, admin_client, calibracion_factory, equipo_factory
    ):
        """Superuser puede eliminar calibración de cualquier empresa (línea 152)."""
        equipo = equipo_factory()
        calibracion = calibracion_factory(equipo=equipo)

        url = reverse('core:eliminar_calibracion', kwargs={'equipo_pk': equipo.pk, 'pk': calibracion.pk})
        response = admin_client.get(url)

        assert response.status_code == 200


# =============================================================================
# EDITAR MANTENIMIENTO
# =============================================================================

@pytest.mark.django_db
class TestEditarMantenimientoCobertura:
    """Cubrir editar_mantenimiento (260, 263-287)."""

    def test_get_editar_mantenimiento_muestra_formulario(
        self, authenticated_client, mantenimiento_factory, equipo_factory
    ):
        """GET muestra el formulario de edición prellenado."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)
        mantenimiento = mantenimiento_factory(equipo=equipo)

        url = reverse('core:editar_mantenimiento', kwargs={'equipo_pk': equipo.pk, 'pk': mantenimiento.pk})
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert 'form' in response.context
        assert 'mantenimiento' in response.context

    def test_post_editar_mantenimiento_valido_redirige(
        self, authenticated_client, mantenimiento_factory, equipo_factory
    ):
        """POST con form válido actualiza el mantenimiento y redirige."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)
        mantenimiento = mantenimiento_factory(equipo=equipo)

        url = reverse('core:editar_mantenimiento', kwargs={'equipo_pk': equipo.pk, 'pk': mantenimiento.pk})
        data = {
            'fecha_mantenimiento': (date.today() - timedelta(days=5)).strftime('%Y-%m-%d'),
            'tipo_mantenimiento': 'Correctivo',
            'descripcion': 'Mantenimiento correctivo actualizado',
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == 302
        mantenimiento.refresh_from_db()
        assert mantenimiento.tipo_mantenimiento == 'Correctivo'

    def test_post_editar_mantenimiento_invalido_remuestra_form(
        self, authenticated_client, mantenimiento_factory, equipo_factory
    ):
        """POST con form inválido re-renderiza el formulario."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)
        mantenimiento = mantenimiento_factory(equipo=equipo)

        url = reverse('core:editar_mantenimiento', kwargs={'equipo_pk': equipo.pk, 'pk': mantenimiento.pk})
        data = {
            'fecha_mantenimiento': '',  # campo requerido vacío
            'tipo_mantenimiento': 'Preventivo',
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == 200
        assert 'form' in response.context

    def test_get_editar_mantenimiento_superuser(
        self, admin_client, mantenimiento_factory, equipo_factory
    ):
        """Superuser puede editar mantenimiento sin filtrar por empresa (línea 260)."""
        equipo = equipo_factory()
        mantenimiento = mantenimiento_factory(equipo=equipo)

        url = reverse('core:editar_mantenimiento', kwargs={'equipo_pk': equipo.pk, 'pk': mantenimiento.pk})
        response = admin_client.get(url)

        assert response.status_code == 200


# =============================================================================
# ELIMINAR MANTENIMIENTO
# =============================================================================

@pytest.mark.django_db
class TestEliminarMantenimientoCobertura:
    """Cubrir eliminar_mantenimiento (304-328)."""

    def test_get_eliminar_mantenimiento_muestra_confirmacion(
        self, authenticated_client, mantenimiento_factory, equipo_factory
    ):
        """GET muestra página de confirmación de eliminación."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)
        mantenimiento = mantenimiento_factory(equipo=equipo)

        url = reverse('core:eliminar_mantenimiento', kwargs={'equipo_pk': equipo.pk, 'pk': mantenimiento.pk})
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert 'object_name' in response.context

    def test_post_eliminar_mantenimiento_exitoso(
        self, authenticated_client, mantenimiento_factory, equipo_factory
    ):
        """POST elimina el mantenimiento y redirige."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)
        mantenimiento = mantenimiento_factory(equipo=equipo)
        mantenimiento_pk = mantenimiento.pk

        url = reverse('core:eliminar_mantenimiento', kwargs={'equipo_pk': equipo.pk, 'pk': mantenimiento.pk})
        response = authenticated_client.post(url)

        assert response.status_code == 302
        assert not Mantenimiento.objects.filter(pk=mantenimiento_pk).exists()

    def test_get_eliminar_mantenimiento_superuser(
        self, admin_client, mantenimiento_factory, equipo_factory
    ):
        """Superuser puede eliminar mantenimiento de cualquier empresa (línea 304)."""
        equipo = equipo_factory()
        mantenimiento = mantenimiento_factory(equipo=equipo)

        url = reverse('core:eliminar_mantenimiento', kwargs={'equipo_pk': equipo.pk, 'pk': mantenimiento.pk})
        response = admin_client.get(url)

        assert response.status_code == 200


# =============================================================================
# DETALLE MANTENIMIENTO
# =============================================================================

@pytest.mark.django_db
class TestDetalleMantenimientoCobertura:
    """Cubrir detalle_mantenimiento (340-355)."""

    def test_get_detalle_mantenimiento_muestra_detalle(
        self, authenticated_client, mantenimiento_factory, equipo_factory
    ):
        """GET muestra los detalles de un mantenimiento."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)
        mantenimiento = mantenimiento_factory(equipo=equipo)

        url = reverse('core:detalle_mantenimiento', kwargs={'equipo_pk': equipo.pk, 'pk': mantenimiento.pk})
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert 'mantenimiento' in response.context
        assert 'equipo' in response.context

    def test_get_detalle_mantenimiento_superuser(
        self, admin_client, mantenimiento_factory, equipo_factory
    ):
        """Superuser puede ver detalle sin filtro de empresa (línea 341)."""
        equipo = equipo_factory()
        mantenimiento = mantenimiento_factory(equipo=equipo)

        url = reverse('core:detalle_mantenimiento', kwargs={'equipo_pk': equipo.pk, 'pk': mantenimiento.pk})
        response = admin_client.get(url)

        assert response.status_code == 200


# =============================================================================
# EDITAR COMPROBACIÓN
# =============================================================================

@pytest.mark.django_db
class TestEditarComprobacionCobertura:
    """Cubrir editar_comprobacion (439-467)."""

    def test_get_editar_comprobacion_muestra_formulario(
        self, authenticated_client, comprobacion_factory, equipo_factory
    ):
        """GET muestra el formulario prellenado."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)
        comprobacion = comprobacion_factory(equipo=equipo)

        url = reverse('core:editar_comprobacion', kwargs={'equipo_pk': equipo.pk, 'pk': comprobacion.pk})
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert 'form' in response.context
        assert 'comprobacion' in response.context

    def test_post_editar_comprobacion_valido_redirige(
        self, authenticated_client, comprobacion_factory, equipo_factory
    ):
        """POST con form válido actualiza la comprobación y redirige."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)
        comprobacion = comprobacion_factory(equipo=equipo)

        url = reverse('core:editar_comprobacion', kwargs={'equipo_pk': equipo.pk, 'pk': comprobacion.pk})
        data = {
            'fecha_comprobacion': (date.today() - timedelta(days=3)).strftime('%Y-%m-%d'),
            'resultado': 'No Aprobado',
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == 302
        comprobacion.refresh_from_db()
        assert comprobacion.resultado == 'No Aprobado'

    def test_post_editar_comprobacion_invalido_remuestra_form(
        self, authenticated_client, comprobacion_factory, equipo_factory
    ):
        """POST con form inválido re-renderiza el formulario."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)
        comprobacion = comprobacion_factory(equipo=equipo)

        url = reverse('core:editar_comprobacion', kwargs={'equipo_pk': equipo.pk, 'pk': comprobacion.pk})
        data = {
            'fecha_comprobacion': '',  # inválido
            'resultado': 'Aprobado',
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == 200
        assert 'form' in response.context

    def test_get_editar_comprobacion_superuser(
        self, admin_client, comprobacion_factory, equipo_factory
    ):
        """Superuser puede editar comprobación sin filtrar por empresa (línea 439)."""
        equipo = equipo_factory()
        comprobacion = comprobacion_factory(equipo=equipo)

        url = reverse('core:editar_comprobacion', kwargs={'equipo_pk': equipo.pk, 'pk': comprobacion.pk})
        response = admin_client.get(url)

        assert response.status_code == 200


# =============================================================================
# ELIMINAR COMPROBACIÓN
# =============================================================================

@pytest.mark.django_db
class TestEliminarComprobacionCobertura:
    """Cubrir eliminar_comprobacion (485, 496-508)."""

    def test_get_eliminar_comprobacion_muestra_confirmacion(
        self, authenticated_client, comprobacion_factory, equipo_factory
    ):
        """GET muestra página de confirmación."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)
        comprobacion = comprobacion_factory(equipo=equipo)

        url = reverse('core:eliminar_comprobacion', kwargs={'equipo_pk': equipo.pk, 'pk': comprobacion.pk})
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert 'object_name' in response.context

    def test_post_eliminar_comprobacion_exitoso(
        self, authenticated_client, comprobacion_factory, equipo_factory
    ):
        """POST elimina la comprobación y redirige."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)
        comprobacion = comprobacion_factory(equipo=equipo)
        comprobacion_pk = comprobacion.pk

        url = reverse('core:eliminar_comprobacion', kwargs={'equipo_pk': equipo.pk, 'pk': comprobacion.pk})
        response = authenticated_client.post(url)

        assert response.status_code == 302
        assert not Comprobacion.objects.filter(pk=comprobacion_pk).exists()

    def test_get_eliminar_comprobacion_superuser(
        self, admin_client, comprobacion_factory, equipo_factory
    ):
        """Superuser puede eliminar comprobación de cualquier empresa (línea 485)."""
        equipo = equipo_factory()
        comprobacion = comprobacion_factory(equipo=equipo)

        url = reverse('core:eliminar_comprobacion', kwargs={'equipo_pk': equipo.pk, 'pk': comprobacion.pk})
        response = admin_client.get(url)

        assert response.status_code == 200


# =============================================================================
# AÑADIR CALIBRACIÓN - Ramas de error (form inválido + superuser)
# =============================================================================

@pytest.mark.django_db
class TestAñadirCalibracionFormInvalidoCobertura:
    """Cubrir ramas de añadir_calibracion: form inválido (66-84) y superuser (26)."""

    def test_post_añadir_calibracion_form_invalido_log(
        self, authenticated_client, equipo_factory
    ):
        """POST con form inválido ejecuta la rama de logging de errores (66-84)."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)

        url = reverse('core:añadir_calibracion', kwargs={'equipo_pk': equipo.pk})
        data = {
            # Falta 'resultado' (requerido) y proveedor/nombre_proveedor
            'fecha_calibracion': (date.today() - timedelta(days=5)).strftime('%Y-%m-%d'),
        }
        response = authenticated_client.post(url, data)

        # El form es inválido → re-renderiza con errores
        assert response.status_code == 200

    def test_get_añadir_calibracion_superuser(
        self, admin_client, equipo_factory
    ):
        """Superuser accede al form de calibración sin filtrar por empresa (línea 26)."""
        equipo = equipo_factory()

        url = reverse('core:añadir_calibracion', kwargs={'equipo_pk': equipo.pk})
        response = admin_client.get(url)

        assert response.status_code == 200
        assert 'form' in response.context


# =============================================================================
# AÑADIR MANTENIMIENTO - Ramas de error (form inválido + superuser)
# =============================================================================

@pytest.mark.django_db
class TestAñadirMantenimientoFormInvalidoCobertura:
    """Cubrir ramas de añadir_mantenimiento: form inválido (222-237) y superuser (193)."""

    def test_post_añadir_mantenimiento_form_invalido_log(
        self, authenticated_client, equipo_factory
    ):
        """POST con form inválido ejecuta la rama de logging de errores (222-237)."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)

        url = reverse('core:añadir_mantenimiento', kwargs={'equipo_pk': equipo.pk})
        data = {
            # Falta 'tipo_mantenimiento' (requerido) y 'fecha_mantenimiento'
            'descripcion': 'Descripción sin tipo ni fecha',
        }
        response = authenticated_client.post(url, data)

        # Form inválido → re-renderiza
        assert response.status_code == 200

    def test_get_añadir_mantenimiento_superuser(
        self, admin_client, equipo_factory
    ):
        """Superuser accede al form de mantenimiento sin filtrar por empresa (línea 193)."""
        equipo = equipo_factory()

        url = reverse('core:añadir_mantenimiento', kwargs={'equipo_pk': equipo.pk})
        response = admin_client.get(url)

        assert response.status_code == 200
        assert 'form' in response.context


# =============================================================================
# AÑADIR COMPROBACIÓN - Ramas de error (form inválido + superuser)
# =============================================================================

@pytest.mark.django_db
class TestAñadirComprobacionFormInvalidoCobertura:
    """Cubrir ramas de añadir_comprobacion: form inválido (402-417) y superuser (373)."""

    def test_post_añadir_comprobacion_form_invalido_log(
        self, authenticated_client, equipo_factory
    ):
        """POST con form inválido ejecuta la rama de logging de errores (402-417)."""
        user = authenticated_client.user
        equipo = equipo_factory(empresa=user.empresa)

        url = reverse('core:añadir_comprobacion', kwargs={'equipo_pk': equipo.pk})
        data = {
            # Falta 'resultado' (requerido)
            'fecha_comprobacion': (date.today() - timedelta(days=2)).strftime('%Y-%m-%d'),
        }
        response = authenticated_client.post(url, data)

        # Form inválido → re-renderiza
        assert response.status_code == 200

    def test_get_añadir_comprobacion_superuser(
        self, admin_client, equipo_factory
    ):
        """Superuser accede al form de comprobación sin filtrar por empresa (línea 373)."""
        equipo = equipo_factory()

        url = reverse('core:añadir_comprobacion', kwargs={'equipo_pk': equipo.pk})
        response = admin_client.get(url)

        assert response.status_code == 200
        assert 'form' in response.context
