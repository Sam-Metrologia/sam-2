"""
Tests para core.admin_views.reporte_validacion_software.

Cubre sobre todo que las cifras que antes estaban escritas a mano
(cobertura total, cobertura por módulo, conteo de scripts inline) ahora
se calculan en vivo y nunca rompen la vista, con o sin archivo .coverage
presente en disco.
"""
import pytest
from django.urls import reverse

from tests.factories import UserFactory


@pytest.mark.django_db
class TestReporteValidacionSoftwareAcceso:

    def test_requiere_login(self, client):
        response = client.get(reverse('core:reporte_validacion_software'))
        assert response.status_code == 302

    def test_usuario_normal_no_puede_acceder(self, client):
        user = UserFactory(is_superuser=False, is_staff=False)
        client.force_login(user)
        response = client.get(reverse('core:reporte_validacion_software'))
        assert response.status_code == 302

    def test_superusuario_ve_el_reporte(self, client):
        user = UserFactory(is_superuser=True, is_staff=True)
        client.force_login(user)
        response = client.get(reverse('core:reporte_validacion_software'))
        assert response.status_code == 200


@pytest.mark.django_db
class TestCoberturaYScriptsEnVivo:

    def _superusuario(self, client):
        user = UserFactory(is_superuser=True, is_staff=True)
        client.force_login(user)
        return user

    def test_cobertura_info_tiene_la_forma_esperada(self, client):
        self._superusuario(client)
        response = client.get(reverse('core:reporte_validacion_software'))

        cobertura_info = response.context['cobertura_info']
        assert set(cobertura_info.keys()) == {'disponible', 'total_pct', 'medido_en', 'por_modulo'}
        assert isinstance(cobertura_info['disponible'], bool)

        if cobertura_info['disponible']:
            # Si hay archivo .coverage en disco, debe traer cifras reales, no texto fijo.
            assert isinstance(cobertura_info['total_pct'], float)
            assert cobertura_info['medido_en'] is not None
        else:
            assert cobertura_info['total_pct'] is None

    def test_scripts_inline_count_es_un_entero_no_negativo(self, client):
        self._superusuario(client)
        response = client.get(reverse('core:reporte_validacion_software'))

        count = response.context['scripts_inline_count']
        assert count is None or (isinstance(count, int) and count >= 0)

    def test_sin_archivo_coverage_no_rompe_la_vista(self, client, monkeypatch, tmp_path):
        """Si .coverage no existe (proyecto recién clonado, CI limpio), la vista
        debe seguir cargando y mostrar 'no disponible', nunca un error 500."""
        self._superusuario(client)

        import pathlib
        original_exists = pathlib.Path.exists

        def _fake_exists(self):
            if self.name == '.coverage':
                return False
            return original_exists(self)

        monkeypatch.setattr(pathlib.Path, 'exists', _fake_exists)

        response = client.get(reverse('core:reporte_validacion_software'))

        assert response.status_code == 200
        assert response.context['cobertura_info']['disponible'] is False
        assert response.context['cobertura_info']['total_pct'] is None
