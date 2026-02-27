"""
Tests para el Módulo C: Pagos con Wompi.
Cubre: página de planes, inicio de pago, resultado, webhook de confirmación,
validación de firma, idempotencia, activación de plan, banners de vencimiento.
"""
import hashlib
import json
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from core.models import Empresa, TransaccionPago
from core.views.pagos import (
    ADDONS,
    PLANES,
    TIERS_ORDENADOS,
    _calcular_firma_integridad,
    _validar_firma_webhook,
)

# URL helper adicional
def _url_addon():
    return reverse('core:iniciar_addon_pago')


# ============================================================================
# Helpers y fixtures locales
# ============================================================================

def _url(name, **kwargs):
    return reverse(f'core:{name}', kwargs=kwargs)


@pytest.fixture
def client_empresa(db):
    """
    Retorna (client_autenticado, empresa) vinculados al mismo usuario.
    Necesario para tests que crean transacciones y luego las consultan via vista.
    """
    from tests.factories import EmpresaFactory, UserFactory
    empresa = EmpresaFactory(fecha_inicio_plan=timezone.now().date())
    user = UserFactory(empresa=empresa)
    c = Client()
    c.login(username=user.username, password='testpass123')
    return c, empresa


def _make_webhook_payload(referencia, estado='APPROVED', amount_in_cents=23800000):
    """Construye un payload de webhook Wompi válido."""
    return {
        'event': 'transaction.updated',
        'data': {
            'transaction': {
                'id': 'wompi_tx_001',
                'status': estado,
                'amount_in_cents': amount_in_cents,
                'reference': referencia,
                'currency': 'COP',
                'payment_method_type': 'PSE',
            }
        },
        'environment': 'test',
        'signature': {
            'properties': ['transaction.id', 'transaction.status', 'transaction.amount_in_cents'],
            'checksum': '',  # se sobreescribe en los tests que validan firma
        },
        'timestamp': 1700000000,
    }


def _firmar_payload(payload, events_secret):
    """Genera el checksum correcto para un payload de webhook."""
    transaction = payload['data']['transaction']
    props = payload['signature']['properties']
    valores = []
    for prop in props:
        partes = prop.split('.')
        valor = payload
        for parte in partes:
            valor = valor.get(parte, {}) if isinstance(valor, dict) else ''
        valores.append(str(valor))
    cadena = ''.join(valores) + events_secret
    return hashlib.sha256(cadena.encode('utf-8')).hexdigest()


# ============================================================================
# C4 — Página de Planes
# ============================================================================

@pytest.mark.django_db
class TestPaginaPlanes:

    def test_requiere_autenticacion(self, client):
        """Página de planes redirige a login si no está autenticado."""
        response = client.get(_url('planes'))
        assert response.status_code == 302
        assert '/login/' in response['Location']

    def test_muestra_planes_autenticado(self, authenticated_client):
        """Usuario autenticado puede ver la página de planes con los precios."""
        response = authenticated_client.get(_url('planes'))
        assert response.status_code == 200
        assert 'planes' in response.context
        assert 'MENSUAL' in response.context['planes']
        assert 'ANUAL' in response.context['planes']

    def test_precio_mensual_correcto(self, authenticated_client):
        """El plan mensual tiene precio base de $200.000 COP."""
        response = authenticated_client.get(_url('planes'))
        plan_mensual = response.context['planes']['MENSUAL']
        assert plan_mensual['precio_base'] == Decimal('200000')

    def test_precio_anual_correcto(self, authenticated_client):
        """El plan anual tiene precio base de $2.000.000 COP."""
        response = authenticated_client.get(_url('planes'))
        plan_anual = response.context['planes']['ANUAL']
        assert plan_anual['precio_base'] == Decimal('2000000')

    def test_precios_incluyen_iva(self, authenticated_client):
        """Los precios totales incluyen IVA del 19%."""
        response = authenticated_client.get(_url('planes'))
        planes = response.context['planes']
        mensual = planes['MENSUAL']
        assert mensual['precio_total'] == Decimal('238000')
        anual = planes['ANUAL']
        assert anual['precio_total'] == Decimal('2380000')

    def test_muestra_estado_trial_activo(self, authenticated_client):
        """Muestra los días restantes cuando el trial está activo."""
        response = authenticated_client.get(_url('planes'))
        assert response.status_code == 200
        # El usuario autenticado del fixture tiene empresa en trial por defecto
        assert 'estado_plan' in response.context

    def test_context_incluye_tiers(self, authenticated_client):
        """La vista envía la lista de tiers ordenados para el template."""
        response = authenticated_client.get(_url('planes'))
        assert 'tiers' in response.context
        assert len(response.context['tiers']) == 4  # Básico, Estándar, Profesional, Empresarial

    def test_cuatro_tiers_presentes_en_planes(self):
        """PLANES contiene los 8 keys (4 tiers × mensual/anual)."""
        expected_keys = {
            'BASICO_MENSUAL', 'BASICO_ANUAL',
            'MENSUAL', 'ANUAL',
            'PRO_MENSUAL', 'PRO_ANUAL',
            'ENTERPRISE_MENSUAL', 'ENTERPRISE_ANUAL',
        }
        assert expected_keys == set(PLANES.keys())

    def test_precios_tiers_con_iva(self):
        """Cada tier tiene precio_total = precio_base × 1.19."""
        for key, plan in PLANES.items():
            esperado = plan['precio_base'] * Decimal('1.19')
            assert plan['precio_total'] == esperado.quantize(Decimal('1')), \
                f"Fallo en precio_total para {key}"

    def test_plan_basico_50_equipos(self):
        """Plan Básico cubre 50 equipos a $80.000/mes."""
        assert PLANES['BASICO_MENSUAL']['equipos'] == 50
        assert PLANES['BASICO_MENSUAL']['precio_base'] == Decimal('80000')

    def test_plan_pro_500_equipos(self):
        """Plan Profesional cubre 500 equipos a $380.000/mes."""
        assert PLANES['PRO_MENSUAL']['equipos'] == 500
        assert PLANES['PRO_MENSUAL']['precio_base'] == Decimal('380000')

    def test_plan_enterprise_1000_equipos(self):
        """Plan Empresarial cubre 1000 equipos a $650.000/mes."""
        assert PLANES['ENTERPRISE_MENSUAL']['equipos'] == 1000
        assert PLANES['ENTERPRISE_MENSUAL']['precio_base'] == Decimal('650000')

    def test_todos_los_planes_tienen_3_usuarios(self):
        """Todos los tiers incluyen exactamente 3 usuarios base."""
        for key, plan in PLANES.items():
            assert plan['usuarios'] == 3, \
                f"Plan {key} tiene {plan['usuarios']} usuarios, esperado 3"

    def test_addons_disponibles(self):
        """Existen los 5 add-ons: técnico, admin, gerente, equipos, storage."""
        assert 'usuario_tecnico' in ADDONS
        assert 'usuario_admin' in ADDONS
        assert 'usuario_gerente' in ADDONS
        assert 'equipos_50' in ADDONS
        assert 'storage_5gb' in ADDONS

    def test_addons_precios_por_rol(self):
        """Los precios de usuario reflejan la jerarquía de roles."""
        assert ADDONS['usuario_tecnico']['precio_base'] < ADDONS['usuario_admin']['precio_base']
        assert ADDONS['usuario_admin']['precio_base'] < ADDONS['usuario_gerente']['precio_base']

    def test_addons_incluyen_precio_con_iva(self):
        """Cada add-on tiene precio_total = precio_base × 1.19."""
        for key, addon in ADDONS.items():
            esperado = (addon['precio_base'] * Decimal('1.19')).quantize(Decimal('1'))
            assert addon['precio_total'] == esperado, \
                f"Add-on {key}: precio_total incorrecto"

    def test_context_incluye_addons(self, authenticated_client):
        """La vista planes envía los add-ons al template."""
        response = authenticated_client.get(_url('planes'))
        assert 'addons' in response.context
        assert len(response.context['addons']) == 5

    def test_planes_anuales_son_2_meses_gratis(self):
        """Plan anual equivale a 10 meses (2 gratis) en todos los tiers."""
        for key_m, key_a in TIERS_ORDENADOS:
            plan_m = PLANES[key_m]
            plan_a = PLANES[key_a]
            mensual_x12 = plan_m['precio_base'] * 12
            assert plan_a['precio_base'] < mensual_x12, \
                f"{key_a} no tiene descuento vs 12×{key_m}"
            ahorro = mensual_x12 - plan_a['precio_base']
            assert ahorro == plan_a['ahorro'], \
                f"Ahorro incorrecto en {key_a}: esperado {ahorro}, got {plan_a['ahorro']}"


# ============================================================================
# C5 — Inicio de Pago
# ============================================================================

@pytest.mark.django_db
class TestIniciarPago:

    def test_requiere_autenticacion(self, client):
        """POST a iniciar_pago redirige a login si no está autenticado."""
        response = client.post(_url('iniciar_pago'), {'plan': 'MENSUAL'})
        assert response.status_code == 302
        assert '/login/' in response['Location']

    def test_plan_invalido_redirige_con_error(self, authenticated_client):
        """Plan inválido redirige a planes con mensaje de error."""
        response = authenticated_client.post(_url('iniciar_pago'), {'plan': 'INVALIDO'})
        assert response.status_code == 302
        assert response['Location'].endswith(_url('planes'))

    @patch('core.views.pagos.settings')
    def test_sin_wompi_key_muestra_error(self, mock_settings, authenticated_client):
        """Sin WOMPI_PUBLIC_KEY configurado, muestra error y redirige a planes."""
        mock_settings.WOMPI_PUBLIC_KEY = ''
        mock_settings.WOMPI_INTEGRITY_SECRET = ''
        mock_settings.WOMPI_SANDBOX = True
        response = authenticated_client.post(_url('iniciar_pago'), {'plan': 'MENSUAL'})
        assert response.status_code == 302
        assert response['Location'].endswith(_url('planes'))

    @patch('core.views.pagos.settings')
    def test_crea_transaccion_pendiente(self, mock_settings, authenticated_client, sample_empresa):
        """Con WOMPI_PUBLIC_KEY válido, crea TransaccionPago con estado pendiente."""
        mock_settings.WOMPI_PUBLIC_KEY = 'pub_test_abc123'
        mock_settings.WOMPI_INTEGRITY_SECRET = 'integrity_secret_test'
        mock_settings.WOMPI_SANDBOX = True

        conteo_antes = TransaccionPago.objects.count()
        authenticated_client.post(_url('iniciar_pago'), {'plan': 'MENSUAL'})
        assert TransaccionPago.objects.count() == conteo_antes + 1

        tx = TransaccionPago.objects.latest('fecha_creacion')
        assert tx.estado == 'pendiente'
        assert tx.plan_seleccionado == 'MENSUAL'
        assert tx.moneda == 'COP'

    @patch('core.views.pagos.settings')
    def test_monto_transaccion_incluye_iva(self, mock_settings, authenticated_client):
        """El monto de la transacción incluye IVA."""
        mock_settings.WOMPI_PUBLIC_KEY = 'pub_test_abc123'
        mock_settings.WOMPI_INTEGRITY_SECRET = 'integrity_secret_test'
        mock_settings.WOMPI_SANDBOX = True

        authenticated_client.post(_url('iniciar_pago'), {'plan': 'MENSUAL'})
        tx = TransaccionPago.objects.latest('fecha_creacion')
        assert tx.monto == Decimal('238000')

    @patch('core.views.pagos.settings')
    def test_referencia_es_unica(self, mock_settings, authenticated_client):
        """Cada llamada a iniciar_pago genera una referencia única."""
        mock_settings.WOMPI_PUBLIC_KEY = 'pub_test_abc123'
        mock_settings.WOMPI_INTEGRITY_SECRET = 'integrity_secret_test'
        mock_settings.WOMPI_SANDBOX = True

        authenticated_client.post(_url('iniciar_pago'), {'plan': 'MENSUAL'})
        authenticated_client.post(_url('iniciar_pago'), {'plan': 'ANUAL'})
        txs = TransaccionPago.objects.order_by('-fecha_creacion')[:2]
        assert txs[0].referencia_pago != txs[1].referencia_pago

    @patch('core.views.pagos.settings')
    def test_redirige_a_wompi(self, mock_settings, authenticated_client):
        """Con credenciales configuradas, redirige al checkout de Wompi."""
        mock_settings.WOMPI_PUBLIC_KEY = 'pub_test_abc123'
        mock_settings.WOMPI_INTEGRITY_SECRET = 'integrity_secret_test'
        mock_settings.WOMPI_SANDBOX = True

        response = authenticated_client.post(_url('iniciar_pago'), {'plan': 'MENSUAL'})
        assert response.status_code == 302
        assert 'checkout.wompi.co' in response['Location']


# ============================================================================
# C7 — Resultado de Pago
# ============================================================================

@pytest.mark.django_db
class TestPagoResultado:

    def test_requiere_autenticacion(self, client):
        """Página de resultado redirige a login si no está autenticado."""
        response = client.get(_url('pago_resultado'))
        assert response.status_code == 302
        assert '/login/' in response['Location']

    def test_sin_referencia_muestra_no_encontrado(self, authenticated_client):
        """Sin referencia válida en query string, muestra 'transacción no encontrada'."""
        response = authenticated_client.get(_url('pago_resultado'))
        assert response.status_code == 200
        assert response.context['transaccion'] is None

    def test_referencia_inexistente_muestra_no_encontrado(self, authenticated_client):
        """Referencia que no existe en BD muestra 'no encontrada'."""
        response = authenticated_client.get(_url('pago_resultado') + '?ref=SAM-FAKE-REF')
        assert response.status_code == 200
        assert response.context['transaccion'] is None

    def test_muestra_transaccion_aprobada(self, client_empresa):
        """Si la transacción está aprobada, muestra pantalla de éxito."""
        c, empresa = client_empresa
        tx = TransaccionPago.objects.create(
            empresa=empresa,
            referencia_pago='SAM-TEST-APROBADA',
            estado='aprobado',
            monto=Decimal('238000'),
            plan_seleccionado='MENSUAL',
        )
        response = c.get(_url('pago_resultado') + f'?ref={tx.referencia_pago}')
        assert response.status_code == 200
        assert response.context['transaccion'] == tx
        assert response.context['transaccion'].estado == 'aprobado'

    def test_muestra_transaccion_rechazada(self, client_empresa):
        """Si la transacción está rechazada, muestra pantalla de fallo."""
        c, empresa = client_empresa
        tx = TransaccionPago.objects.create(
            empresa=empresa,
            referencia_pago='SAM-TEST-RECHAZADA',
            estado='rechazado',
            monto=Decimal('238000'),
            plan_seleccionado='MENSUAL',
        )
        response = c.get(_url('pago_resultado') + f'?ref={tx.referencia_pago}')
        assert response.status_code == 200
        assert response.context['transaccion'].estado == 'rechazado'

    def test_no_muestra_transaccion_de_otra_empresa(self, client_empresa):
        """Un usuario no puede ver el resultado de pago de otra empresa."""
        c, _ = client_empresa
        otra_empresa = Empresa.objects.create(
            nombre='Otra Empresa',
            nit='111222333-1',
            email='otra@empresa.com',
            fecha_inicio_plan=timezone.now().date(),
        )
        tx = TransaccionPago.objects.create(
            empresa=otra_empresa,
            referencia_pago='SAM-OTRA-EMPRESA',
            estado='aprobado',
            monto=Decimal('238000'),
            plan_seleccionado='MENSUAL',
        )
        response = c.get(_url('pago_resultado') + f'?ref={tx.referencia_pago}')
        # Debe mostrar "no encontrada" porque no pertenece a su empresa
        assert response.context['transaccion'] is None


# ============================================================================
# C6 — Webhook de Confirmación
# ============================================================================

@pytest.mark.django_db
class TestWompiWebhook:

    def _post_webhook(self, client, payload, events_secret=''):
        """Helper para enviar un webhook firmado."""
        if events_secret:
            checksum = _firmar_payload(payload, events_secret)
            payload['signature']['checksum'] = checksum
        return client.post(
            _url('wompi_webhook'),
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_get_retorna_405(self, client):
        """El webhook solo acepta POST."""
        response = client.get(_url('wompi_webhook'))
        assert response.status_code == 405

    def test_payload_invalido_retorna_400(self, client):
        """Payload JSON malformado retorna 400."""
        response = client.post(
            _url('wompi_webhook'),
            data='no-es-json',
            content_type='application/json',
        )
        assert response.status_code == 400

    @patch('core.views.pagos.settings')
    def test_firma_invalida_retorna_401(self, mock_settings, client, sample_empresa):
        """Webhook con firma incorrecta retorna 401."""
        mock_settings.WOMPI_EVENTS_SECRET = 'secreto_real'
        mock_settings.WOMPI_SANDBOX = True

        tx = TransaccionPago.objects.create(
            empresa=sample_empresa,
            referencia_pago='SAM-FIRMA-MAL',
            estado='pendiente',
            monto=Decimal('238000'),
            plan_seleccionado='MENSUAL',
        )
        payload = _make_webhook_payload(tx.referencia_pago)
        # Firma incorrecta — no generamos el checksum real
        payload['signature']['checksum'] = 'firma_completamente_incorrecta'
        response = client.post(
            _url('wompi_webhook'),
            data=json.dumps(payload),
            content_type='application/json',
        )
        assert response.status_code == 401

    @patch('core.views.pagos.settings')
    def test_pago_aprobado_activa_plan(self, mock_settings, client, sample_empresa):
        """Webhook APPROVED activa el plan de la empresa y marca transacción como aprobada."""
        mock_settings.WOMPI_EVENTS_SECRET = ''  # Sin validación de firma
        mock_settings.WOMPI_SANDBOX = True

        tx = TransaccionPago.objects.create(
            empresa=sample_empresa,
            referencia_pago='SAM-APROBADO-001',
            estado='pendiente',
            monto=Decimal('238000'),
            plan_seleccionado='MENSUAL',
        )
        payload = _make_webhook_payload(tx.referencia_pago, estado='APPROVED')

        response = self._post_webhook(client, payload)
        assert response.status_code == 200

        tx.refresh_from_db()
        assert tx.estado == 'aprobado'

        sample_empresa.refresh_from_db()
        assert not sample_empresa.es_periodo_prueba
        assert sample_empresa.estado_suscripcion == 'Activo'
        assert sample_empresa.limite_equipos_empresa == PLANES['MENSUAL']['equipos']

    @patch('core.views.pagos.settings')
    def test_pago_rechazado_no_activa_plan(self, mock_settings, client, sample_empresa):
        """Webhook DECLINED no activa el plan y marca transacción como rechazada."""
        mock_settings.WOMPI_EVENTS_SECRET = ''
        mock_settings.WOMPI_SANDBOX = True

        tx = TransaccionPago.objects.create(
            empresa=sample_empresa,
            referencia_pago='SAM-RECHAZADO-001',
            estado='pendiente',
            monto=Decimal('238000'),
            plan_seleccionado='MENSUAL',
        )
        estado_prueba_antes = sample_empresa.es_periodo_prueba

        payload = _make_webhook_payload(tx.referencia_pago, estado='DECLINED')
        response = self._post_webhook(client, payload)
        assert response.status_code == 200

        tx.refresh_from_db()
        assert tx.estado == 'rechazado'

        sample_empresa.refresh_from_db()
        assert sample_empresa.es_periodo_prueba == estado_prueba_antes

    @patch('core.views.pagos.settings')
    def test_webhook_es_idempotente(self, mock_settings, client, sample_empresa):
        """Webhook duplicado con APPROVED no reprocesa ni genera doble activación."""
        mock_settings.WOMPI_EVENTS_SECRET = ''
        mock_settings.WOMPI_SANDBOX = True

        tx = TransaccionPago.objects.create(
            empresa=sample_empresa,
            referencia_pago='SAM-IDEM-001',
            estado='aprobado',
            monto=Decimal('238000'),
            plan_seleccionado='MENSUAL',
        )
        payload = _make_webhook_payload(tx.referencia_pago, estado='APPROVED')
        response = self._post_webhook(client, payload)
        assert response.status_code == 200

        tx.refresh_from_db()
        assert tx.estado == 'aprobado'

    @patch('core.views.pagos.settings')
    def test_referencia_inexistente_retorna_404(self, mock_settings, client):
        """Webhook con referencia que no existe en BD retorna 404."""
        mock_settings.WOMPI_EVENTS_SECRET = ''
        mock_settings.WOMPI_SANDBOX = True

        payload = _make_webhook_payload('SAM-NO-EXISTE-999')
        response = self._post_webhook(client, payload)
        assert response.status_code == 404

    @patch('core.views.pagos.settings')
    def test_guarda_datos_respuesta_wompi(self, mock_settings, client, sample_empresa):
        """El webhook almacena la respuesta completa de Wompi en datos_respuesta."""
        mock_settings.WOMPI_EVENTS_SECRET = ''
        mock_settings.WOMPI_SANDBOX = True

        tx = TransaccionPago.objects.create(
            empresa=sample_empresa,
            referencia_pago='SAM-DATOS-001',
            estado='pendiente',
            monto=Decimal('238000'),
            plan_seleccionado='MENSUAL',
        )
        payload = _make_webhook_payload(tx.referencia_pago, estado='APPROVED')
        self._post_webhook(client, payload)

        tx.refresh_from_db()
        assert tx.datos_respuesta is not None
        assert tx.datos_respuesta.get('reference') == tx.referencia_pago

    @patch('core.views.pagos.settings')
    def test_pago_aprobado_activa_plan_anual(self, mock_settings, client, sample_empresa):
        """Webhook APPROVED para plan anual configura 12 meses de suscripción."""
        mock_settings.WOMPI_EVENTS_SECRET = ''
        mock_settings.WOMPI_SANDBOX = True

        tx = TransaccionPago.objects.create(
            empresa=sample_empresa,
            referencia_pago='SAM-ANUAL-001',
            estado='pendiente',
            monto=Decimal('2380000'),
            plan_seleccionado='ANUAL',
        )
        payload = _make_webhook_payload(tx.referencia_pago, estado='APPROVED')
        response = self._post_webhook(client, payload)
        assert response.status_code == 200

        sample_empresa.refresh_from_db()
        assert sample_empresa.duracion_suscripcion_meses == 12

    @patch('core.views.pagos.settings')
    def test_pago_aprobado_activa_plan_pro(self, mock_settings, client, sample_empresa):
        """Webhook APPROVED para plan Profesional configura 500 equipos."""
        mock_settings.WOMPI_EVENTS_SECRET = ''
        mock_settings.WOMPI_SANDBOX = True

        tx = TransaccionPago.objects.create(
            empresa=sample_empresa,
            referencia_pago='SAM-PRO-001',
            estado='pendiente',
            monto=PLANES['PRO_MENSUAL']['precio_total'],
            plan_seleccionado='PRO_MENSUAL',
        )
        payload = _make_webhook_payload(tx.referencia_pago, estado='APPROVED')
        response = self._post_webhook(client, payload)
        assert response.status_code == 200

        sample_empresa.refresh_from_db()
        assert sample_empresa.limite_equipos_empresa == 500

    @patch('core.views.pagos.settings')
    def test_pago_aprobado_activa_plan_basico(self, mock_settings, client, sample_empresa):
        """Webhook APPROVED para plan Básico configura 50 equipos."""
        mock_settings.WOMPI_EVENTS_SECRET = ''
        mock_settings.WOMPI_SANDBOX = True

        tx = TransaccionPago.objects.create(
            empresa=sample_empresa,
            referencia_pago='SAM-BASICO-001',
            estado='pendiente',
            monto=PLANES['BASICO_MENSUAL']['precio_total'],
            plan_seleccionado='BASICO_MENSUAL',
        )
        payload = _make_webhook_payload(tx.referencia_pago, estado='APPROVED')
        response = self._post_webhook(client, payload)
        assert response.status_code == 200

        sample_empresa.refresh_from_db()
        assert sample_empresa.limite_equipos_empresa == 50

    @patch('core.views.pagos.settings')
    def test_guarda_ip_cliente(self, mock_settings, client_empresa):
        """La transacción registra la IP del cliente al iniciarse."""
        mock_settings.WOMPI_PUBLIC_KEY = 'pub_test_abc123'
        mock_settings.WOMPI_INTEGRITY_SECRET = 'integrity_secret_test'
        mock_settings.WOMPI_SANDBOX = True

        c, _ = client_empresa
        c.post(_url('iniciar_pago'), {'plan': 'MENSUAL'})
        tx = TransaccionPago.objects.latest('fecha_creacion')
        assert tx.ip_cliente is not None


# ============================================================================
# Funciones utilitarias de firma
# ============================================================================

class TestFirmasWompi:

    def test_firma_integridad_correcta(self):
        """_calcular_firma_integridad genera el hash esperado por Wompi."""
        referencia = 'SAM-TEST-001'
        monto = 23800000
        moneda = 'COP'
        secret = 'mi_secreto'
        resultado = _calcular_firma_integridad(referencia, monto, moneda, secret)
        esperado = hashlib.sha256(
            f'{referencia}{monto}{moneda}{secret}'.encode('utf-8')
        ).hexdigest()
        assert resultado == esperado

    def test_firma_webhook_valida(self):
        """_validar_firma_webhook acepta payload con firma correcta."""
        secret = 'eventos_secret_test'
        payload = _make_webhook_payload('SAM-FW-001', estado='APPROVED')
        checksum = _firmar_payload(payload, secret)
        payload['signature']['checksum'] = checksum
        payload_bytes = json.dumps(payload).encode('utf-8')
        assert _validar_firma_webhook(
            payload_bytes,
            payload['signature']['properties'],
            checksum,
            secret,
        ) is True

    def test_firma_webhook_invalida(self):
        """_validar_firma_webhook rechaza payload con firma incorrecta."""
        secret = 'eventos_secret_test'
        payload = _make_webhook_payload('SAM-FW-002')
        payload['signature']['checksum'] = 'firma_falsa'
        payload_bytes = json.dumps(payload).encode('utf-8')
        assert _validar_firma_webhook(
            payload_bytes,
            payload['signature']['properties'],
            'firma_falsa',
            secret,
        ) is False


# ============================================================================
# TransaccionPago model
# ============================================================================

@pytest.mark.django_db
class TestTransaccionPagoModel:

    def test_monto_en_centavos(self, sample_empresa):
        """monto_en_centavos retorna el valor correcto para Wompi."""
        tx = TransaccionPago(
            empresa=sample_empresa,
            referencia_pago='SAM-CENTS-001',
            monto=Decimal('238000'),
            plan_seleccionado='MENSUAL',
        )
        assert tx.monto_en_centavos == 23800000

    def test_esta_aprobada(self, sample_empresa):
        """esta_aprobada() retorna True solo cuando estado es aprobado."""
        tx = TransaccionPago(
            empresa=sample_empresa,
            referencia_pago='SAM-EST-001',
            monto=Decimal('238000'),
            plan_seleccionado='MENSUAL',
            estado='aprobado',
        )
        assert tx.esta_aprobada() is True
        tx.estado = 'pendiente'
        assert tx.esta_aprobada() is False

    def test_str_representacion(self, sample_empresa):
        """__str__ muestra empresa, referencia y estado."""
        tx = TransaccionPago(
            empresa=sample_empresa,
            referencia_pago='SAM-STR-001',
            monto=Decimal('238000'),
            plan_seleccionado='MENSUAL',
            estado='pendiente',
        )
        assert 'SAM-STR-001' in str(tx)
        assert 'pendiente' in str(tx)


# ============================================================================
# Add-ons: inicio de pago y activación automática
# ============================================================================

@pytest.mark.django_db
class TestIniciarAddonPago:

    @patch('core.views.pagos.settings')
    def test_crea_transaccion_addon_pendiente(self, mock_settings, client_empresa):
        """POST a iniciar_addon_pago crea TransaccionPago con plan_seleccionado='ADDON'."""
        mock_settings.WOMPI_PUBLIC_KEY = 'pub_test_abc123'
        mock_settings.WOMPI_INTEGRITY_SECRET = 'integrity_test'
        mock_settings.WOMPI_SANDBOX = True
        c, _ = client_empresa
        c.post(_url_addon(), {
            'tecnicos': 2, 'admins': 1, 'gerentes': 0,
            'bloques_equipos': 0, 'bloques_storage': 0,
        })
        tx = TransaccionPago.objects.latest('fecha_creacion')
        assert tx.plan_seleccionado == 'ADDON'
        assert tx.estado == 'pendiente'
        assert tx.datos_addon['tecnicos'] == 2
        assert tx.datos_addon['admins'] == 1

    @patch('core.views.pagos.settings')
    def test_monto_addon_calculado_correctamente(self, mock_settings, client_empresa):
        """El monto incluye precios por rol con IVA."""
        mock_settings.WOMPI_PUBLIC_KEY = 'pub_test_abc123'
        mock_settings.WOMPI_INTEGRITY_SECRET = 'integrity_test'
        mock_settings.WOMPI_SANDBOX = True
        c, _ = client_empresa
        # 1 técnico ($20k) + 1 admin ($28k) = $48k + 19% IVA = $57.120
        c.post(_url_addon(), {
            'tecnicos': 1, 'admins': 1, 'gerentes': 0,
            'bloques_equipos': 0, 'bloques_storage': 0,
        })
        tx = TransaccionPago.objects.latest('fecha_creacion')
        esperado = (Decimal('48000') * Decimal('1.19')).quantize(Decimal('1'))
        assert tx.monto == esperado

    @patch('core.views.pagos.settings')
    def test_sin_addons_redirige_con_error(self, mock_settings, authenticated_client):
        """POST sin ningún add-on seleccionado redirige con error."""
        mock_settings.WOMPI_PUBLIC_KEY = 'pub_test_abc123'
        mock_settings.WOMPI_INTEGRITY_SECRET = 'integrity_test'
        mock_settings.WOMPI_SANDBOX = True
        response = authenticated_client.post(_url_addon(), {
            'tecnicos': 0, 'admins': 0, 'gerentes': 0,
            'bloques_equipos': 0, 'bloques_storage': 0,
        })
        assert response.status_code == 302
        assert response['Location'].endswith(_url('planes'))

    @patch('core.views.pagos.settings')
    def test_redirige_a_wompi(self, mock_settings, client_empresa):
        """Con credenciales, redirige al checkout de Wompi."""
        mock_settings.WOMPI_PUBLIC_KEY = 'pub_test_abc123'
        mock_settings.WOMPI_INTEGRITY_SECRET = 'integrity_test'
        mock_settings.WOMPI_SANDBOX = True
        c, _ = client_empresa
        response = c.post(_url_addon(), {'tecnicos': 1})
        assert response.status_code == 302
        assert 'checkout.wompi.co' in response['Location']


@pytest.mark.django_db
class TestActivacionAddons:

    def _post_webhook(self, client, payload):
        return client.post(
            _url('wompi_webhook'),
            data=json.dumps(payload),
            content_type='application/json',
        )

    @patch('core.views.pagos.settings')
    def test_webhook_addon_activa_usuarios(self, mock_settings, client, sample_empresa):
        """Webhook APPROVED para addon incrementa limite_usuarios_empresa."""
        mock_settings.WOMPI_EVENTS_SECRET = ''
        sample_empresa.limite_usuarios_empresa = 3
        sample_empresa.save()

        tx = TransaccionPago.objects.create(
            empresa=sample_empresa,
            referencia_pago='SAM-ADDON-USR-001',
            estado='pendiente',
            monto=Decimal('95200'),
            plan_seleccionado='ADDON',
            datos_addon={'tecnicos': 2, 'admins': 1, 'gerentes': 0,
                         'bloques_equipos': 0, 'bloques_storage': 0},
        )
        payload = _make_webhook_payload(tx.referencia_pago, estado='APPROVED')
        self._post_webhook(client, payload)

        sample_empresa.refresh_from_db()
        assert sample_empresa.limite_usuarios_empresa == 6   # 3 base + 3 nuevos

    @patch('core.views.pagos.settings')
    def test_webhook_addon_activa_equipos(self, mock_settings, client, sample_empresa):
        """Webhook APPROVED para addon incrementa limite_equipos_empresa."""
        mock_settings.WOMPI_EVENTS_SECRET = ''
        equipos_antes = sample_empresa.limite_equipos_empresa

        tx = TransaccionPago.objects.create(
            empresa=sample_empresa,
            referencia_pago='SAM-ADDON-EQ-001',
            estado='pendiente',
            monto=Decimal('107100'),
            plan_seleccionado='ADDON',
            datos_addon={'tecnicos': 0, 'admins': 0, 'gerentes': 0,
                         'bloques_equipos': 2, 'bloques_storage': 0},
        )
        payload = _make_webhook_payload(tx.referencia_pago, estado='APPROVED')
        self._post_webhook(client, payload)

        sample_empresa.refresh_from_db()
        assert sample_empresa.limite_equipos_empresa == equipos_antes + 100  # 2 bloques × 50

    @patch('core.views.pagos.settings')
    def test_webhook_addon_activa_storage(self, mock_settings, client, sample_empresa):
        """Webhook APPROVED para addon incrementa limite_almacenamiento_mb."""
        mock_settings.WOMPI_EVENTS_SECRET = ''
        storage_antes = sample_empresa.limite_almacenamiento_mb

        tx = TransaccionPago.objects.create(
            empresa=sample_empresa,
            referencia_pago='SAM-ADDON-STOR-001',
            estado='pendiente',
            monto=Decimal('23800'),
            plan_seleccionado='ADDON',
            datos_addon={'tecnicos': 0, 'admins': 0, 'gerentes': 0,
                         'bloques_equipos': 0, 'bloques_storage': 1},
        )
        payload = _make_webhook_payload(tx.referencia_pago, estado='APPROVED')
        self._post_webhook(client, payload)

        sample_empresa.refresh_from_db()
        assert sample_empresa.limite_almacenamiento_mb == storage_antes + 5 * 1024

    @patch('core.views.pagos.settings')
    def test_addon_idempotente(self, mock_settings, client, sample_empresa):
        """Webhook duplicado no vuelve a activar add-ons."""
        mock_settings.WOMPI_EVENTS_SECRET = ''
        sample_empresa.limite_usuarios_empresa = 3
        sample_empresa.save()

        tx = TransaccionPago.objects.create(
            empresa=sample_empresa,
            referencia_pago='SAM-ADDON-IDEM-001',
            estado='aprobado',   # ya procesado
            monto=Decimal('23800'),
            plan_seleccionado='ADDON',
            datos_addon={'tecnicos': 1, 'admins': 0, 'gerentes': 0,
                         'bloques_equipos': 0, 'bloques_storage': 0},
        )
        payload = _make_webhook_payload(tx.referencia_pago, estado='APPROVED')
        self._post_webhook(client, payload)

        sample_empresa.refresh_from_db()
        assert sample_empresa.limite_usuarios_empresa == 3  # no cambió


@pytest.mark.django_db
class TestActivarAddonsModel:

    def test_activar_addons_incrementa_todos_los_limites(self, sample_empresa):
        """activar_addons incrementa usuarios, equipos y storage correctamente."""
        sample_empresa.limite_usuarios_empresa = 3
        sample_empresa.limite_equipos_empresa = 200
        sample_empresa.limite_almacenamiento_mb = 4096
        sample_empresa.save()

        sample_empresa.activar_addons({
            'tecnicos': 2,
            'admins': 1,
            'gerentes': 1,
            'bloques_equipos': 3,
            'bloques_storage': 2,
        })
        sample_empresa.refresh_from_db()
        assert sample_empresa.limite_usuarios_empresa == 7      # 3 + 2 + 1 + 1
        assert sample_empresa.limite_equipos_empresa == 350     # 200 + 3×50
        assert sample_empresa.limite_almacenamiento_mb == 4096 + 2 * 5 * 1024


# ============================================================================
# Creación de usuarios por el administrador de la empresa (autoservicio)
# ============================================================================

@pytest.mark.django_db
class TestCrearUsuarioEmpresa:
    """
    Tests para la vista crear_usuario_empresa.
    Solo ADMINISTRADOR (o superusuario) puede acceder; valida el límite.
    """

    URL = '/core/usuarios/crear/'

    def _admin_client(self, empresa):
        """Retorna un Client autenticado con un usuario ADMINISTRADOR de la empresa."""
        from core.models import CustomUser
        user = CustomUser.objects.create_user(
            username='admin_empresa_test',
            password='testpass123',
            empresa=empresa,
            rol_usuario='ADMINISTRADOR',
            is_active=True,
        )
        c = Client()
        c.login(username='admin_empresa_test', password='testpass123')
        return c, user

    def test_tecnico_no_puede_acceder(self, sample_empresa):
        """Un usuario con rol TECNICO es redirigido al dashboard."""
        from core.models import CustomUser
        user = CustomUser.objects.create_user(
            username='tec_test_acceso',
            password='testpass123',
            empresa=sample_empresa,
            rol_usuario='TECNICO',
            is_active=True,
        )
        c = Client()
        c.login(username='tec_test_acceso', password='testpass123')
        response = c.get(self.URL)
        assert response.status_code == 302
        assert 'dashboard' in response['Location']

    def test_admin_puede_ver_formulario(self, sample_empresa):
        """ADMINISTRADOR obtiene 200 en GET."""
        c, _ = self._admin_client(sample_empresa)
        response = c.get(self.URL)
        assert response.status_code == 200
        assert any('crear_usuario_empresa' in t.name for t in response.templates)

    def test_crear_usuario_tecnico(self, sample_empresa):
        """POST crea un usuario TECNICO nuevo en la empresa."""
        from core.models import CustomUser
        sample_empresa.limite_usuarios_empresa = 10
        sample_empresa.save()

        c, _ = self._admin_client(sample_empresa)
        response = c.post(self.URL, {
            'first_name': 'Pedro',
            'last_name': 'Lopez',
            'email': 'pedro@test.com',
            'rol_usuario': 'TECNICO',
        })
        # Muestra la contraseña generada en la misma página (200)
        assert response.status_code == 200
        assert CustomUser.objects.filter(empresa=sample_empresa, rol_usuario='TECNICO').exists()

    def test_limite_alcanzado_redirige_a_planes(self, sample_empresa):
        """Si se alcanzó el límite de usuarios, POST redirige a planes."""
        from core.models import CustomUser
        # Llenar el límite
        sample_empresa.limite_usuarios_empresa = 1
        sample_empresa.save()
        # El único slot lo ocupa el admin que creamos en _admin_client
        c, _ = self._admin_client(sample_empresa)
        # El admin ya ocupa el único slot, así que el límite está lleno
        response = c.post(self.URL, {
            'first_name': 'Extra',
            'last_name': 'User',
            'email': 'extra@test.com',
            'rol_usuario': 'TECNICO',
        })
        assert response.status_code == 302
        assert 'planes' in response['Location']

    def test_campo_obligatorio_nombre(self, sample_empresa):
        """POST sin nombre muestra error (no crea usuario)."""
        from core.models import CustomUser
        sample_empresa.limite_usuarios_empresa = 10
        sample_empresa.save()

        c, _ = self._admin_client(sample_empresa)
        # Contar DESPUÉS de crear el admin (el admin ya fue creado)
        count_antes = CustomUser.objects.filter(empresa=sample_empresa).count()

        c.post(self.URL, {
            'first_name': '',          # campo vacío
            'last_name': 'Lopez',
            'email': 'sin_nombre@test.com',
            'rol_usuario': 'TECNICO',
        })
        count_despues = CustomUser.objects.filter(empresa=sample_empresa).count()
        assert count_despues == count_antes  # no se creó ninguno nuevo

    def test_rol_gerencia_asigna_flags(self, sample_empresa):
        """Un usuario GERENCIA creado tiene is_management_user=True."""
        from core.models import CustomUser
        sample_empresa.limite_usuarios_empresa = 10
        sample_empresa.save()

        c, _ = self._admin_client(sample_empresa)
        c.post(self.URL, {
            'first_name': 'Ana',
            'last_name': 'Gerente',
            'email': 'ana_ger@test.com',
            'rol_usuario': 'GERENCIA',
        })
        gerente = CustomUser.objects.filter(
            empresa=sample_empresa, rol_usuario='GERENCIA'
        ).first()
        assert gerente is not None
        assert gerente.is_management_user is True
        assert gerente.can_access_dashboard_decisiones is True

    def test_no_autenticado_redirige_login(self):
        """Usuario no autenticado es enviado al login."""
        c = Client()
        response = c.get(self.URL)
        assert response.status_code == 302
        assert 'login' in response['Location']
