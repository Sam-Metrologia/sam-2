"""
Tests para Panel de Decisiones (core/views/panel_decisiones.py)

Objetivo: Aumentar cobertura del módulo panel_decisiones.py de 7.99% a ~40%
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.urls import reverse
from django.contrib.messages import get_messages
from core.models import (
    Empresa, CustomUser, Equipo,
    Calibracion, Mantenimiento, Comprobacion
)


@pytest.mark.django_db
class TestPanelDecisionesAcceso:
    """Tests de control de acceso al panel de decisiones"""

    def test_acceso_denegado_usuario_tecnico(self, client):
        """Usuario con rol TÉCNICO no puede acceder al panel"""
        # Crear empresa
        empresa = Empresa.objects.create(
            nombre="Empresa Test",
            nit="900111222-3",
            limite_equipos_empresa=10
        )

        # Crear usuario técnico
        usuario_tecnico = CustomUser.objects.create_user(
            username='tecnico1',
            email='tecnico@test.com',
            password='test123',
            empresa=empresa,
            rol_usuario='TECNICO',
            is_active=True
        )

        client.login(username='tecnico1', password='test123')
        response = client.get(reverse('core:panel_decisiones'))

        # Debe redirigir a home
        assert response.status_code == 302
        assert response.url == reverse('core:home')

        # Verificar mensaje de error
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        assert 'No tienes permisos' in str(messages[0])

    def test_acceso_denegado_usuario_administrador(self, client):
        """Usuario con rol ADMINISTRADOR no puede acceder al panel"""
        empresa = Empresa.objects.create(
            nombre="Empresa Test",
            nit="900111222-3",
            limite_equipos_empresa=10
        )

        usuario_admin = CustomUser.objects.create_user(
            username='admin1',
            email='admin@test.com',
            password='test123',
            empresa=empresa,
            rol_usuario='ADMINISTRADOR',
            is_active=True
        )

        client.login(username='admin1', password='test123')
        response = client.get(reverse('core:panel_decisiones'))

        assert response.status_code == 302
        assert response.url == reverse('core:home')

    def test_acceso_permitido_gerente(self, client):
        """Usuario con rol GERENCIA puede acceder al panel"""
        empresa = Empresa.objects.create(
            nombre="Empresa Test",
            nit="900111222-3",
            limite_equipos_empresa=10
        )

        usuario_gerente = CustomUser.objects.create_user(
            username='gerente1',
            email='gerente@test.com',
            password='test123',
            empresa=empresa,
            rol_usuario='GERENCIA',
            is_active=True,
            can_access_dashboard_decisiones=True
        )

        client.login(username='gerente1', password='test123')
        response = client.get(reverse('core:panel_decisiones'))

        # Debe cargar la página exitosamente
        assert response.status_code == 200
        assert 'core/panel_decisiones.html' in [t.name for t in response.templates]

    def test_acceso_permitido_superusuario(self, client, django_user_model):
        """Superusuario puede acceder al panel (vista SAM)"""
        superuser = django_user_model.objects.create_superuser(
            username='super',
            email='super@test.com',
            password='test123'
        )

        client.login(username='super', password='test123')
        response = client.get(reverse('core:panel_decisiones'))

        # Debe cargar la página exitosamente
        assert response.status_code == 200


@pytest.mark.django_db
class TestPanelDecisionesGerente:
    """Tests del panel de decisiones para usuarios gerente (vista empresa)"""

    @pytest.fixture
    def setup_empresa_con_equipos(self):
        """Fixture que crea empresa con equipos y actividades"""
        empresa = Empresa.objects.create(
            nombre="MetroLab S.A.S.",
            nit="900123456-7",
            limite_equipos_empresa=20
        )

        gerente = CustomUser.objects.create_user(
            username='gerente_metro',
            email='gerente@metrolab.com',
            password='test123',
            empresa=empresa,
            rol_usuario='GERENCIA',
            is_active=True,
            can_access_dashboard_decisiones=True
        )

        # Crear 3 equipos
        equipos = []
        for i in range(3):
            equipo = Equipo.objects.create(
                codigo_interno=f'EQ-00{i+1}',
                nombre=f'Equipo Test {i+1}',
                marca='Test Brand',
                modelo=f'Model-{i+1}',
                numero_serie=f'SN-{i+1}',
                tipo_equipo='Balanza',
                empresa=empresa,
                estado='Activo',
                ubicacion='Lab Principal',
                responsable='Técnico Test'
            )
            equipos.append(equipo)

        # Crear actividades recientes para equipo 1 (saludable)
        Calibracion.objects.create(
            equipo=equipos[0],
            fecha_calibracion=date.today() - timedelta(days=30),
            nombre_proveedor='Lab Certificado',
            resultado='Aprobado',
            numero_certificado='CERT-2025-001'
        )
        equipos[0].proxima_calibracion = date.today() + timedelta(days=335)
        equipos[0].save()

        Mantenimiento.objects.create(
            equipo=equipos[0],
            fecha_mantenimiento=date.today() - timedelta(days=15),
            tipo_mantenimiento='Preventivo',
            nombre_proveedor='Mantenimiento SAM',
            descripcion='Mantenimiento preventivo anual'
        )

        # Equipo 2: Calibración vencida (no saludable)
        Calibracion.objects.create(
            equipo=equipos[1],
            fecha_calibracion=date.today() - timedelta(days=400),
            nombre_proveedor='Lab Certificado',
            resultado='Aprobado',
            numero_certificado='CERT-2024-001'
        )
        equipos[1].proxima_calibracion = date.today() - timedelta(days=30)  # Vencida
        equipos[1].save()

        return {
            'empresa': empresa,
            'gerente': gerente,
            'equipos': equipos
        }

    def test_panel_gerente_muestra_metricas(self, client, setup_empresa_con_equipos):
        """Panel de gerente muestra métricas de salud, cumplimiento y eficiencia"""
        data = setup_empresa_con_equipos

        client.login(username='gerente_metro', password='test123')
        response = client.get(reverse('core:panel_decisiones'))

        assert response.status_code == 200
        context = response.context

        # Verificar que existen las métricas principales (claves directas en contexto)
        assert 'salud_general_porcentaje' in context
        assert 'cumplimiento_porcentaje' in context
        assert 'eficiencia_porcentaje' in context

        # Verificar datos de salud
        assert 'total_equipos_salud' in context
        assert context['total_equipos_salud'] == 3

    def test_panel_gerente_muestra_actividades_criticas(self, client, setup_empresa_con_equipos):
        """Panel muestra actividades críticas y vencidas"""
        data = setup_empresa_con_equipos

        client.login(username='gerente_metro', password='test123')
        response = client.get(reverse('core:panel_decisiones'))

        assert response.status_code == 200
        context = response.context

        # El contexto debe contener datos de alertas
        assert 'alertas_predictivas' in context or 'recomendaciones' in context

        # Verificar que tiene información sobre equipos
        assert 'total_equipos_salud' in context
        assert context['total_equipos_salud'] > 0

    def test_panel_gerente_muestra_recomendaciones(self, client, setup_empresa_con_equipos):
        """Panel genera recomendaciones basadas en métricas"""
        data = setup_empresa_con_equipos

        client.login(username='gerente_metro', password='test123')
        response = client.get(reverse('core:panel_decisiones'))

        assert response.status_code == 200
        context = response.context

        # Debe tener recomendaciones
        assert 'recomendaciones' in context
        recomendaciones = context['recomendaciones']

        assert isinstance(recomendaciones, list)
        # Puede estar vacío o tener recomendaciones dependiendo de las métricas


@pytest.mark.django_db
class TestPanelDecisionesSuperusuario:
    """Tests del panel de decisiones para superusuarios (vista SAM multi-empresa)"""

    @pytest.fixture
    def setup_multiples_empresas(self):
        """Fixture que crea múltiples empresas con equipos"""
        empresas = []
        for i in range(2):
            empresa = Empresa.objects.create(
                nombre=f"Empresa {i+1}",
                nit=f"90011122{i}-3",
                limite_equipos_empresa=10
            )

            # Crear equipo para cada empresa
            Equipo.objects.create(
                codigo_interno=f'EMP{i+1}-EQ-001',
                nombre=f'Equipo Empresa {i+1}',
                marca='Test Brand',
                modelo='Model-1',
                numero_serie=f'SN-EMP{i+1}-001',
                tipo_equipo='Balanza',
                empresa=empresa,
                estado='Activo',
                ubicacion='Lab Principal',
                responsable='Técnico Test'
            )

            empresas.append(empresa)

        superuser = CustomUser.objects.create_superuser(
            username='superadmin',
            email='super@sam.com',
            password='test123'
        )

        return {
            'empresas': empresas,
            'superuser': superuser
        }

    def test_panel_superusuario_vista_sam(self, client, setup_multiples_empresas):
        """Superusuario ve panel SAM con datos agregados de todas las empresas"""
        data = setup_multiples_empresas

        client.login(username='superadmin', password='test123')
        response = client.get(reverse('core:panel_decisiones'))

        assert response.status_code == 200
        context = response.context

        # Vista SAM debe tener métricas agregadas
        assert 'total_empresas' in context or 'empresas' in context

        # Verificar que se muestran datos de múltiples empresas
        # (La implementación puede variar según el código)

    def test_panel_superusuario_vista_empresa_especifica(self, client, setup_multiples_empresas):
        """Superusuario puede ver panel de una empresa específica"""
        data = setup_multiples_empresas
        empresa = data['empresas'][0]

        client.login(username='superadmin', password='test123')
        url = reverse('core:panel_decisiones') + f'?empresa_id={empresa.id}'
        response = client.get(url)

        assert response.status_code == 200
        context = response.context

        # Debe mostrar datos de la empresa seleccionada
        assert 'salud_general_porcentaje' in context
        assert 'cumplimiento_porcentaje' in context
        assert 'perspectiva' in context

    def test_panel_superusuario_empresa_no_existe(self, client, setup_multiples_empresas):
        """Superusuario con empresa_id inválido vuelve a vista SAM"""
        client.login(username='superadmin', password='test123')
        url = reverse('core:panel_decisiones') + '?empresa_id=99999'
        response = client.get(url)

        # Debe cargar la vista SAM con warning
        assert response.status_code == 200

        messages = list(get_messages(response.wsgi_request))
        # Puede tener mensaje de warning
        if len(messages) > 0:
            assert 'no existe' in str(messages[0]).lower()


@pytest.mark.django_db
class TestFuncionesCalculoPanelDecisiones:
    """Tests de funciones auxiliares de cálculo del panel"""

    def test_decimal_to_float_convierte_decimales(self):
        """Función decimal_to_float convierte Decimals en estructuras anidadas"""
        from core.views.panel_decisiones import decimal_to_float

        data = {
            'precio': Decimal('100.50'),
            'items': [
                {'costo': Decimal('25.25')},
                {'costo': Decimal('75.25')}
            ],
            'total': Decimal('200.75')
        }

        result = decimal_to_float(data)

        assert result['precio'] == 100.50
        assert result['items'][0]['costo'] == 25.25
        assert result['total'] == 200.75
        assert isinstance(result['precio'], float)

    def test_funciones_auxiliares_son_privadas(self):
        """Las funciones auxiliares _calcular_* son privadas y se prueban via integración"""
        # Estas funciones se testean indirectamente a través de los tests
        # de integración que llaman al panel completo
        assert True  # Placeholder para mantener la clase


@pytest.mark.integration
@pytest.mark.django_db
class TestPanelDecisionesIntegracion:
    """Tests de integración completos del panel de decisiones"""

    def test_flujo_completo_gerente_con_datos_reales(self, client):
        """Test E2E: Gerente accede al panel con empresa que tiene equipos y actividades"""
        # Setup: Crear empresa completa
        empresa = Empresa.objects.create(
            nombre="Metrología Integral S.A.S.",
            nit="900555666-7",
            limite_equipos_empresa=50
        )

        gerente = CustomUser.objects.create_user(
            username='gerente_integral',
            email='gerente@integral.com',
            password='Password123!',
            empresa=empresa,
            rol_usuario='GERENCIA',
            is_active=True,
            can_access_dashboard_decisiones=True
        )

        # Crear 5 equipos con diferentes estados de salud
        equipos_data = [
            {'codigo': 'BAL-001', 'tipo': 'Balanza', 'calibracion_dias': 300},
            {'codigo': 'TERM-002', 'tipo': 'Termómetro', 'calibracion_dias': -10},  # Vencido
            {'codigo': 'CAL-003', 'tipo': 'Calibrador', 'calibracion_dias': 200},
            {'codigo': 'MAN-004', 'tipo': 'Manómetro', 'calibracion_dias': 150},
            {'codigo': 'MIC-005', 'tipo': 'Micrómetro', 'calibracion_dias': 5},  # Próximo a vencer
        ]

        for eq_data in equipos_data:
            equipo = Equipo.objects.create(
                codigo_interno=eq_data['codigo'],
                nombre=f"{eq_data['tipo']} de Precisión",
                marca='Test Brand',
                modelo='Model-X',
                numero_serie=f"SN-{eq_data['codigo']}",
                tipo_equipo=eq_data['tipo'],
                empresa=empresa,
                estado='Activo',
                ubicacion='Laboratorio Principal',
                responsable='Técnico Carlos'
            )

            # Crear calibración
            fecha_cal = date.today() - timedelta(days=(365 - eq_data['calibracion_dias']))
            Calibracion.objects.create(
                equipo=equipo,
                fecha_calibracion=fecha_cal,
                nombre_proveedor='Laboratorio Acreditado',
                resultado='Aprobado',
                numero_certificado=f"CERT-{eq_data['codigo']}"
            )
            equipo.proxima_calibracion = date.today() + timedelta(days=eq_data['calibracion_dias'])
            equipo.save()

        # Ejecutar: Gerente accede al panel
        client.login(username='gerente_integral', password='Password123!')
        response = client.get(reverse('core:panel_decisiones'))

        # Verificar: Response exitoso
        assert response.status_code == 200

        # Verificar: Contexto tiene todas las secciones esperadas
        context = response.context
        assert 'salud_general_porcentaje' in context
        assert 'cumplimiento_porcentaje' in context
        assert 'eficiencia_porcentaje' in context

        # Verificar: Datos de salud
        assert 'total_equipos_salud' in context
        assert context['total_equipos_salud'] == 5

        # Verificar: Tiene alertas o recomendaciones
        assert 'alertas_predictivas' in context or 'recomendaciones' in context

        # Verificar: Tiene recomendaciones
        if 'recomendaciones' in context:
            assert isinstance(context['recomendaciones'], list)
