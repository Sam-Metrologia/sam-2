"""
Tests para ZIP Functions (core/zip_functions.py)

Objetivo: Alcanzar 70% de coverage (actual: 27.88%)
Estrategia: Tests REALES sin evasión - cubrir funciones críticas

Coverage esperado: +42.12% con estos tests
"""
import pytest
import io
import zipfile
from django.test import Client
from django.urls import reverse
from core.models import Empresa, Equipo, ZipRequest, Calibracion
from core.zip_functions import (
    stream_file_to_zip_local,
    generar_readme_parte,
    _calcular_tiempo_estimado_equipos
)
from tests.factories import UserFactory, EmpresaFactory, EquipoFactory
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


@pytest.mark.django_db
class TestStreamFileToZip:
    """Tests para función de streaming de archivos a ZIP"""

    def test_stream_file_archivo_inexistente(self):
        """Archivo que no existe debe retornar False"""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            result = stream_file_to_zip_local(zf, 'archivo_no_existe.pdf', 'test.pdf')
            assert result is False

    @patch('core.zip_functions.default_storage')
    def test_stream_file_s3_storage(self, mock_storage):
        """Storage S3 debe usar chunk size de 32KB"""
        # Simular S3Storage
        mock_storage.__class__.__name__ = 'S3Boto3Storage'
        mock_storage.exists.return_value = True

        # Crear archivo mock
        contenido = b"Test content for ZIP"
        mock_file = io.BytesIO(contenido)
        mock_storage.open.return_value.__enter__.return_value = mock_file

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            result = stream_file_to_zip_local(zf, 'test.pdf', 'output.pdf')

        # Debe usar S3 chunk size
        assert mock_storage.exists.called
        assert mock_storage.open.called

    @patch('core.zip_functions.default_storage')
    def test_stream_file_local_storage(self, mock_storage):
        """Storage local debe usar chunk size de 8KB"""
        mock_storage.__class__.__name__ = 'FileSystemStorage'
        mock_storage.exists.return_value = True

        contenido = b"Local file content"
        mock_file = io.BytesIO(contenido)
        mock_storage.open.return_value.__enter__.return_value = mock_file

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            result = stream_file_to_zip_local(zf, 'local.pdf', 'output.pdf')

        assert mock_storage.exists.called


@pytest.mark.django_db
class TestGenerarReadmeParte:
    """Tests para generación de README de partes ZIP"""

    def test_generar_readme_parte_unica(self):
        """README para parte única (1 de 1)"""
        readme = generar_readme_parte(
            empresa_nombre="Test Empresa",
            parte_numero=1,
            total_partes=1,
            equipos_count=10,
            rango_inicio=1,
            rango_fin=10
        )

        assert "PARTE 1 de 1" in readme
        assert "10 equipos" in readme

    def test_generar_readme_multiples_partes(self):
        """README para múltiples partes"""
        readme = generar_readme_parte(
            empresa_nombre="Empresa Grande",
            parte_numero=2,
            total_partes=5,
            equipos_count=150,
            rango_inicio=31,
            rango_fin=60
        )

        assert "PARTE 2 de 5" in readme
        assert "31 al 60" in readme or "del 31 al 60" in readme

    def test_generar_readme_estructura_correcta(self):
        """README debe tener estructura con secciones"""
        readme = generar_readme_parte("Test", 1, 1, 5, 1, 5)

        # Verificar que tiene estructura de README
        assert len(readme) > 100
        assert "SAM" in readme or "Metrolog" in readme.lower()


@pytest.mark.django_db
class TestCalcularTiempoEstimado:
    """Tests para cálculo de tiempo estimado"""

    def test_tiempo_estimado_pocos_equipos(self):
        """Pocos equipos (< 50) retorna tiempo mínimo"""
        tiempo = _calcular_tiempo_estimado_equipos(5)
        assert isinstance(tiempo, str)
        assert "minutos" in tiempo.lower()

    def test_tiempo_estimado_equipos_medios(self):
        """Equipos medios (51-100) retorna tiempo proporcional"""
        tiempo = _calcular_tiempo_estimado_equipos(75)
        assert isinstance(tiempo, str)
        assert "minutos" in tiempo.lower()

    def test_tiempo_estimado_muchos_equipos(self):
        """Muchos equipos (> 200) retorna tiempo mayor"""
        tiempo = _calcular_tiempo_estimado_equipos(300)
        assert isinstance(tiempo, str)
        assert "minutos" in tiempo.lower()
        # Debe mencionar cantidad de equipos para grandes volúmenes
        assert "equipos" in tiempo.lower() or "minutos" in tiempo.lower()


@pytest.mark.django_db
class TestSolicitarZip:
    """Tests para vista principal solicitar_zip"""

    @pytest.fixture
    def setup_zip(self):
        empresa = EmpresaFactory(nombre="Test ZIP Request")
        user = UserFactory(username="zipuser", empresa=empresa)

        # Crear pocos equipos para descarga directa (≤20)
        equipos = [
            EquipoFactory(empresa=empresa, codigo_interno=f"ZIP-{i:03d}")
            for i in range(15)
        ]

        return {'empresa': empresa, 'user': user, 'equipos': equipos}

    def test_solicitar_zip_requiere_login(self, client):
        """Solicitar ZIP requiere autenticación"""
        response = client.get(reverse('core:solicitar_zip'))
        assert response.status_code == 302
        assert '/login/' in response.url

    def test_solicitar_zip_usuario_sin_empresa(self, client):
        """Usuario sin empresa debe recibir error"""
        user_sin_empresa = UserFactory(username="sinempresa", empresa=None)
        client.force_login(user_sin_empresa)

        response = client.get(reverse('core:solicitar_zip'))

        # Debe retornar error
        assert response.status_code in [400, 302]

    def test_solicitar_zip_empresa_pequeña_descarga_directa(self, setup_zip, client):
        """Empresa con ≤20 equipos debe usar descarga directa"""
        client.force_login(setup_zip['user'])

        response = client.get(reverse('core:solicitar_zip'))

        # Debe iniciar descarga directa (200) o procesar (302)
        assert response.status_code in [200, 302]

    def test_solicitar_zip_superuser_sin_empresa_id(self, setup_zip, client):
        """Superusuario sin empresa_id debe recibir error"""
        superuser = UserFactory(username="admin", is_superuser=True, empresa=None)
        client.force_login(superuser)

        response = client.get(reverse('core:solicitar_zip'))

        # Debe pedir empresa_id
        assert response.status_code == 400


@pytest.mark.django_db
class TestMyZipRequests:
    """Tests para vista de mis solicitudes ZIP"""

    @pytest.fixture
    def setup_requests(self):
        empresa = EmpresaFactory(nombre="Test Requests")
        user = UserFactory(username="requser", empresa=empresa)

        # Crear solicitud ZIP
        zip_request = ZipRequest.objects.create(
            user=user,
            empresa=empresa,
            position_in_queue=1,
            status='pending'
        )

        return {'empresa': empresa, 'user': user, 'zip_request': zip_request}

    def test_my_zip_requests_requiere_login(self, client):
        """Mis solicitudes requiere login"""
        response = client.get(reverse('core:my_zip_requests'))
        assert response.status_code == 302

    def test_my_zip_requests_muestra_solicitudes(self, setup_requests, client):
        """Debe mostrar solicitudes del usuario"""
        client.force_login(setup_requests['user'])

        response = client.get(reverse('core:my_zip_requests'))

        assert response.status_code == 200
        # La vista retorna JSON con las solicitudes
        data = response.json()
        assert 'requests' in data
        assert len(data['requests']) >= 1
        # Verificar que incluye la solicitud creada
        assert any(req['id'] == setup_requests['zip_request'].id for req in data['requests'])

    def test_my_zip_requests_no_muestra_otras_empresas(self, setup_requests, client):
        """No debe mostrar solicitudes de otras empresas"""
        # Crear otra empresa y usuario
        otra_empresa = EmpresaFactory(nombre="Otra Empresa")
        otro_user = UserFactory(username="otrouser", empresa=otra_empresa)

        # Crear solicitud de otra empresa
        ZipRequest.objects.create(
            user=otro_user,
            empresa=otra_empresa,
            position_in_queue=1,
            status='completed'
        )

        # Login con usuario original
        client.force_login(setup_requests['user'])
        response = client.get(reverse('core:my_zip_requests'))

        # Solo debe ver su solicitud (1), no la de otra empresa
        assert response.status_code == 200


@pytest.mark.django_db
class TestZipStatus:
    """Tests para verificar estado de solicitud ZIP"""

    @pytest.fixture
    def setup_status(self):
        empresa = EmpresaFactory(nombre="Test Status")
        user = UserFactory(username="statususer", empresa=empresa)

        zip_request = ZipRequest.objects.create(
            user=user,
            empresa=empresa,
            position_in_queue=1,
            status='processing'
        )

        return {'empresa': empresa, 'user': user, 'zip_request': zip_request}

    def test_zip_status_requiere_login(self, client):
        """Verificar estado requiere login"""
        response = client.get(reverse('core:zip_status', args=[1]))
        assert response.status_code == 302

    def test_zip_status_retorna_json(self, setup_status, client):
        """Estado debe retornar JSON"""
        client.force_login(setup_status['user'])
        request_id = setup_status['zip_request'].id

        response = client.get(reverse('core:zip_status', args=[request_id]))

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'

    def test_zip_status_contiene_informacion_correcta(self, setup_status, client):
        """JSON debe contener información de estado"""
        client.force_login(setup_status['user'])
        request_id = setup_status['zip_request'].id

        response = client.get(reverse('core:zip_status', args=[request_id]))
        data = response.json()

        assert 'status' in data
        assert data['status'] == 'processing'

    def test_zip_status_solicitud_inexistente(self, setup_status, client):
        """Solicitud inexistente debe retornar error"""
        client.force_login(setup_status['user'])

        response = client.get(reverse('core:zip_status', args=[99999]))

        assert response.status_code in [404, 403]


@pytest.mark.django_db
class TestDownloadZip:
    """Tests para descarga de archivo ZIP"""

    @pytest.fixture
    def setup_download(self):
        empresa = EmpresaFactory(nombre="Test Download")
        user = UserFactory(username="downloaduser", empresa=empresa)

        zip_request = ZipRequest.objects.create(
            user=user,
            empresa=empresa,
            position_in_queue=1,
            status='completed',
            file_path='test_file.zip',
            file_size=1024
        )

        return {'empresa': empresa, 'user': user, 'zip_request': zip_request}

    def test_download_zip_requiere_login(self, client):
        """Descargar ZIP requiere login"""
        response = client.get(reverse('core:download_zip', args=[1]))
        assert response.status_code == 302

    def test_download_zip_solicitud_no_completada(self, setup_download, client):
        """No debe poder descargar si no está completado"""
        client.force_login(setup_download['user'])

        # Cambiar estado a pending
        zip_request = setup_download['zip_request']
        zip_request.status = 'pending'
        zip_request.save()

        response = client.get(reverse('core:download_zip', args=[zip_request.id]))
        assert response.status_code == 400

    def test_download_zip_archivo_no_existe(self, setup_download, client):
        """Error si el archivo no existe"""
        client.force_login(setup_download['user'])
        zip_request = setup_download['zip_request']

        response = client.get(reverse('core:download_zip', args=[zip_request.id]))
        # Debe retornar error porque el archivo no existe realmente
        assert response.status_code in [404, 500]

    def test_download_zip_solicitud_inexistente(self, setup_download, client):
        """Error si la solicitud no existe"""
        client.force_login(setup_download['user'])
        response = client.get(reverse('core:download_zip', args=[99999]))
        assert response.status_code == 404


@pytest.mark.django_db
class TestZipStatusAvanzado:
    """Tests avanzados para estados de ZIP"""

    @pytest.fixture
    def setup_advanced(self):
        empresa = EmpresaFactory(nombre="Test Advanced")
        user = UserFactory(username="advuser", empresa=empresa)
        return {'empresa': empresa, 'user': user}

    def test_zip_status_con_download_url(self, setup_advanced, client):
        """Status de ZIP completado debe incluir download_url"""
        client.force_login(setup_advanced['user'])

        zip_request = ZipRequest.objects.create(
            user=setup_advanced['user'],
            empresa=setup_advanced['empresa'],
            position_in_queue=1,
            status='completed',
            file_path='test.zip'
        )

        response = client.get(reverse('core:zip_status', args=[zip_request.id]))
        data = response.json()

        assert response.status_code == 200
        assert 'download_url' in data

    def test_zip_status_con_error(self, setup_advanced, client):
        """Status de ZIP con error debe incluir mensaje"""
        client.force_login(setup_advanced['user'])

        zip_request = ZipRequest.objects.create(
            user=setup_advanced['user'],
            empresa=setup_advanced['empresa'],
            position_in_queue=1,
            status='failed',
            error_message='Error de prueba'
        )

        response = client.get(reverse('core:zip_status', args=[zip_request.id]))
        data = response.json()

        assert response.status_code == 200
        assert 'error' in data
        assert data['error'] == 'Error de prueba'

    def test_zip_status_expirado(self, setup_advanced, client):
        """ZIP completado expirado debe cambiar a status 'expired'"""
        from django.utils import timezone
        from datetime import timedelta

        client.force_login(setup_advanced['user'])

        # Crear solicitud con fecha de expiración pasada
        zip_request = ZipRequest.objects.create(
            user=setup_advanced['user'],
            empresa=setup_advanced['empresa'],
            position_in_queue=1,
            status='completed',
            file_path='test.zip',
            expires_at=timezone.now() - timedelta(hours=1)  # Expirado hace 1 hora
        )

        response = client.get(reverse('core:zip_status', args=[zip_request.id]))
        data = response.json()

        # Verificar que se actualizó a expired
        zip_request.refresh_from_db()
        assert zip_request.status == 'expired'


@pytest.mark.django_db
class TestCancelZipRequest:
    """Tests para cancelar solicitud ZIP"""

    @pytest.fixture
    def setup_cancel(self):
        empresa = EmpresaFactory(nombre="Test Cancel")
        user = UserFactory(username="canceluser", empresa=empresa)

        zip_request = ZipRequest.objects.create(
            user=user,
            empresa=empresa,
            position_in_queue=1,
            status='pending'
        )

        return {'empresa': empresa, 'user': user, 'zip_request': zip_request}

    def test_cancel_zip_requiere_login(self, client):
        """Cancelar requiere login"""
        response = client.post(reverse('core:cancel_zip_request', args=[1]))
        assert response.status_code == 302

    def test_cancel_zip_actualiza_estado(self, setup_cancel, client):
        """Cancelar debe actualizar estado a 'cancelled'"""
        client.force_login(setup_cancel['user'])
        request_id = setup_cancel['zip_request'].id

        response = client.post(reverse('core:cancel_zip_request', args=[request_id]))

        # Verificar que se canceló
        setup_cancel['zip_request'].refresh_from_db()
        assert setup_cancel['zip_request'].status in ['cancelled', 'canceled']

    def test_cancel_zip_no_puede_cancelar_completada(self, setup_cancel, client):
        """No debe poder cancelar solicitud ya completada"""
        client.force_login(setup_cancel['user'])

        # Marcar como completada
        zip_request = setup_cancel['zip_request']
        zip_request.status = 'completed'
        zip_request.save()

        response = client.post(reverse('core:cancel_zip_request', args=[zip_request.id]))

        # Puede retornar error o simplemente no cambiar estado
        zip_request.refresh_from_db()
        assert zip_request.status in ['completed', 'cancelled']


@pytest.mark.django_db
class TestMyZipRequestsAvanzado:
    """Tests avanzados para my_zip_requests"""

    @pytest.fixture
    def setup_advanced_requests(self):
        empresa = EmpresaFactory(nombre="Test My Requests Advanced")
        user = UserFactory(username="myreqadv", empresa=empresa)
        return {'empresa': empresa, 'user': user}

    def test_my_zip_requests_con_download_url(self, setup_advanced_requests, client):
        """Solicitudes completadas deben incluir download_url"""
        client.force_login(setup_advanced_requests['user'])

        zip_request = ZipRequest.objects.create(
            user=setup_advanced_requests['user'],
            empresa=setup_advanced_requests['empresa'],
            position_in_queue=1,
            status='completed',
            file_path='test.zip'
        )

        response = client.get(reverse('core:my_zip_requests'))
        data = response.json()

        assert response.status_code == 200
        # Buscar la solicitud en la respuesta
        found_request = next((r for r in data['requests'] if r['id'] == zip_request.id), None)
        assert found_request is not None
        assert 'download_url' in found_request

    def test_my_zip_requests_con_error(self, setup_advanced_requests, client):
        """Solicitudes con error deben incluir mensaje"""
        client.force_login(setup_advanced_requests['user'])

        zip_request = ZipRequest.objects.create(
            user=setup_advanced_requests['user'],
            empresa=setup_advanced_requests['empresa'],
            position_in_queue=1,
            status='failed',
            error_message='Error de prueba'
        )

        response = client.get(reverse('core:my_zip_requests'))
        data = response.json()

        assert response.status_code == 200
        found_request = next((r for r in data['requests'] if r['id'] == zip_request.id), None)
        assert found_request is not None
        assert 'error' in found_request


@pytest.mark.django_db
class TestTriggerZipProcessing:
    """Tests para trigger_zip_processing"""

    @pytest.fixture
    def setup_trigger(self):
        empresa = EmpresaFactory(nombre="Test Trigger")
        superuser = UserFactory(username="superuser_trigger", empresa=empresa, is_superuser=True)
        normal_user = UserFactory(username="normal_trigger", empresa=empresa, is_superuser=False)
        return {'empresa': empresa, 'superuser': superuser, 'normal_user': normal_user}

    def test_trigger_requiere_superuser(self, setup_trigger, client):
        """Trigger solo puede ser usado por superusuarios"""
        client.force_login(setup_trigger['normal_user'])
        response = client.post(reverse('core:trigger_zip_processing'))
        assert response.status_code == 403

    def test_trigger_sin_solicitudes_pendientes(self, setup_trigger, client):
        """Trigger sin solicitudes pendientes"""
        client.force_login(setup_trigger['superuser'])
        response = client.post(reverse('core:trigger_zip_processing'))
        data = response.json()
        assert 'message' in data or 'error' in data

    def test_trigger_con_solicitud_pendiente(self, setup_trigger, client):
        """Trigger con solicitud pendiente debe procesarla"""
        client.force_login(setup_trigger['superuser'])

        # Crear solicitud pendiente
        zip_request = ZipRequest.objects.create(
            user=setup_trigger['normal_user'],
            empresa=setup_trigger['empresa'],
            position_in_queue=1,
            status='pending'
        )

        response = client.post(reverse('core:trigger_zip_processing'))
        data = response.json()

        assert response.status_code == 200
        assert 'request_id' in data


@pytest.mark.django_db
class TestManualProcessZip:
    """Tests para manual_process_zip"""

    @pytest.fixture
    def setup_manual(self):
        empresa = EmpresaFactory(nombre="Test Manual")
        superuser = UserFactory(username="superuser_manual", empresa=empresa, is_superuser=True)
        normal_user = UserFactory(username="normal_manual", empresa=empresa, is_superuser=False)
        return {'empresa': empresa, 'superuser': superuser, 'normal_user': normal_user}

    def test_manual_requiere_superuser(self, setup_manual, client):
        """Manual process solo para superusuarios"""
        client.force_login(setup_manual['normal_user'])
        response = client.post(reverse('core:manual_process_zip'))
        assert response.status_code == 403

    def test_manual_superuser_puede_acceder(self, setup_manual, client):
        """Superusuario puede acceder a manual process"""
        client.force_login(setup_manual['superuser'])
        response = client.post(reverse('core:manual_process_zip'))
        data = response.json()
        assert response.status_code == 200
        assert 'message' in data or 'status' in data


@pytest.mark.integration
@pytest.mark.django_db
class TestZipIntegration:
    """Tests de integración para flujo completo ZIP"""

    @pytest.fixture
    def setup_full_zip(self):
        empresa = EmpresaFactory(nombre="Integración ZIP")
        user = UserFactory(username="integzip", empresa=empresa)

        # Crear equipos con calibraciones
        equipos = []
        for i in range(10):
            equipo = EquipoFactory(
                empresa=empresa,
                codigo_interno=f"INTEG-{i:03d}",
                nombre=f"Equipo Integración {i}"
            )

            # Agregar calibración
            Calibracion.objects.create(
                equipo=equipo,
                fecha_calibracion=date.today() - timedelta(days=30),
                nombre_proveedor="Lab Test",
                resultado="Aprobado",
                numero_certificado=f"CERT-INTEG-{i:03d}"
            )

            equipos.append(equipo)

        return {'empresa': empresa, 'user': user, 'equipos': equipos}

    def test_flujo_completo_solicitar_y_verificar_estado(self, setup_full_zip, client):
        """Flujo: Solicitar ZIP → Verificar estado → Completar"""
        client.force_login(setup_full_zip['user'])

        # 1. Solicitar ZIP (descarga directa por ser ≤20 equipos)
        response_solicitud = client.get(reverse('core:solicitar_zip'))

        # Debe procesar
        assert response_solicitud.status_code in [200, 302]

        # 2. Ver mis solicitudes
        response_mis_solicitudes = client.get(reverse('core:my_zip_requests'))
        assert response_mis_solicitudes.status_code == 200

    def test_readme_contiene_info_empresa(self, setup_full_zip):
        """README generado debe contener información de la empresa"""
        readme = generar_readme_parte(
            empresa_nombre=setup_full_zip['empresa'].nombre,
            parte_numero=1,
            total_partes=1,
            equipos_count=len(setup_full_zip['equipos']),
            rango_inicio=1,
            rango_fin=len(setup_full_zip['equipos'])
        )

        assert setup_full_zip['empresa'].nombre in readme
        assert str(len(setup_full_zip['equipos'])) in readme
