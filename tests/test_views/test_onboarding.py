"""
Tests para el módulo de Onboarding Guiado (Módulo B).
Cubre: modelo OnboardingProgress, signal auto-crear, API endpoints,
marcado de pasos en vistas existentes, integración con dashboard,
y creación de equipo demo en registro trial.
"""
import pytest
from datetime import date, timedelta

from django.test import Client
from django.urls import reverse
from django.utils import timezone

from core.models import Empresa, CustomUser, Equipo, OnboardingProgress
from tests.factories import EmpresaFactory, UserFactory


# ============================================================================
# Helpers
# ============================================================================

def _crear_empresa_trial(**kwargs):
    """Crea una empresa con período de prueba activo (usa activar_periodo_prueba)."""
    empresa = EmpresaFactory(**kwargs)
    empresa.activar_periodo_prueba(duracion_dias=30)
    return empresa


def _crear_empresa_no_trial(**kwargs):
    """Crea una empresa sin período de prueba (plan gratuito por defecto)."""
    return EmpresaFactory(**kwargs)


def _crear_usuario_trial_con_onboarding(empresa=None, **kwargs):
    """Crea un usuario trial con OnboardingProgress (creación explícita)."""
    if empresa is None:
        empresa = _crear_empresa_trial()
    user = UserFactory(empresa=empresa, **kwargs)
    progress, _ = OnboardingProgress.objects.get_or_create(usuario=user)
    return user


def _crear_cliente_autenticado_trial():
    """Crea un cliente autenticado con usuario trial y OnboardingProgress."""
    empresa = _crear_empresa_trial()
    user = UserFactory(empresa=empresa)
    OnboardingProgress.objects.get_or_create(usuario=user)
    client = Client()
    client.force_login(user)
    client.user = user
    return client


# ============================================================================
# TestOnboardingModel - Tests del modelo OnboardingProgress
# ============================================================================

@pytest.mark.django_db
class TestOnboardingModel:

    def test_onboarding_creado_por_signal(self):
        """Crear usuario trial con create_user genera OnboardingProgress por signal."""
        empresa = _crear_empresa_trial()
        # Usar create_user directamente para que el signal post_save funcione
        user = CustomUser.objects.create_user(
            username='signal_test_user',
            password='testpass123',
            empresa=empresa,
        )
        assert OnboardingProgress.objects.filter(usuario=user).exists()
        progress = user.onboarding_progress
        assert progress.tour_completado is False
        assert progress.paso_crear_equipo is False
        assert progress.paso_registrar_calibracion is False
        assert progress.paso_generar_reporte is False

    def test_onboarding_no_creado_sin_trial(self):
        """Crear usuario de empresa no-trial NO genera OnboardingProgress."""
        empresa = _crear_empresa_no_trial()
        user = CustomUser.objects.create_user(
            username='no_trial_user',
            password='testpass123',
            empresa=empresa,
        )
        assert not OnboardingProgress.objects.filter(usuario=user).exists()

    def test_marcar_paso_actualiza_progreso(self):
        """marcar_paso() marca un paso y actualiza el progreso."""
        user = _crear_usuario_trial_con_onboarding()
        progress = user.onboarding_progress
        assert progress.pasos_completados == 0
        assert progress.porcentaje == 0

        result = progress.marcar_paso('crear_equipo')
        assert result is True
        progress.refresh_from_db()
        assert progress.paso_crear_equipo is True
        assert progress.pasos_completados == 1
        assert progress.porcentaje == 33
        assert progress.completado is False

    def test_marcar_paso_no_duplica(self):
        """marcar_paso() retorna False si el paso ya estaba marcado."""
        user = _crear_usuario_trial_con_onboarding()
        progress = user.onboarding_progress
        progress.marcar_paso('crear_equipo')
        result = progress.marcar_paso('crear_equipo')
        assert result is False

    def test_completar_todos_los_pasos(self):
        """Al completar los 3 pasos, el onboarding se marca como completado."""
        user = _crear_usuario_trial_con_onboarding()
        progress = user.onboarding_progress
        progress.marcar_paso('crear_equipo')
        progress.marcar_paso('registrar_calibracion')
        progress.marcar_paso('generar_reporte')
        progress.refresh_from_db()
        assert progress.completado is True
        assert progress.pasos_completados == 3
        assert progress.porcentaje == 100
        assert progress.fecha_completado is not None

    def test_str_representation(self):
        """__str__ muestra formato correcto."""
        user = _crear_usuario_trial_con_onboarding()
        progress = user.onboarding_progress
        assert f"Onboarding {user.username}: 0/3" == str(progress)


# ============================================================================
# TestOnboardingAPI - Tests de los endpoints API
# ============================================================================

@pytest.mark.django_db
class TestOnboardingAPI:

    def test_progreso_retorna_json(self):
        """GET /onboarding/progreso/ retorna JSON con estado actual."""
        client = _crear_cliente_autenticado_trial()
        url = reverse('core:onboarding_progreso')
        response = client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data['has_onboarding'] is True
        assert data['tour_completado'] is False
        assert data['pasos_completados'] == 0
        assert data['total_pasos'] == 3
        assert data['porcentaje'] == 0
        assert 'pasos' in data
        assert data['pasos']['crear_equipo'] is False

    def test_completar_tour_marca_completado(self):
        """POST /onboarding/completar-tour/ marca tour_completado=True."""
        client = _crear_cliente_autenticado_trial()
        url = reverse('core:onboarding_completar_tour')
        response = client.post(url)
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True

        # Verificar en BD
        client.user.onboarding_progress.refresh_from_db()
        assert client.user.onboarding_progress.tour_completado is True

    def test_progreso_sin_onboarding(self):
        """Usuario sin onboarding recibe has_onboarding=False."""
        empresa = _crear_empresa_no_trial()
        user = UserFactory(empresa=empresa)
        client = Client()
        client.force_login(user)

        url = reverse('core:onboarding_progreso')
        response = client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data['has_onboarding'] is False

    def test_api_requiere_login(self):
        """Endpoints de onboarding requieren autenticación."""
        client = Client()
        url_progreso = reverse('core:onboarding_progreso')
        url_tour = reverse('core:onboarding_completar_tour')

        response = client.get(url_progreso)
        assert response.status_code == 302  # Redirect a login

        response = client.post(url_tour)
        assert response.status_code == 302  # Redirect a login


# ============================================================================
# TestOnboardingEnVistas - Tests de marcado de pasos en vistas existentes
# ============================================================================

@pytest.mark.django_db
class TestOnboardingEnVistas:

    def test_crear_equipo_marca_paso(self):
        """_marcar_paso_onboarding marca paso_crear_equipo=True."""
        from core.views.onboarding import _marcar_paso_onboarding
        user = _crear_usuario_trial_con_onboarding()
        _marcar_paso_onboarding(user, 'crear_equipo')
        user.onboarding_progress.refresh_from_db()
        assert user.onboarding_progress.paso_crear_equipo is True

    def test_registrar_calibracion_marca_paso(self):
        """_marcar_paso_onboarding marca paso_registrar_calibracion=True."""
        from core.views.onboarding import _marcar_paso_onboarding
        user = _crear_usuario_trial_con_onboarding()
        _marcar_paso_onboarding(user, 'registrar_calibracion')
        user.onboarding_progress.refresh_from_db()
        assert user.onboarding_progress.paso_registrar_calibracion is True

    def test_generar_reporte_marca_paso(self):
        """_marcar_paso_onboarding marca paso_generar_reporte=True."""
        from core.views.onboarding import _marcar_paso_onboarding
        user = _crear_usuario_trial_con_onboarding()
        _marcar_paso_onboarding(user, 'generar_reporte')
        user.onboarding_progress.refresh_from_db()
        assert user.onboarding_progress.paso_generar_reporte is True

    def test_paso_no_se_marca_sin_onboarding(self):
        """_marcar_paso_onboarding no falla si el usuario no tiene onboarding."""
        empresa = _crear_empresa_no_trial()
        user = UserFactory(empresa=empresa)
        from core.views.onboarding import _marcar_paso_onboarding
        # No debe lanzar excepción
        _marcar_paso_onboarding(user, 'crear_equipo')


# ============================================================================
# TestOnboardingEnDashboard - Tests de integración con el dashboard
# ============================================================================

@pytest.mark.django_db
class TestOnboardingEnDashboard:

    def test_dashboard_muestra_checklist_para_trial(self):
        """Dashboard de empresa trial muestra el checklist de onboarding."""
        client = _crear_cliente_autenticado_trial()
        url = reverse('core:dashboard')
        response = client.get(url)
        assert response.status_code == 200
        assert 'onboarding_progress' in response.context
        assert response.context['onboarding_progress'] is not None
        content = response.content.decode()
        assert 'Primeros pasos en SAM' in content

    def test_dashboard_no_muestra_checklist_sin_trial(self):
        """Dashboard de empresa normal NO muestra checklist."""
        empresa = _crear_empresa_no_trial()
        user = UserFactory(empresa=empresa)
        client = Client()
        client.force_login(user)
        url = reverse('core:dashboard')
        response = client.get(url)
        assert response.status_code == 200
        assert response.context.get('onboarding_progress') is None
        content = response.content.decode()
        assert 'Primeros pasos en SAM' not in content

    def test_dashboard_no_muestra_checklist_completado(self):
        """Dashboard no muestra checklist cuando onboarding está completado."""
        client = _crear_cliente_autenticado_trial()
        progress = client.user.onboarding_progress
        progress.paso_crear_equipo = True
        progress.paso_registrar_calibracion = True
        progress.paso_generar_reporte = True
        progress.fecha_completado = timezone.now()
        progress.save()

        url = reverse('core:dashboard')
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Primeros pasos en SAM' not in content

    def test_porcentaje_progreso(self):
        """1 de 3 pasos completados muestra 33% de progreso."""
        user = _crear_usuario_trial_con_onboarding()
        progress = user.onboarding_progress
        progress.marcar_paso('crear_equipo')
        progress.refresh_from_db()
        assert progress.porcentaje == 33
        assert progress.pasos_completados == 1
        assert progress.total_pasos == 3


# ============================================================================
# TestEquipoDemoEnRegistro - Tests de creación de equipo demo
# ============================================================================

# Datos válidos para registro trial (solo empresa, usuarios se auto-generan)
VALID_TRIAL_DATA = {
    'nombre_empresa': 'Metrología Onboarding S.A.S.',
    'nit': '900777888-1',
    'email_empresa': 'contacto@metrologiaonb.com',
    'telefono': '+57 300 777 8888',
}
# Username auto-generado del admin: dir + "metro" + últimos 4 dígitos NIT "9007778881" → "8881"
ADMIN_USERNAME_ONB = 'dirmetro8881'


def _get_trial_url():
    return reverse('core:solicitar_trial')


@pytest.mark.django_db
class TestEquipoDemoEnRegistro:

    def test_registro_trial_crea_equipo_demo(self, client):
        """Al registrar trial, se crea equipo EQ-DEMO-001."""
        client.post(_get_trial_url(), data=VALID_TRIAL_DATA)
        empresa = Empresa.objects.get(nombre='Metrología Onboarding S.A.S.')
        assert Equipo.objects.filter(
            codigo_interno='EQ-DEMO-001',
            empresa=empresa,
        ).exists()

    def test_equipo_demo_tiene_datos_completos(self, client):
        """El equipo demo tiene marca, modelo, rango y resolución."""
        client.post(_get_trial_url(), data=VALID_TRIAL_DATA)
        empresa = Empresa.objects.get(nombre='Metrología Onboarding S.A.S.')
        equipo = Equipo.objects.get(codigo_interno='EQ-DEMO-001', empresa=empresa)
        assert equipo.nombre == 'Balanza Analítica (Demo)'
        assert equipo.marca == 'Ohaus'
        assert equipo.modelo == 'Pioneer PX224'
        assert equipo.rango_medida == '0 - 220 g'
        assert equipo.resolucion == '0.0001 g (0.1 mg)'
        assert equipo.estado == 'Activo'
        assert equipo.ubicacion == 'Laboratorio Principal'

    def test_equipo_demo_tiene_calibracion_proxima(self, client):
        """El equipo demo tiene proxima_calibracion configurada."""
        client.post(_get_trial_url(), data=VALID_TRIAL_DATA)
        empresa = Empresa.objects.get(nombre='Metrología Onboarding S.A.S.')
        equipo = Equipo.objects.get(codigo_interno='EQ-DEMO-001', empresa=empresa)
        assert equipo.proxima_calibracion is not None
        assert equipo.fecha_ultima_calibracion is not None
        assert equipo.frecuencia_calibracion_meses is not None

    def test_dashboard_trial_muestra_metricas(self, client):
        """Dashboard de empresa trial con equipo demo muestra total_equipos >= 1."""
        client.post(_get_trial_url(), data=VALID_TRIAL_DATA)
        admin = CustomUser.objects.get(username=ADMIN_USERNAME_ONB)
        client.force_login(admin)
        response = client.get(reverse('core:dashboard'))
        assert response.status_code == 200
        assert response.context['total_equipos'] >= 1


# ============================================================================
# TestOnboardingPermisosPrestamos - Permisos de préstamos en trial
# ============================================================================

@pytest.mark.django_db
class TestOnboardingPermisosPrestamos:

    def test_prestamos_permisos_asignados_admin(self, client):
        """Admin trial tiene permiso can_add_prestamo y can_change_prestamo."""
        from django.contrib.auth.models import Permission
        client.post(_get_trial_url(), data=VALID_TRIAL_DATA)
        admin = CustomUser.objects.get(username=ADMIN_USERNAME_ONB)
        permisos = set(admin.user_permissions.values_list('codename', flat=True))
        assert 'can_add_prestamo' in permisos
        assert 'can_change_prestamo' in permisos
        assert 'can_view_prestamo' in permisos

    def test_prestamos_permisos_asignados_tecnico(self, client):
        """Técnico trial tiene permiso can_view_prestamo."""
        client.post(_get_trial_url(), data=VALID_TRIAL_DATA)
        # El técnico se genera con username 'tecmetro' + últimos 4 dígitos del NIT
        tecnico = CustomUser.objects.filter(
            empresa__nombre='Metrología Onboarding S.A.S.',
            rol_usuario='TECNICO'
        ).first()
        assert tecnico is not None
        permisos = set(tecnico.user_permissions.values_list('codename', flat=True))
        assert 'can_view_prestamo' in permisos


# ============================================================================
# TestTourMultiPaginaScripts - Scripts Shepherd.js en base.html
# ============================================================================

@pytest.mark.django_db
class TestTourMultiPaginaScripts:

    def test_shepherd_cargado_en_dashboard(self):
        """Shepherd.js se carga en dashboard cuando hay onboarding activo."""
        client = _crear_cliente_autenticado_trial()
        response = client.get(reverse('core:dashboard'))
        assert response.status_code == 200
        content = response.content.decode()
        assert 'shepherd.min.js' in content
        assert 'onboarding_tour' in content

    def test_shepherd_cargado_en_equipos(self):
        """Shepherd.js se carga en lista de equipos cuando hay onboarding activo."""
        from django.contrib.auth.models import Permission
        client = _crear_cliente_autenticado_trial()
        # El usuario necesita permiso view_equipo para acceder a la lista
        perm = Permission.objects.filter(codename='view_equipo').first()
        if perm:
            client.user.user_permissions.add(perm)
        response = client.get(reverse('core:home'))
        assert response.status_code == 200
        content = response.content.decode()
        assert 'shepherd.min.js' in content

    def test_shepherd_no_cargado_sin_onboarding(self):
        """Shepherd.js NO se carga para usuarios sin onboarding activo."""
        empresa = _crear_empresa_no_trial()
        user = UserFactory(empresa=empresa)
        client = Client()
        client.force_login(user)
        response = client.get(reverse('core:dashboard'))
        assert response.status_code == 200
        content = response.content.decode()
        assert 'shepherd.min.js' not in content

    def test_shepherd_no_cargado_onboarding_completado(self):
        """Shepherd.js NO se carga cuando onboarding está completado."""
        client = _crear_cliente_autenticado_trial()
        progress = client.user.onboarding_progress
        progress.paso_crear_equipo = True
        progress.paso_registrar_calibracion = True
        progress.paso_generar_reporte = True
        progress.fecha_completado = timezone.now()
        progress.save()

        response = client.get(reverse('core:dashboard'))
        assert response.status_code == 200
        content = response.content.decode()
        assert 'shepherd.min.js' not in content
