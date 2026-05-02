"""
Tests para historial de cambios en formatos de documentos.
Cubre: EmpresaFormatoLog, actualizar_formato_empresa() (historial + email),
       _enviar_email_cambio_formato().
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from django.test import Client
from django.urls import reverse

from core.models import Empresa, CustomUser, EmpresaFormatoLog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_hf_counter = 0


def _hf_empresa(suffix='hf'):
    global _hf_counter
    _hf_counter += 1
    return Empresa.objects.create(
        nombre=f'Empresa HF {suffix} {_hf_counter}',
        nit=f'7{_hf_counter:08d}-{_hf_counter % 10}',
        email=f'hf{_hf_counter}@test.com',
    )


def _hf_user(empresa, rol='ADMINISTRADOR', username=None):
    global _hf_counter
    _hf_counter += 1
    uname = username or f'hf_u_{_hf_counter}'
    return CustomUser.objects.create_user(
        username=uname,
        password='pass123',
        email=f'{uname}@samtest.com',
        empresa=empresa,
        rol_usuario=rol,
    )


# ---------------------------------------------------------------------------
# 1. Modelo EmpresaFormatoLog
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestEmpresaFormatoLog:

    def test_crear_registro(self):
        """EmpresaFormatoLog almacena empresa, campo, valores y usuario."""
        empresa = _hf_empresa('log')
        user = _hf_user(empresa)
        log = EmpresaFormatoLog.objects.create(
            empresa=empresa,
            campo='Código Confirmación',
            valor_anterior='CONF-001',
            valor_nuevo='CONF-002',
            usuario=user,
        )
        log.refresh_from_db()
        assert log.campo == 'Código Confirmación'
        assert log.valor_anterior == 'CONF-001'
        assert log.valor_nuevo == 'CONF-002'
        assert log.usuario == user
        assert log.fecha is not None

    def test_str_representacion(self):
        """__str__ muestra valores anterior y nuevo."""
        empresa = _hf_empresa('str')
        log = EmpresaFormatoLog.objects.create(
            empresa=empresa,
            campo='Versión Intervalos',
            valor_anterior='01',
            valor_nuevo='02',
        )
        texto = str(log)
        assert '01' in texto
        assert '02' in texto

    def test_usuario_puede_ser_nulo(self):
        """EmpresaFormatoLog acepta usuario=None (SET_NULL)."""
        empresa = _hf_empresa('null_user')
        log = EmpresaFormatoLog.objects.create(
            empresa=empresa,
            campo='Código Comprobación',
            valor_anterior='',
            valor_nuevo='COMP-001',
            usuario=None,
        )
        assert log.usuario is None

    def test_valor_anterior_puede_ser_vacio(self):
        """valor_anterior puede ser cadena vacía (primer registro)."""
        empresa = _hf_empresa('empty_ant')
        log = EmpresaFormatoLog.objects.create(
            empresa=empresa,
            campo='Código Mantenimiento',
            valor_anterior='',
            valor_nuevo='MNT-001',
        )
        assert log.valor_anterior == ''


# ---------------------------------------------------------------------------
# 2. actualizar_formato_empresa() — integración historial
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestActualizarFormatoHistorial:

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.empresa = _hf_empresa('ajax')
        self.user = _hf_user(self.empresa)
        self.client = Client()
        self.client.force_login(self.user)
        self.url = reverse('core:actualizar_formato_empresa')

    def _post(self, payload):
        return self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_crea_log_al_cambiar_codigo(self):
        """Cambiar código crea EmpresaFormatoLog con etiqueta y valores correctos."""
        self.empresa.confirmacion_codigo = 'CONF-OLD'
        self.empresa.save()

        self._post({'tipo': 'confirmacion', 'codigo': 'CONF-NEW'})

        log = EmpresaFormatoLog.objects.filter(
            empresa=self.empresa, campo='Código Confirmación'
        ).first()
        assert log is not None
        assert log.valor_anterior == 'CONF-OLD'
        assert log.valor_nuevo == 'CONF-NEW'
        assert log.usuario == self.user

    def test_crea_log_al_cambiar_version(self):
        """Cambiar versión crea EmpresaFormatoLog con etiqueta correcta."""
        self.empresa.intervalos_version = '01'
        self.empresa.save()

        self._post({'tipo': 'intervalos', 'version': '02'})

        log = EmpresaFormatoLog.objects.filter(
            empresa=self.empresa, campo='Versión Intervalos'
        ).first()
        assert log is not None
        assert log.valor_anterior == '01'
        assert log.valor_nuevo == '02'

    def test_crea_log_al_cambiar_fecha(self):
        """Cambiar fecha crea EmpresaFormatoLog con fecha formateada."""
        self._post({'tipo': 'mantenimiento', 'fecha': '2026-01-15'})

        log = EmpresaFormatoLog.objects.filter(
            empresa=self.empresa, campo='Fecha Mantenimiento'
        ).first()
        assert log is not None
        assert log.valor_nuevo == '15/01/2026'

    def test_no_crea_log_si_valor_igual(self):
        """Si el valor enviado es igual al actual no se crea log."""
        self.empresa.comprobacion_codigo = 'COMP-001'
        self.empresa.save()

        count_before = EmpresaFormatoLog.objects.filter(empresa=self.empresa).count()
        self._post({'tipo': 'comprobacion', 'codigo': 'COMP-001'})
        count_after = EmpresaFormatoLog.objects.filter(empresa=self.empresa).count()

        assert count_after == count_before

    def test_tecnico_no_puede_cambiar(self):
        """TECNICO recibe 403 y no se crea log."""
        tecnico = _hf_user(self.empresa, rol='TECNICO')
        c = Client()
        c.force_login(tecnico)
        count_before = EmpresaFormatoLog.objects.count()

        response = c.post(
            self.url,
            data=json.dumps({'tipo': 'confirmacion', 'codigo': 'X'}),
            content_type='application/json',
        )
        assert response.status_code == 403
        assert EmpresaFormatoLog.objects.count() == count_before

    def test_etiqueta_correcta_para_cada_tipo(self):
        """Cada tipo usa la etiqueta correcta en el campo del log."""
        etiquetas_esperadas = {
            'intervalos':    'Código Intervalos',
            'mantenimiento': 'Código Mantenimiento',
            'confirmacion':  'Código Confirmación',
            'comprobacion':  'Código Comprobación',
        }
        for tipo, etiqueta in etiquetas_esperadas.items():
            self._post({'tipo': tipo, 'codigo': f'NEW-{tipo[:3].upper()}'})
            log = EmpresaFormatoLog.objects.filter(
                empresa=self.empresa, campo=etiqueta
            ).first()
            assert log is not None, f'No se creó log para tipo={tipo}'

    @patch('core.views.companies._enviar_email_cambio_formato')
    def test_email_se_envia_cuando_hay_cambios(self, mock_email):
        """Cuando hay cambios reales se llama _enviar_email_cambio_formato."""
        self._post({'tipo': 'confirmacion', 'codigo': 'NUEVO-EMAIL-TEST'})
        assert mock_email.called
        args = mock_email.call_args[0]
        assert args[0] == self.empresa
        assert args[1] == self.user

    @patch('core.views.companies._enviar_email_cambio_formato')
    def test_email_no_se_envia_sin_cambios(self, mock_email):
        """Sin cambios reales no se llama al email."""
        self.empresa.confirmacion_codigo = 'MISMO-CODIGO'
        self.empresa.save()

        self._post({'tipo': 'confirmacion', 'codigo': 'MISMO-CODIGO'})
        assert not mock_email.called

    def test_multiple_campos_generan_multiples_logs(self):
        """Cambiar código y versión en un POST crea dos registros de log."""
        self.empresa.intervalos_codigo = 'OLD-COD'
        self.empresa.intervalos_version = 'OLD-VER'
        self.empresa.save()

        self._post({'tipo': 'intervalos', 'codigo': 'NEW-COD', 'version': 'NEW-VER'})

        logs = EmpresaFormatoLog.objects.filter(empresa=self.empresa)
        campos = set(logs.values_list('campo', flat=True))
        assert 'Código Intervalos' in campos
        assert 'Versión Intervalos' in campos


# ---------------------------------------------------------------------------
# 3. _enviar_email_cambio_formato() — destinatarios y contenido
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestEnviarEmailCambioFormato:

    def _run_email(self, empresa, editor, cambios):
        from core.views.companies import _enviar_email_cambio_formato
        _enviar_email_cambio_formato(empresa, editor, cambios)

    def test_no_enviar_sin_destinatarios(self):
        """Sin usuarios Admin/Gerencia activos no se envía email."""
        empresa = _hf_empresa('nodest')
        editor = _hf_user(empresa, rol='TECNICO')

        with patch('django.core.mail.EmailMultiAlternatives.send') as mock_send:
            self._run_email(empresa, editor, [('Campo', 'A', 'B')])
        assert not mock_send.called

    def test_envia_a_admin_activo(self):
        """Con Admin activo como destinatario se envía el email."""
        empresa = _hf_empresa('destok')
        editor = _hf_user(empresa, rol='ADMINISTRADOR')

        with patch('django.core.mail.EmailMultiAlternatives.send') as mock_send:
            self._run_email(empresa, editor, [('Código Confirmación', 'V1', 'V2')])
        assert mock_send.called

    def test_no_envia_a_usuario_inactivo(self):
        """Usuario Admin inactivo no recibe email."""
        empresa = _hf_empresa('inact')
        editor = _hf_user(empresa, rol='ADMINISTRADOR')
        editor.is_active = False
        editor.save()

        with patch('django.core.mail.EmailMultiAlternatives.send') as mock_send:
            self._run_email(empresa, editor, [('Campo', 'A', 'B')])
        assert not mock_send.called

    def test_subject_contiene_nombre_empresa(self):
        """El subject del email contiene el nombre de la empresa."""
        empresa = _hf_empresa('subj')
        editor = _hf_user(empresa, rol='ADMINISTRADOR')

        subjects_capturados = []

        original_init = __import__(
            'django.core.mail', fromlist=['EmailMultiAlternatives']
        ).EmailMultiAlternatives.__init__

        def fake_init(self_msg, subject='', body='', from_email=None, to=None, **kw):
            subjects_capturados.append(subject)
            self_msg.subject = subject
            self_msg.body = body
            self_msg.from_email = from_email
            self_msg.to = to or []
            self_msg.alternatives = []

        with patch('django.core.mail.EmailMultiAlternatives.__init__', fake_init), \
             patch('django.core.mail.EmailMultiAlternatives.attach_alternative'), \
             patch('django.core.mail.EmailMultiAlternatives.send'):
            self._run_email(empresa, editor, [('Campo', 'Antes', 'Después')])

        assert subjects_capturados, 'No se creó ningún EmailMultiAlternatives'
        assert empresa.nombre in subjects_capturados[0]
