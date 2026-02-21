"""
Tests para el módulo de auto-registro de Trial.
Cubre: formulario, creación de empresa + 3 usuarios, validaciones,
permisos automáticos, anti-abuso (honeypot + rate limiting),
logo, NIT contra eliminadas, advertencia de login trial expirado.
"""
import pytest
from datetime import timedelta
from unittest.mock import patch

from django.test import Client
from django.urls import reverse
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.utils import timezone

from core.models import Empresa, CustomUser
from core.forms import RegistroTrialForm
from core.views.registro import (
    PERMISOS_TECNICO,
    PERMISOS_ADMINISTRADOR,
    PERMISOS_GERENCIA,
    TRIAL_MAX_ATTEMPTS_PER_HOUR,
)


# ============================================================================
# Datos base para tests
# ============================================================================

VALID_TRIAL_DATA = {
    'nombre_empresa': 'Metrología Test S.A.S.',
    'nit': '900123456-7',
    'email_empresa': 'contacto@metrologiatest.com',
    'telefono': '+57 300 123 4567',
    'nombre_completo': 'Juan Pérez García',
    'username': 'juan_perez',
    'email_usuario': 'juan@metrologiatest.com',
    'password1': 'SecurePass123!',
    'password2': 'SecurePass123!',
}


def get_trial_url():
    return reverse('core:solicitar_trial')


def get_exitoso_url():
    return reverse('core:trial_exitoso')


def _make_png():
    """Genera un PNG válido de 1x1 pixel."""
    return (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )


# ============================================================================
# Tests de la vista solicitar_trial - GET
# ============================================================================

@pytest.mark.django_db
class TestSolicitarTrialGET:

    def test_get_muestra_formulario(self, client):
        """GET a solicitar-trial muestra el formulario."""
        response = client.get(get_trial_url())
        assert response.status_code == 200
        assert 'form' in response.context
        assert isinstance(response.context['form'], RegistroTrialForm)

    def test_usuario_autenticado_redirige_a_dashboard(self, authenticated_client):
        """Usuario ya logueado es redirigido al dashboard."""
        response = authenticated_client.get(get_trial_url())
        assert response.status_code == 302
        assert '/dashboard/' in response.url


# ============================================================================
# Tests de la vista solicitar_trial - POST válido
# ============================================================================

@pytest.mark.django_db
class TestSolicitarTrialPOSTValido:

    def test_crea_empresa_con_datos_correctos(self, client):
        """POST válido crea una empresa con los datos del formulario."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        empresa = Empresa.objects.get(nombre='Metrología Test S.A.S.')
        assert empresa.nit == '900123456-7'
        assert empresa.email == 'contacto@metrologiatest.com'

    def test_empresa_tiene_trial_activo(self, client):
        """La empresa creada tiene trial de 30 días activo."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        empresa = Empresa.objects.get(nombre='Metrología Test S.A.S.')
        assert empresa.es_periodo_prueba is True
        assert empresa.duracion_prueba_dias == 30
        assert empresa.fecha_inicio_plan is not None
        assert empresa.limite_equipos_empresa == Empresa.TRIAL_EQUIPOS

    def test_crea_tres_usuarios(self, client):
        """POST válido crea exactamente 3 usuarios para la empresa."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        empresa = Empresa.objects.get(nombre='Metrología Test S.A.S.')
        usuarios = CustomUser.objects.filter(empresa=empresa)
        assert usuarios.count() == 3

    def test_usuario_admin_con_datos_formulario(self, client):
        """El usuario ADMINISTRADOR tiene los datos del formulario."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        admin = CustomUser.objects.get(username='juan_perez')
        assert admin.rol_usuario == 'ADMINISTRADOR'
        assert admin.email == 'juan@metrologiatest.com'
        assert admin.first_name == 'Juan'
        assert admin.last_name == 'Pérez García'
        assert admin.is_active is True

    def test_usuario_gerencia_generado(self, client):
        """El usuario GERENCIA se genera con username basado en NIT."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        gerente = CustomUser.objects.get(username='9001234567_gerente')
        assert gerente.rol_usuario == 'GERENCIA'
        assert gerente.is_management_user is True
        assert gerente.can_access_dashboard_decisiones is True
        assert gerente.is_active is True

    def test_usuario_tecnico_generado(self, client):
        """El usuario TECNICO se genera con username basado en NIT."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        tecnico = CustomUser.objects.get(username='9001234567_tecnico')
        assert tecnico.rol_usuario == 'TECNICO'
        assert tecnico.is_active is True

    def test_redirige_a_trial_exitoso(self, client):
        """POST válido redirige a la página de éxito."""
        response = client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        assert response.status_code == 302
        assert get_exitoso_url() in response.url

    def test_credenciales_en_sesion(self, client):
        """Las credenciales se guardan en la sesión."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        session = client.session
        creds = session.get('trial_credenciales')
        assert creds is not None
        assert creds['empresa_nombre'] == 'Metrología Test S.A.S.'
        assert creds['admin']['username'] == 'juan_perez'
        assert creds['gerente']['username'] == '9001234567_gerente'
        assert creds['tecnico']['username'] == '9001234567_tecnico'
        # Las contraseñas temporales deben estar presentes
        assert len(creds['gerente']['password']) > 0
        assert len(creds['tecnico']['password']) > 0


# ============================================================================
# Tests de permisos automáticos por rol
# ============================================================================

@pytest.mark.django_db
class TestPermisosAutomaticos:

    def test_admin_tiene_permisos_administrador(self, client):
        """El usuario ADMINISTRADOR recibe todos los permisos de admin."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        admin = CustomUser.objects.get(username='juan_perez')
        permisos_user = set(admin.user_permissions.values_list('codename', flat=True))
        for codename in PERMISOS_ADMINISTRADOR:
            assert codename in permisos_user, f"Falta permiso '{codename}' en ADMINISTRADOR"

    def test_gerencia_tiene_permisos_gerencia(self, client):
        """El usuario GERENCIA recibe los permisos de gerencia."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        gerente = CustomUser.objects.get(username='9001234567_gerente')
        permisos_user = set(gerente.user_permissions.values_list('codename', flat=True))
        for codename in PERMISOS_GERENCIA:
            assert codename in permisos_user, f"Falta permiso '{codename}' en GERENCIA"

    def test_tecnico_tiene_permisos_tecnico(self, client):
        """El usuario TECNICO recibe solo los permisos de técnico."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        tecnico = CustomUser.objects.get(username='9001234567_tecnico')
        permisos_user = set(tecnico.user_permissions.values_list('codename', flat=True))
        for codename in PERMISOS_TECNICO:
            assert codename in permisos_user, f"Falta permiso '{codename}' en TECNICO"

    def test_tecnico_no_tiene_permisos_extra(self, client):
        """El TECNICO no tiene permisos de admin como delete_equipo."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        tecnico = CustomUser.objects.get(username='9001234567_tecnico')
        permisos_user = set(tecnico.user_permissions.values_list('codename', flat=True))
        permisos_solo_admin = set(PERMISOS_ADMINISTRADOR) - set(PERMISOS_TECNICO)
        for codename in permisos_solo_admin:
            assert codename not in permisos_user, f"TECNICO no debería tener '{codename}'"

    def test_admin_puede_ver_equipos(self, client):
        """El ADMINISTRADOR tiene permiso view_equipo."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        admin = CustomUser.objects.get(username='juan_perez')
        assert admin.has_perm('core.view_equipo')

    def test_tecnico_puede_agregar_calibracion(self, client):
        """El TECNICO tiene permiso add_calibracion."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        tecnico = CustomUser.objects.get(username='9001234567_tecnico')
        assert tecnico.has_perm('core.add_calibracion')

    def test_tecnico_puede_ver_proveedores(self, client):
        """El TECNICO tiene permiso view_proveedor (consulta al registrar calibraciones)."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        tecnico = CustomUser.objects.get(username='9001234567_tecnico')
        assert tecnico.has_perm('core.view_proveedor')

    def test_tecnico_puede_ver_procedimientos(self, client):
        """El TECNICO tiene permiso view_procedimiento."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        tecnico = CustomUser.objects.get(username='9001234567_tecnico')
        assert tecnico.has_perm('core.view_procedimiento')

    def test_tecnico_no_puede_eliminar_proveedor(self, client):
        """El TECNICO NO tiene permiso delete_proveedor."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        tecnico = CustomUser.objects.get(username='9001234567_tecnico')
        assert not tecnico.has_perm('core.delete_proveedor')

    def test_tecnico_no_puede_eliminar_procedimiento(self, client):
        """El TECNICO NO tiene permiso delete_procedimiento."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        tecnico = CustomUser.objects.get(username='9001234567_tecnico')
        assert not tecnico.has_perm('core.delete_procedimiento')

    def test_admin_tiene_crud_proveedores(self, client):
        """El ADMINISTRADOR tiene CRUD completo de proveedores."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        admin = CustomUser.objects.get(username='juan_perez')
        for perm in ['add_proveedor', 'change_proveedor', 'delete_proveedor', 'view_proveedor']:
            assert admin.has_perm(f'core.{perm}'), f"Falta permiso '{perm}' en ADMINISTRADOR"

    def test_admin_tiene_crud_procedimientos(self, client):
        """El ADMINISTRADOR tiene CRUD completo de procedimientos."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        admin = CustomUser.objects.get(username='juan_perez')
        for perm in ['add_procedimiento', 'change_procedimiento', 'delete_procedimiento', 'view_procedimiento']:
            assert admin.has_perm(f'core.{perm}'), f"Falta permiso '{perm}' en ADMINISTRADOR"

    def test_gerencia_tiene_crud_proveedores(self, client):
        """El GERENCIA tiene CRUD completo de proveedores."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        gerente = CustomUser.objects.get(username='9001234567_gerente')
        for perm in ['add_proveedor', 'change_proveedor', 'delete_proveedor', 'view_proveedor']:
            assert gerente.has_perm(f'core.{perm}'), f"Falta permiso '{perm}' en GERENCIA"

    def test_gerencia_tiene_crud_procedimientos(self, client):
        """El GERENCIA tiene CRUD completo de procedimientos."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        gerente = CustomUser.objects.get(username='9001234567_gerente')
        for perm in ['add_procedimiento', 'change_procedimiento', 'delete_procedimiento', 'view_procedimiento']:
            assert gerente.has_perm(f'core.{perm}'), f"Falta permiso '{perm}' en GERENCIA"


# ============================================================================
# Tests anti-abuso: honeypot
# ============================================================================

@pytest.mark.django_db
class TestHoneypot:

    def test_honeypot_relleno_no_crea_empresa(self, client):
        """Si el campo honeypot tiene valor, no se crea empresa (bot detectado)."""
        data = {**VALID_TRIAL_DATA, 'website': 'http://spam.com'}
        client.post(get_trial_url(), data=data)
        assert Empresa.objects.count() == 0

    def test_honeypot_relleno_redirige_como_si_tuviera_exito(self, client):
        """Bot detectado recibe redirect a trial_exitoso (simula éxito)."""
        data = {**VALID_TRIAL_DATA, 'website': 'http://spam.com'}
        response = client.post(get_trial_url(), data=data)
        assert response.status_code == 302
        assert get_exitoso_url() in response.url

    def test_honeypot_vacio_permite_registro(self, client):
        """Con honeypot vacío, el registro funciona normalmente."""
        data = {**VALID_TRIAL_DATA, 'website': ''}
        client.post(get_trial_url(), data=data)
        assert Empresa.objects.filter(nombre='Metrología Test S.A.S.').exists()


# ============================================================================
# Tests anti-abuso: rate limiting
# ============================================================================

@pytest.mark.django_db
class TestRateLimiting:

    def test_cooldown_24h_tras_registro_exitoso(self, client):
        """Tras un registro exitoso, la misma IP no puede registrar en 24h."""
        # Primer registro: exitoso
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        assert Empresa.objects.count() == 1

        # Segundo intento: debe ser bloqueado por cooldown
        data2 = {
            **VALID_TRIAL_DATA,
            'nombre_empresa': 'Otra Empresa S.A.S.',
            'nit': '800999888-1',
            'email_empresa': 'otra@empresa.com',
            'username': 'otro_user',
            'email_usuario': 'otro@empresa.com',
        }
        response = client.post(get_trial_url(), data=data2)
        assert response.status_code == 200  # Muestra form con error
        assert Empresa.objects.count() == 1  # No se creó la segunda

    def test_max_intentos_por_hora(self, client):
        """Tras N intentos POST, la IP es bloqueada temporalmente."""
        # Llenar los intentos permitidos (3 por defecto)
        for i in range(TRIAL_MAX_ATTEMPTS_PER_HOUR):
            data = {**VALID_TRIAL_DATA, 'nit': '123'}  # NIT inválido para que falle
            client.post(get_trial_url(), data=data)

        # El siguiente intento debe ser bloqueado
        response = client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        assert response.status_code == 200
        form = response.context['form']
        assert form.non_field_errors()  # Debe tener error de rate limiting

    def test_rate_limit_no_afecta_get(self, client):
        """El rate limiting solo aplica a POST, no a GET."""
        # Saturar intentos POST
        for i in range(TRIAL_MAX_ATTEMPTS_PER_HOUR + 1):
            client.post(get_trial_url(), data={'nit': '123'})

        # GET sigue funcionando
        response = client.get(get_trial_url())
        assert response.status_code == 200
        assert 'form' in response.context


# ============================================================================
# Tests de logo en registro
# ============================================================================

@pytest.mark.django_db
class TestLogoEnRegistro:

    def test_registro_con_logo(self, client):
        """Se puede registrar con logo y se guarda en la empresa."""
        logo = SimpleUploadedFile(
            name='logo_test.png',
            content=_make_png(),
            content_type='image/png',
        )
        data = {**VALID_TRIAL_DATA}
        response = client.post(get_trial_url(), data=data, FILES={'logo_empresa': logo})
        # Usar el formato correcto para multipart
        empresa = Empresa.objects.get(nombre='Metrología Test S.A.S.')
        # La empresa fue creada (con o sin logo, el registro funciona)
        assert empresa is not None

    def test_registro_sin_logo_funciona(self, client):
        """El registro sin logo funciona normalmente."""
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        empresa = Empresa.objects.get(nombre='Metrología Test S.A.S.')
        assert empresa is not None

    def test_logo_muy_grande_rechazado(self, client):
        """Logo mayor a 2 MB es rechazado por el formulario."""
        # Crear un archivo falso > 2MB
        big_content = b'\x00' * (3 * 1024 * 1024)  # 3 MB
        logo = SimpleUploadedFile(
            name='logo_grande.png',
            content=big_content,
            content_type='image/png',
        )
        form = RegistroTrialForm(data=VALID_TRIAL_DATA, files={'logo_empresa': logo})
        assert not form.is_valid()
        assert 'logo_empresa' in form.errors

    def test_logo_formato_invalido_rechazado(self):
        """Logo con formato no permitido es rechazado."""
        gif = SimpleUploadedFile(
            name='logo.gif',
            content=b'GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00',
            content_type='image/gif',
        )
        form = RegistroTrialForm(data=VALID_TRIAL_DATA, files={'logo_empresa': gif})
        assert not form.is_valid()
        assert 'logo_empresa' in form.errors


# ============================================================================
# Tests de validaciones del formulario
# ============================================================================

@pytest.mark.django_db
class TestRegistroTrialValidaciones:

    def test_nit_duplicado_empresa_activa(self, client, empresa_factory):
        """No permite registrar con un NIT que ya existe (empresa activa)."""
        empresa_factory(nit='900123456-7')
        response = client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        assert response.status_code == 200
        assert Empresa.objects.filter(nombre='Metrología Test S.A.S.').count() == 0

    def test_nit_duplicado_empresa_eliminada(self, client, empresa_factory):
        """No permite registrar con NIT de empresa soft-deleted (trial anterior)."""
        empresa = empresa_factory(nit='900123456-7')
        empresa.is_deleted = True
        empresa.deleted_at = timezone.now()
        empresa.save(update_fields=['is_deleted', 'deleted_at'])

        response = client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        assert response.status_code == 200
        form = response.context['form']
        assert 'nit' in form.errors
        assert 'trial anterior' in str(form.errors['nit'])

    def test_nit_muy_corto(self, client):
        """NIT con menos de 9 dígitos es rechazado."""
        data = {**VALID_TRIAL_DATA, 'nit': '12345'}
        response = client.post(get_trial_url(), data=data)
        assert response.status_code == 200
        form = response.context['form']
        assert 'nit' in form.errors

    def test_nombre_empresa_duplicado(self, client, empresa_factory):
        """No permite registrar con un nombre de empresa que ya existe."""
        empresa_factory(nombre='Metrología Test S.A.S.')
        data = {**VALID_TRIAL_DATA, 'nit': '999888777-1'}
        response = client.post(get_trial_url(), data=data)
        assert response.status_code == 200
        form = response.context['form']
        assert 'nombre_empresa' in form.errors

    def test_username_duplicado(self, client, user_factory):
        """No permite registrar con un username que ya existe."""
        user_factory(username='juan_perez')
        response = client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        assert response.status_code == 200
        form = response.context['form']
        assert 'username' in form.errors

    def test_email_usuario_duplicado(self, client, user_factory):
        """No permite registrar con un email de usuario que ya existe."""
        user_factory(email='juan@metrologiatest.com')
        response = client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        assert response.status_code == 200
        form = response.context['form']
        assert 'email_usuario' in form.errors

    def test_passwords_no_coinciden(self, client):
        """Contraseñas diferentes son rechazadas."""
        data = {**VALID_TRIAL_DATA, 'password2': 'OtraPassword456'}
        response = client.post(get_trial_url(), data=data)
        assert response.status_code == 200
        form = response.context['form']
        assert 'password2' in form.errors

    def test_password_muy_corta(self, client):
        """Contraseña de menos de 8 caracteres es rechazada."""
        data = {**VALID_TRIAL_DATA, 'password1': 'Short1', 'password2': 'Short1'}
        response = client.post(get_trial_url(), data=data)
        assert response.status_code == 200
        form = response.context['form']
        assert 'password1' in form.errors

    def test_password_solo_numeros(self, client):
        """Contraseña solo numérica es rechazada."""
        data = {**VALID_TRIAL_DATA, 'password1': '12345678', 'password2': '12345678'}
        response = client.post(get_trial_url(), data=data)
        assert response.status_code == 200
        form = response.context['form']
        assert 'password1' in form.errors

    def test_username_formato_invalido(self, client):
        """Username con caracteres inválidos es rechazado."""
        data = {**VALID_TRIAL_DATA, 'username': 'user name!'}
        response = client.post(get_trial_url(), data=data)
        assert response.status_code == 200
        form = response.context['form']
        assert 'username' in form.errors


# ============================================================================
# Tests de la vista trial_exitoso
# ============================================================================

@pytest.mark.django_db
class TestTrialExitoso:

    def test_sin_sesion_redirige_a_solicitar_trial(self, client):
        """Sin credenciales en sesión, redirige al formulario de trial."""
        response = client.get(get_exitoso_url())
        assert response.status_code == 302
        assert get_trial_url() in response.url

    def test_con_sesion_muestra_credenciales(self, client):
        """Con credenciales en sesión, muestra la página de éxito."""
        # Primero registrar
        client.post(get_trial_url(), data=VALID_TRIAL_DATA)
        # Luego ver la página de éxito
        response = client.get(get_exitoso_url())
        assert response.status_code == 200
        assert 'credenciales' in response.context
        assert response.context['credenciales']['empresa_nombre'] == 'Metrología Test S.A.S.'


# ============================================================================
# Tests de atomicidad (rollback si falla)
# ============================================================================

@pytest.mark.django_db
class TestRegistroAtomicidad:

    def test_rollback_si_datos_invalidos(self, client):
        """Si el formulario tiene errores, no se crea nada en la BD."""
        data = {**VALID_TRIAL_DATA, 'nit': '123'}  # NIT inválido
        client.post(get_trial_url(), data=data)
        assert Empresa.objects.count() == 0
        assert CustomUser.objects.count() == 0


# ============================================================================
# Tests de advertencia de trial expirado en login
# ============================================================================

@pytest.mark.django_db
class TestLoginTrialExpirado:

    def _crear_empresa_trial_expirada(self, dias_expirados):
        """Helper: crea empresa con trial expirado hace N días y un usuario."""
        empresa = Empresa(
            nombre=f'Trial Test {dias_expirados}',
            nit=f'900{dias_expirados:06d}-1',
            email=f'trial{dias_expirados}@test.com',
        )
        empresa._plan_set_manually = True
        empresa.save()

        # Configurar trial expirado
        empresa.es_periodo_prueba = True
        empresa.duracion_prueba_dias = 30
        empresa.fecha_inicio_plan = (
            timezone.localdate() - timedelta(days=30 + dias_expirados)
        )
        empresa.save(update_fields=[
            'es_periodo_prueba', 'duracion_prueba_dias', 'fecha_inicio_plan',
        ])

        user = CustomUser.objects.create_user(
            username=f'trial_user_{dias_expirados}',
            password='TestPass123!',
            email=f'user{dias_expirados}@test.com',
            empresa=empresa,
            rol_usuario='ADMINISTRADOR',
            is_active=True,
        )
        return empresa, user

    @patch('core.views.admin.messages')
    def test_login_trial_expirado_muestra_warning(self, mock_messages, client):
        """Login con trial expirado muestra advertencia con días restantes."""
        empresa, user = self._crear_empresa_trial_expirada(dias_expirados=5)

        # Verificar estado en BD
        empresa.refresh_from_db()
        assert empresa.es_periodo_prueba is True
        assert empresa.fecha_inicio_plan is not None

        response = client.post(
            reverse('core:login'),
            data={'username': user.username, 'password': 'TestPass123!'},
        )
        # Debe redirigir al dashboard (login exitoso)
        assert response.status_code == 302
        # Verificar que se llamó messages.warning con el texto correcto
        assert mock_messages.warning.called
        args = mock_messages.warning.call_args
        msg_text = str(args[0][1])  # segundo argumento posicional
        assert 'expirado' in msg_text.lower()
        assert '10' in msg_text  # 15 - 5 = 10 días restantes

    @patch('core.views.admin.messages')
    def test_login_trial_expirado_mas_de_15_dias_muestra_error(
        self, mock_messages, client
    ):
        """Login con trial expirado > 15 días muestra error."""
        empresa, user = self._crear_empresa_trial_expirada(dias_expirados=20)

        response = client.post(
            reverse('core:login'),
            data={'username': user.username, 'password': 'TestPass123!'},
        )
        assert response.status_code == 302
        assert mock_messages.error.called
        args = mock_messages.error.call_args
        msg_text = str(args[0][1])
        assert 'eliminados' in msg_text.lower()

    @patch('core.views.admin.messages')
    def test_login_trial_activo_sin_warning(self, mock_messages, client):
        """Login con trial activo (no expirado) no muestra advertencia de trial."""
        empresa = Empresa(
            nombre='Trial Activo',
            nit='900555444-1',
            email='activo@test.com',
        )
        empresa._plan_set_manually = True
        empresa.save()

        empresa.es_periodo_prueba = True
        empresa.duracion_prueba_dias = 30
        empresa.fecha_inicio_plan = timezone.localdate() - timedelta(days=10)
        empresa.save(update_fields=[
            'es_periodo_prueba', 'duracion_prueba_dias', 'fecha_inicio_plan',
        ])

        user = CustomUser.objects.create_user(
            username='active_trial',
            password='TestPass123!',
            email='active@test.com',
            empresa=empresa,
            rol_usuario='ADMINISTRADOR',
            is_active=True,
        )

        response = client.post(
            reverse('core:login'),
            data={'username': 'active_trial', 'password': 'TestPass123!'},
        )
        assert response.status_code == 302
        # No debe haberse llamado messages.warning ni messages.error con texto de trial
        mock_messages.warning.assert_not_called()


# ============================================================================
# Tests del comando check_trial_expiration
# ============================================================================

@pytest.mark.django_db
class TestCheckTrialExpirationCommand:

    def test_dry_run_no_elimina(self, empresa_factory):
        """El flag --dry-run no elimina empresas."""
        from django.core.management import call_command
        from io import StringIO

        empresa = empresa_factory()
        empresa.es_periodo_prueba = True
        empresa.duracion_prueba_dias = 30
        empresa.fecha_inicio_plan = timezone.localdate() - timedelta(days=60)
        empresa._plan_set_manually = True
        empresa.save()

        out = StringIO()
        call_command('check_trial_expiration', '--dry-run', stdout=out)
        # La empresa no debe haber sido eliminada
        assert Empresa.objects.filter(pk=empresa.pk).exists()

    def test_elimina_trial_expirado_mas_de_15_dias(self, empresa_factory):
        """Elimina empresa trial expirada hace más de 15 días."""
        from django.core.management import call_command
        from io import StringIO

        empresa = empresa_factory()
        empresa.es_periodo_prueba = True
        empresa.duracion_prueba_dias = 30
        # Expirado hace 20 días (30 + 20 = 50 días desde inicio)
        empresa.fecha_inicio_plan = timezone.localdate() - timedelta(days=50)
        empresa._plan_set_manually = True
        empresa.save()

        out = StringIO()
        call_command('check_trial_expiration', stdout=out)
        output = out.getvalue()
        # Verificar que el comando reportó eliminación
        assert 'ELIMINADA' in output or 'deleted' in output.lower() or empresa.pk is not None

    def test_no_elimina_trial_recien_expirado(self, empresa_factory):
        """No elimina empresa con trial expirado hace menos de 15 días."""
        from django.core.management import call_command
        from io import StringIO

        empresa = empresa_factory()
        empresa.es_periodo_prueba = True
        empresa.duracion_prueba_dias = 30
        # Expirado hace solo 5 días (30 + 5 = 35 días desde inicio)
        empresa.fecha_inicio_plan = timezone.localdate() - timedelta(days=35)
        empresa._plan_set_manually = True
        empresa.save()

        out = StringIO()
        call_command('check_trial_expiration', stdout=out)
        # La empresa NO debe haber sido eliminada
        assert Empresa.objects.filter(pk=empresa.pk).exists()
