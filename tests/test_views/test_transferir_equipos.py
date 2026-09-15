"""
Tests para core.views.companies.transferir_equipos — mover equipos entre
sedes de la misma empresa matriz.
"""
import pytest
from django.urls import reverse

from core.constants import ESTADO_DE_BAJA, PRESTAMO_ACTIVO
from core.models import PrestamoEquipo, TransferenciaEquipo
from tests.factories import EmpresaFactory, EquipoFactory, UserFactory


@pytest.mark.django_db
class TestTransferirEquiposAcceso:

    def test_requiere_login(self, client):
        response = client.get(reverse('core:transferir_equipos'))
        assert response.status_code == 302
        assert reverse('core:login') in response.url

    def test_usuario_sin_sedes_no_puede_acceder(self, client):
        empresa = EmpresaFactory()
        user = UserFactory(empresa=empresa, rol_usuario='TECNICO')
        client.force_login(user)

        response = client.get(reverse('core:transferir_equipos'), follow=True)

        assert response.status_code == 200
        assert response.redirect_chain[-1][0] == reverse('core:dashboard')
        mensajes = [str(m) for m in response.context['messages']]
        assert any('No tienes sedes' in m for m in mensajes)

    def test_gerente_de_matriz_ve_formulario_con_equipos_de_su_sede(self, client):
        matriz = EmpresaFactory()
        sede_a = EmpresaFactory(empresa_matriz=matriz)
        user = UserFactory(empresa=matriz, rol_usuario='GERENCIA')
        client.force_login(user)
        equipo = EquipoFactory(empresa=matriz)

        response = client.get(reverse('core:transferir_equipos'))

        assert response.status_code == 200
        assert equipo in response.context['equipos']
        assert sede_a in response.context['destinos_posibles']


@pytest.mark.django_db
class TestTransferirEquiposEjecucion:

    def _gerente_con_matriz_y_sede(self):
        matriz = EmpresaFactory(limite_equipos_empresa=100)
        sede_a = EmpresaFactory(empresa_matriz=matriz, limite_equipos_empresa=100)
        user = UserFactory(empresa=matriz, rol_usuario='GERENCIA')
        return matriz, sede_a, user

    def test_transferencia_exitosa_sin_conflicto(self, client):
        matriz, sede_a, user = self._gerente_con_matriz_y_sede()
        client.force_login(user)
        equipo = EquipoFactory(empresa=matriz, codigo_interno='EQ-001')

        response = client.post(reverse('core:transferir_equipos'), {
            'empresa_destino': sede_a.id,
            'equipos': [equipo.pk],
        })

        equipo.refresh_from_db()
        assert response.status_code == 302
        assert equipo.empresa_id == sede_a.id
        assert equipo.codigo_interno == 'EQ-001'  # no cambió, no había choque

        transferencia = TransferenciaEquipo.objects.get(equipo=equipo)
        assert transferencia.empresa_origen_id == matriz.id
        assert transferencia.empresa_destino_id == sede_a.id
        assert transferencia.codigo_interno_nuevo is None
        assert transferencia.realizado_por == user

    def test_equipo_con_prestamo_activo_se_mueve_sin_bloquear(self, client):
        """Decisión de negocio: no se bloquea la transferencia por préstamo activo."""
        matriz, sede_a, user = self._gerente_con_matriz_y_sede()
        client.force_login(user)
        equipo = EquipoFactory(empresa=matriz, codigo_interno='EQ-002')
        prestamo = PrestamoEquipo.objects.create(
            equipo=equipo, empresa=matriz,
            nombre_prestatario='Juan Pérez', estado_prestamo=PRESTAMO_ACTIVO,
        )

        response = client.post(reverse('core:transferir_equipos'), {
            'empresa_destino': sede_a.id,
            'equipos': [equipo.pk],
        })

        equipo.refresh_from_db()
        prestamo.refresh_from_db()
        assert response.status_code == 302
        assert equipo.empresa_id == sede_a.id
        assert prestamo.empresa_id == sede_a.id  # se actualizó junto con el equipo
        assert prestamo.estado_prestamo == PRESTAMO_ACTIVO  # sigue activo, no se tocó

    def test_codigo_duplicado_en_destino_pide_resolucion_y_no_mueve(self, client):
        matriz, sede_a, user = self._gerente_con_matriz_y_sede()
        client.force_login(user)
        equipo = EquipoFactory(empresa=matriz, codigo_interno='EQ-DUP')
        EquipoFactory(empresa=sede_a, codigo_interno='EQ-DUP')  # ya existe en destino

        response = client.post(reverse('core:transferir_equipos'), {
            'empresa_destino': sede_a.id,
            'equipos': [equipo.pk],
        })

        equipo.refresh_from_db()
        assert response.status_code == 200  # se re-renderiza, no redirige
        assert equipo.empresa_id == matriz.id  # no se movió
        assert equipo in response.context['conflictos']
        assert not TransferenciaEquipo.objects.filter(equipo=equipo).exists()

    def test_codigo_duplicado_se_resuelve_con_codigo_nuevo(self, client):
        matriz, sede_a, user = self._gerente_con_matriz_y_sede()
        client.force_login(user)
        equipo = EquipoFactory(empresa=matriz, codigo_interno='EQ-DUP2')
        EquipoFactory(empresa=sede_a, codigo_interno='EQ-DUP2')

        response = client.post(reverse('core:transferir_equipos'), {
            'empresa_destino': sede_a.id,
            'equipos': [equipo.pk],
            f'codigo_nuevo_{equipo.pk}': 'EQ-DUP2-NORTE',
        })

        equipo.refresh_from_db()
        assert response.status_code == 302
        assert equipo.empresa_id == sede_a.id
        assert equipo.codigo_interno == 'EQ-DUP2-NORTE'

        transferencia = TransferenciaEquipo.objects.get(equipo=equipo)
        assert transferencia.codigo_interno_anterior == 'EQ-DUP2'
        assert transferencia.codigo_interno_nuevo == 'EQ-DUP2-NORTE'

    def test_no_puede_transferir_a_empresa_ajena(self, client):
        matriz, sede_a, user = self._gerente_con_matriz_y_sede()
        client.force_login(user)
        empresa_ajena = EmpresaFactory()
        equipo = EquipoFactory(empresa=matriz)

        response = client.post(reverse('core:transferir_equipos'), {
            'empresa_destino': empresa_ajena.id,
            'equipos': [equipo.pk],
        })

        equipo.refresh_from_db()
        assert equipo.empresa_id == matriz.id  # no se movió
        mensajes = [str(m) for m in response.context['messages']]
        assert any('sede destino válida' in m for m in mensajes)

    def test_respeta_cupo_de_equipos_en_destino(self, client):
        matriz = EmpresaFactory(limite_equipos_empresa=100)
        sede_a = EmpresaFactory(empresa_matriz=matriz, limite_equipos_empresa=1)
        EquipoFactory(empresa=sede_a)  # ya está en el cupo (1/1)
        user = UserFactory(empresa=matriz, rol_usuario='GERENCIA')
        client.force_login(user)
        equipo = EquipoFactory(empresa=matriz)

        response = client.post(reverse('core:transferir_equipos'), {
            'empresa_destino': sede_a.id,
            'equipos': [equipo.pk],
        })

        equipo.refresh_from_db()
        assert equipo.empresa_id == matriz.id  # no se movió, sin cupo
        mensajes = [str(m) for m in response.context['messages']]
        assert any('no tiene cupo suficiente' in m for m in mensajes)

    def test_equipo_dado_de_baja_no_se_puede_transferir_aunque_se_fuerce_el_id(self, client):
        matriz, sede_a, user = self._gerente_con_matriz_y_sede()
        client.force_login(user)
        equipo = EquipoFactory(empresa=matriz, estado=ESTADO_DE_BAJA)

        response = client.post(reverse('core:transferir_equipos'), {
            'empresa_destino': sede_a.id,
            'equipos': [equipo.pk],
        })

        equipo.refresh_from_db()
        assert equipo.empresa_id == matriz.id  # no se movió
        mensajes = [str(m) for m in response.context['messages']]
        assert any('Ninguno de los equipos seleccionados' in m for m in mensajes)

    def test_dos_equipos_con_el_mismo_codigo_nuevo_no_revientan_con_500(self, client):
        """
        Si el código de dos equipos choca en destino y el usuario les pone el
        MISMO código nuevo a ambos, no debe reventar con IntegrityError/500 —
        debe pedir que se resuelva, igual que un choque contra la base de datos.
        """
        matriz, sede_a, user = self._gerente_con_matriz_y_sede()
        client.force_login(user)
        equipo_1 = EquipoFactory(empresa=matriz, codigo_interno='EQ-DUP-A')
        equipo_2 = EquipoFactory(empresa=matriz, codigo_interno='EQ-DUP-B')
        EquipoFactory(empresa=sede_a, codigo_interno='EQ-DUP-A')
        EquipoFactory(empresa=sede_a, codigo_interno='EQ-DUP-B')

        response = client.post(reverse('core:transferir_equipos'), {
            'empresa_destino': sede_a.id,
            'equipos': [equipo_1.pk, equipo_2.pk],
            f'codigo_nuevo_{equipo_1.pk}': 'EQ-REPETIDO',
            f'codigo_nuevo_{equipo_2.pk}': 'EQ-REPETIDO',
        })

        assert response.status_code == 200  # nunca 500
        equipo_1.refresh_from_db()
        equipo_2.refresh_from_db()
        assert equipo_1.empresa_id == matriz.id  # ninguno se movió
        assert equipo_2.empresa_id == matriz.id
        assert equipo_1 in response.context['conflictos'] or equipo_2 in response.context['conflictos']

    def test_codigos_nuevos_distintos_para_dos_equipos_si_funciona(self, client):
        """Caso normal: dos equipos con choque, cada uno con un código nuevo distinto."""
        matriz, sede_a, user = self._gerente_con_matriz_y_sede()
        client.force_login(user)
        equipo_1 = EquipoFactory(empresa=matriz, codigo_interno='EQ-DUP-C')
        equipo_2 = EquipoFactory(empresa=matriz, codigo_interno='EQ-DUP-D')
        EquipoFactory(empresa=sede_a, codigo_interno='EQ-DUP-C')
        EquipoFactory(empresa=sede_a, codigo_interno='EQ-DUP-D')

        response = client.post(reverse('core:transferir_equipos'), {
            'empresa_destino': sede_a.id,
            'equipos': [equipo_1.pk, equipo_2.pk],
            f'codigo_nuevo_{equipo_1.pk}': 'EQ-NUEVO-1',
            f'codigo_nuevo_{equipo_2.pk}': 'EQ-NUEVO-2',
        })

        assert response.status_code == 302
        equipo_1.refresh_from_db()
        equipo_2.refresh_from_db()
        assert equipo_1.empresa_id == sede_a.id
        assert equipo_2.empresa_id == sede_a.id
        assert equipo_1.codigo_interno == 'EQ-NUEVO-1'
        assert equipo_2.codigo_interno == 'EQ-NUEVO-2'
