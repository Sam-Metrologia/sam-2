"""
Tests del grupo matriz + sedes: volver a la matriz, contadores y filtros del listado,
todas las sedes juntas y el Excel único de equipos.
"""
import io
from datetime import date, timedelta

import openpyxl
import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.urls import reverse

from core import busqueda_equipos as be
from core.models import Calibracion, Equipo
from core.tenancy import SESSION_KEY_EMPRESA_ACTIVA, get_empresa_activa
from tests.factories import EmpresaFactory, EquipoFactory, UserFactory


@pytest.fixture
def grupo():
    matriz = EmpresaFactory(nombre='MATRIZ', limite_equipos_empresa=100)
    sede = EmpresaFactory(nombre='SEDE', empresa_matriz=matriz, limite_equipos_empresa=100)
    return matriz, sede


def _gerente(empresa):
    return UserFactory(empresa=empresa, rol_usuario='GERENCIA')


def _super(empresa=None):
    return UserFactory(empresa=empresa, is_superuser=True, is_staff=True)


def _cambiar(client, empresa_id, **extra):
    return client.post(reverse('core:cambiar_sede'), {'empresa_id': empresa_id, **extra})


def _mensajes(response):
    return [str(m) for m in response.context['messages']]


@pytest.fixture
def datos(grupo):
    matriz, sede = grupo
    for empresa, codigo, nombre, estado in [
            (matriz, 'M1', 'Cinta métrica', 'Activo'), (matriz, 'M2', 'Manómetro', 'Activo'),
            (sede, 'S1', 'Cinta Metrica', 'Activo'), (sede, 'S2', 'Cinta métrica', 'De Baja'),
            (EmpresaFactory(nombre='AJENA'), 'X1', 'Cinta métrica', 'Activo')]:
        EquipoFactory(empresa=empresa, codigo_interno=codigo, nombre=nombre, estado=estado)
    return matriz, sede


def _con_permiso(user, *codenames):
    user.user_permissions.add(*Permission.objects.filter(codename__in=('view_equipo',) + codenames))
    return user


def _excel(client, **params):
    r = client.get(reverse('core:exportar_equipos_excel'), params)
    assert r.status_code == 200, getattr(r, 'url', r.status_code)
    return openpyxl.load_workbook(io.BytesIO(r.content))


def _codigos_excel(libro):
    return {f[0] for f in libro['Equipos'].iter_rows(min_row=6, values_only=True) if f[0]}


@pytest.mark.django_db
class TestExcelUnico:
    @pytest.mark.parametrize('params', [
        lambda ajena: {'empresa_id': ajena}, lambda ajena: {'sede': ajena},
        lambda ajena: {'empresa_id': f'grupo-{ajena}'}, lambda ajena: {'empresa_id': ''}])
    def test_no_descarga_otra_empresa(self, client, datos, params):
        matriz, sede = datos
        ajena = Equipo.objects.get(codigo_interno='X1').empresa_id
        client.force_login(_con_permiso(_gerente(matriz)))
        assert _codigos_excel(_excel(client, **params(ajena))) == {'M1', 'M2'}

    def test_el_excel_dashboard_inseguro_ya_no_existe(self, client, datos):
        client.force_login(_con_permiso(_gerente(datos[0]), 'can_export_reports'))
        assert client.get('/core/informes/dashboard_excel/', {'empresa_id': datos[1].id}).status_code == 404

    def test_esta_sede_o_todas_las_sedes(self, client, datos):
        matriz, sede = datos
        client.force_login(_con_permiso(_gerente(matriz)))
        assert _codigos_excel(_excel(client)) == {'M1', 'M2'}
        assert _codigos_excel(_excel(client, sede=sede.id)) == {'S1', 'S2'}
        libro = _excel(client, sede='todas')
        assert _codigos_excel(libro) == {'M1', 'M2', 'S1', 'S2'}
        filas = [f[:5] for f in libro['Resumen'].iter_rows(min_row=6, values_only=True)]
        assert filas[:3] == [('MATRIZ', 2, 0, 0, 2), ('SEDE', 1, 0, 1, 2), ('TOTAL', 3, 0, 1, 4)]
        conteo = {f[0]: f[1:5] for f in libro['Conteo por nombre'].iter_rows(min_row=6, values_only=True)}
        assert (2, 0, 1, 3) in conteo.values() and len(conteo) == 2

    def test_formato_de_la_matriz_en_el_grupo_y_de_la_sede_sola(self, client, datos):
        matriz, sede = datos
        for empresa, codigo in ((matriz, 'COD-MATRIZ'), (sede, 'COD-SEDE')):
            empresa.listado_codigo = codigo
            empresa.save()
        client.force_login(_con_permiso(_gerente(matriz)))
        assert 'COD-MATRIZ' in _excel(client, sede='todas')['Equipos']['A3'].value
        assert 'COD-SEDE' in _excel(client, sede=sede.id)['Equipos']['A3'].value

    @pytest.mark.parametrize('rol,indice', [('ADMINISTRADOR', 0), ('GERENCIA', 1)])
    def test_todas_no_sirve_sin_ser_gerente_de_la_matriz(self, client, datos, rol, indice):
        user = _con_permiso(UserFactory(empresa=datos[indice], rol_usuario=rol))
        client.force_login(user)
        assert _codigos_excel(_excel(client, sede='todas')) == [{'M1', 'M2'}, {'S1', 'S2'}][indice]

    def test_superusuario_una_empresa_un_grupo_o_todas(self, client, datos):
        matriz, sede = datos
        client.force_login(_super())
        assert _codigos_excel(_excel(client, empresa_id=sede.id)) == {'S1', 'S2'}
        assert _codigos_excel(_excel(client, empresa_id=f'grupo-{matriz.id}')) == {'M1', 'M2', 'S1', 'S2'}
        assert _codigos_excel(_excel(client)) == {'M1', 'M2', 'S1', 'S2', 'X1'}
        for malo in ('999999', 'grupo-999999', 'abc'):
            assert client.get(reverse('core:exportar_equipos_excel'), {'empresa_id': malo}).status_code == 302

    def test_prestamos_solo_con_permiso(self, client, datos):
        matriz, _ = datos
        sin_permiso = _gerente(matriz)
        sin_permiso.user_permissions.clear()  # el rol trae can_view_prestamo
        sin_permiso.groups.clear()
        client.force_login(_con_permiso(sin_permiso))
        hojas = _excel(client).sheetnames
        assert hojas == ['Resumen', 'Conteo por nombre', 'Equipos', 'Proveedores', 'Procedimientos', 'Dashboard']
        client.force_login(_con_permiso(_gerente(matriz), 'can_view_prestamo'))
        assert 'Préstamos' in _excel(client).sheetnames

    def test_textos_peligrosos_no_rompen_ni_ejecutan(self, client, grupo):
        matriz, _ = grupo
        EquipoFactory(empresa=matriz, codigo_interno='F1', nombre='=1+1', observaciones='a\x0bb')
        client.force_login(_con_permiso(_gerente(matriz)))
        celda = _excel(client)['Equipos']['B6']
        assert celda.value == '=1+1' and celda.data_type == 's'

    def test_ultimo_certificado_y_mas_de_20_equipos(self, client, grupo):
        matriz, _ = grupo
        equipos = [EquipoFactory(empresa=matriz, codigo_interno=f'E{i:02d}') for i in range(25)]
        for dias, numero in ((400, 'VIEJO'), (10, 'NUEVO')):
            Calibracion.objects.create(equipo=equipos[0], numero_certificado=numero,
                                       fecha_calibracion=date.today() - timedelta(days=dias))
        client.force_login(_con_permiso(_gerente(matriz)))
        libro = _excel(client)
        assert len(_codigos_excel(libro)) == 25
        fila = next(f for f in libro['Equipos'].iter_rows(min_row=6, values_only=True) if f[0] == 'E00')
        assert fila[17] == 'NUEVO'

    def test_no_hace_una_consulta_por_equipo(self, client, grupo, django_assert_max_num_queries):
        matriz, _ = grupo
        for i in range(40):
            EquipoFactory(empresa=matriz, codigo_interno=f'Q{i}')
        from core.excel_equipos import excel_de_empresas
        with django_assert_max_num_queries(12):
            excel_de_empresas([matriz], con_prestamos=True)

    def test_el_zip_lleva_el_mismo_excel(self, grupo):
        from core.models import Procedimiento, Proveedor
        from core.views.reports import _generate_consolidated_excel_content
        matriz, _ = grupo
        for hay_equipos in (False, True):
            if hay_equipos:
                EquipoFactory(empresa=matriz)
            libro = openpyxl.load_workbook(io.BytesIO(_generate_consolidated_excel_content(
                Equipo.objects.filter(empresa=matriz), Proveedor.objects.all(), Procedimiento.objects.all())))
            assert libro.sheetnames[:3] == ['Resumen', 'Conteo por nombre', 'Equipos']

    def test_informes_ofrece_las_opciones_segun_el_usuario(self, client, datos):
        matriz, sede = datos

        def contexto(user, **params):
            client.force_login(user)
            r = client.get(reverse('core:informes'), params)
            assert 'Dashboard Excel Completo' not in r.content.decode()
            return r.context
        c = contexto(_gerente(matriz))
        assert c['sedes_excel'] == [matriz, sede] and c['sedes_excel_marcadas'] == [matriz.id]
        c = contexto(_gerente(sede))
        assert c['sedes_excel'] == [] and c['opciones_excel'] == []
        c = contexto(_super())
        assert [v for v, _ in c['opciones_excel']] == ['', f'grupo-{matriz.id}']
        assert c['grupos_excel'][0]['sedes'] == [matriz, sede]
        c = contexto(_super(), empresa_id=sede.id)
        assert [v for v, _ in c['opciones_excel']] == [str(sede.id), f'grupo-{matriz.id}']


@pytest.mark.django_db
class TestVolverAMatriz:
    def test_dashboard_no_muestra_datos_de_la_sede_anterior(self, client, grupo, settings):
        settings.CACHES = {'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'grupo-sedes'}}
        matriz, sede = grupo
        for i in range(3):
            EquipoFactory(empresa=matriz, codigo_interno=f'M{i}')
        for i in range(5):
            EquipoFactory(empresa=sede, codigo_interno=f'S{i}')
        cache.clear()  # las dos empresas quedan en la misma versión de caché
        client.force_login(_gerente(matriz))
        _cambiar(client, sede.id)
        assert client.get(reverse('core:dashboard')).context['total_equipos'] == 5
        _cambiar(client, matriz.id)
        assert client.get(reverse('core:dashboard')).context['total_equipos'] == 3
        cache.clear()

    def test_boton_volver_solo_aparece_estando_en_una_sede(self, client, grupo):
        matriz, sede = grupo
        client.force_login(_gerente(matriz))
        assert 'Volver a matriz' not in client.get(reverse('core:home')).content.decode()
        _cambiar(client, sede.id)
        assert 'Volver a matriz' in client.get(reverse('core:home')).content.decode()

    def test_desde_el_detalle_de_un_equipo_va_al_panel(self, client, grupo):
        matriz, sede = grupo
        equipo = EquipoFactory(empresa=sede)
        client.force_login(_gerente(matriz))
        _cambiar(client, sede.id)
        r = _cambiar(client, matriz.id, next=reverse('core:detalle_equipo', args=[equipo.pk]))
        assert r.url == reverse('core:dashboard')

    def test_superusuario_puede_ir_a_la_sede_volver_y_ver_todas(self, client, grupo):
        matriz, sede = grupo
        EquipoFactory(empresa=matriz, codigo_interno='EN-MATRIZ')
        EquipoFactory(empresa=sede, codigo_interno='EN-SEDE')
        EquipoFactory(empresa=EmpresaFactory(), codigo_interno='EN-OTRA')
        client.force_login(_super(matriz))

        def codigos(**params):
            return {e.codigo_interno for e in client.get(reverse('core:home'), params).context['equipos']}

        assert codigos() == {'EN-MATRIZ', 'EN-SEDE', 'EN-OTRA'}
        _cambiar(client, sede.id)
        assert codigos() == {'EN-SEDE'}
        assert codigos(empresa_id='') == {'EN-MATRIZ', 'EN-SEDE', 'EN-OTRA'}
        assert client.get(reverse('core:dashboard')).context['total_equipos'] == 1
        assert client.get(reverse('core:informes')).context['selected_company_id'] == str(sede.id)
        assert client.get(reverse('core:panel_decisiones')).status_code == 200
        _cambiar(client, matriz.id)
        assert codigos() == {'EN-MATRIZ'}
        _cambiar(client, 'todas')
        assert codigos() == {'EN-MATRIZ', 'EN-SEDE', 'EN-OTRA'}

    def test_todas_no_sirve_para_un_usuario_normal(self, client, grupo):
        matriz, sede = grupo
        client.force_login(_gerente(matriz))
        _cambiar(client, sede.id)
        _cambiar(client, 'todas')
        assert client.session[SESSION_KEY_EMPRESA_ACTIVA] == sede.id

    def test_superusuario_ignora_en_sesion_una_empresa_fuera_de_su_grupo(self, grupo):
        matriz, _ = grupo

        class Peticion:
            user = _super(matriz)
            session = {SESSION_KEY_EMPRESA_ACTIVA: EmpresaFactory().id}
        assert get_empresa_activa(Peticion()) == matriz


@pytest.mark.django_db
class TestTransferirDeVuelta:
    @pytest.mark.parametrize('superusuario', [True, False])
    def test_devolver_equipo_a_la_matriz_eligiendo_origen(self, client, grupo, superusuario):
        matriz, sede = grupo
        equipo = EquipoFactory(empresa=sede)
        client.force_login(_super() if superusuario else _gerente(matriz))
        r = client.get(reverse('core:transferir_equipos'), {'origen': sede.id})
        assert r.context['empresa_origen'] == sede and equipo in r.context['equipos']
        client.post(reverse('core:transferir_equipos'), {
            'empresa_origen': sede.id, 'empresa_destino': matriz.id, 'equipos': [equipo.pk]})
        equipo.refresh_from_db()
        assert equipo.empresa_id == matriz.id

    def test_superusuario_no_mueve_entre_clientes_distintos(self, client, grupo):
        matriz, _ = grupo
        otra = EmpresaFactory()
        EmpresaFactory(empresa_matriz=otra)
        equipo = EquipoFactory(empresa=matriz)
        client.force_login(_super())
        client.post(reverse('core:transferir_equipos'), {
            'empresa_origen': matriz.id, 'empresa_destino': otra.id, 'equipos': [equipo.pk]})
        equipo.refresh_from_db()
        assert equipo.empresa_id == matriz.id

    def test_gerente_no_puede_usar_un_origen_ajeno(self, client, grupo):
        matriz, sede = grupo
        ajeno = EquipoFactory(empresa=EmpresaFactory())
        client.force_login(_gerente(matriz))
        client.post(reverse('core:transferir_equipos'), {
            'empresa_origen': ajeno.empresa_id, 'empresa_destino': sede.id, 'equipos': [ajeno.pk]})
        empresa_antes = ajeno.empresa_id
        ajeno.refresh_from_db()
        assert ajeno.empresa_id == empresa_antes

    def test_la_sede_de_origen_queda_recalculada(self, client, grupo):
        matriz, sede = grupo
        equipos = [EquipoFactory(empresa=matriz) for _ in range(2)]
        client.force_login(_gerente(matriz))
        client.post(reverse('core:transferir_equipos'), {
            'empresa_destino': sede.id, 'equipos': [equipos[0].pk]})
        matriz.refresh_from_db()
        sede.refresh_from_db()
        assert (matriz.stats_total_equipos, sede.stats_total_equipos) == (1, 1)


@pytest.mark.django_db
class TestBusquedaYConteo:
    def test_sin_tildes_mayusculas_ni_plurales(self):
        empresa = EmpresaFactory()
        for i, nombre in enumerate(['Cinta Métrica', 'CINTA METRICA', 'cinta  métrica 5 m', 'Manómetro']):
            EquipoFactory(empresa=empresa, nombre=nombre, codigo_interno=f'C{i}', numero_serie=f'S{i}',
                          marca='X', modelo='Y', ubicacion='Z', responsable='W')
        for texto in ('cinta metrica', 'Cinta Métrica', 'cintas métricas', 'CINTAS METRICAS'):
            assert be.filtrar_por_texto(Equipo.objects.all(), texto).count() == 3, texto
        assert be.filtrar_por_texto(Equipo.objects.all(), 'manometros').count() == 1
        assert be.filtrar_por_texto(Equipo.objects.all(), 'no existe').count() == 0

    def test_las_palabras_deben_estar_en_el_mismo_campo(self):
        EquipoFactory(nombre='Cinta métrica', numero_serie='555', codigo_interno='A', marca='X',
                      modelo='Y', ubicacion='Z', responsable='W')
        assert be.filtrar_por_texto(Equipo.objects.all(), 'cinta 5').count() == 0

    def test_agrupa_el_mismo_nombre_escrito_distinto(self):
        empresa = EmpresaFactory()
        for i, (nombre, estado) in enumerate([
                ('Cinta Métrica', 'Activo'), ('cinta metrica', 'En Calibración'),
                ('CINTA MÉTRICA', 'Inactivo'), ('Cinta Métrica', 'De Baja')]):
            EquipoFactory(empresa=empresa, nombre=nombre, estado=estado, codigo_interno=f'C{i}')
        c = be.contar(Equipo.objects.filter(empresa=empresa))
        esperado = {'activos': 2, 'inactivos': 1, 'de_baja': 1, 'total': 4}
        assert c['total'] == esperado and c['por_empresa'][empresa.id] == esperado
        assert len(c['por_nombre']) == 1 and c['por_nombre'][0]['total'] == 4


@pytest.mark.django_db
class TestFiltroEstadoListado:
    @pytest.fixture
    def entrar(self, client):
        empresa = EmpresaFactory()
        for codigo, estado in [('ACT', 'Activo'), ('CAL', 'En Calibración'), ('INA', 'Inactivo'), ('BAJ', 'De Baja')]:
            EquipoFactory(empresa=empresa, codigo_interno=codigo, estado=estado)

        def _entrar(superusuario=False):
            client.force_login(_super() if superusuario else _gerente(empresa))
            extra = {'empresa_id': empresa.id} if superusuario else {}
            return lambda **p: client.get(reverse('core:home'), {**extra, **p})
        return _entrar

    @pytest.mark.parametrize('superusuario', [True, False])
    @pytest.mark.parametrize('estado,esperados', [
        (None, {'ACT', 'CAL'}), ('', {'ACT', 'CAL'}), ('activos', {'ACT', 'CAL'}),
        ('inventado', {'ACT', 'CAL'}), ('todos', {'ACT', 'CAL', 'INA', 'BAJ'}),
        ('Inactivo', {'INA'}), ('De Baja', {'BAJ'}), ('En Calibración', {'CAL'}),
    ])
    def test_filtro(self, entrar, superusuario, estado, esperados):
        r = entrar(superusuario)(**({} if estado is None else {'estado': estado}))
        assert {e.codigo_interno for e in r.context['equipos']} == esperados
        assert r.context['conteo'] == {'activos': 2, 'inactivos': 1, 'de_baja': 1, 'total': 4}

    def test_los_enlaces_conservan_los_filtros(self, entrar):
        html = entrar()(estado='todos', orden='calibracion', tipo_equipo='').content.decode()
        assert 'estado=todos&amp;' in html and 'orden=mantenimiento' in html

    def test_el_texto_buscado_no_inyecta_html(self, entrar):
        html = entrar()(q='"><script>alert(1)</script>').content.decode()
        assert '<script>alert(1)</script>' not in html


@pytest.mark.django_db
class TestTodasLasSedesEnElListado:
    def _ver(self, client, **params):
        r = client.get(reverse('core:home'), params)
        return r, {e.codigo_interno for e in r.context['equipos']}

    def test_todas_las_sedes_sin_incluir_ajenas(self, client, datos):
        matriz, sede = datos
        client.force_login(_gerente(matriz))
        r, codigos = self._ver(client, sede='todas')
        assert codigos == {'M1', 'M2', 'S1'}
        assert r.context['conteo'] == {'activos': 3, 'inactivos': 0, 'de_baja': 1, 'total': 4}
        assert [(f['empresa'].nombre, f['total']) for f in r.context['resumen_sedes']] == [('MATRIZ', 2), ('SEDE', 2)]

    def test_por_defecto_solo_la_sede_activa(self, client, datos):
        client.force_login(_gerente(datos[0]))
        r, codigos = self._ver(client)
        assert codigos == {'M1', 'M2'} and r.context['resumen_sedes'] == []

    def test_cuantas_cintas_hay(self, client, datos):
        client.force_login(_gerente(datos[0]))
        r, codigos = self._ver(client, sede='todas', q='cintas metricas', estado='todos')
        assert codigos == {'M1', 'S1', 'S2'}
        assert [f['total'] for f in r.context['resumen_sedes']] == [1, 2]

    def test_equipos_de_otra_sede_son_solo_consulta(self, client, datos):
        matriz, sede = datos
        client.force_login(_gerente(matriz))
        s1, m1 = (Equipo.objects.get(codigo_interno=c) for c in ('S1', 'M1'))
        html = self._ver(client, sede='todas')[0].content.decode()
        assert reverse('core:editar_equipo', args=[m1.pk]) in html
        assert reverse('core:editar_equipo', args=[s1.pk]) not in html
        assert 'Solo consulta' in html

    @pytest.mark.parametrize('rol,indice', [('TECNICO', 0), ('ADMINISTRADOR', 0), ('GERENCIA', 1)])
    def test_sin_acceso_al_grupo_ve_solo_lo_suyo(self, client, datos, rol, indice):
        client.force_login(UserFactory(empresa=datos[indice], rol_usuario=rol))
        for pedido in ('todas', datos[1 - indice].id):
            r, codigos = self._ver(client, sede=pedido, estado='todos')
            assert codigos == [{'M1', 'M2'}, {'S1', 'S2'}][indice]
            assert 'name="sede"' not in r.content.decode()

    def test_sede_ajena_en_la_url_se_ignora(self, client, datos):
        client.force_login(_gerente(datos[0]))
        ajena = Equipo.objects.get(codigo_interno='X1').empresa_id
        assert self._ver(client, sede=ajena)[1] == {'M1', 'M2'}

    def test_superusuario_ve_un_grupo_completo(self, client, datos):
        matriz, _ = datos
        client.force_login(_super())
        r, codigos = self._ver(client, empresa_id=f'grupo-{matriz.id}')
        assert codigos == {'M1', 'M2', 'S1'} and len(r.context['resumen_sedes']) == 2
        assert f'value="grupo-{matriz.id}" selected' in r.content.decode()
        for malo in ('grupo-999999', 'abc', '999999'):
            assert self._ver(client, empresa_id=malo)[1] == set()

    def test_el_resumen_llega_cerrado(self, client, datos):
        client.force_login(_gerente(datos[0]))
        html = self._ver(client)[0].content.decode()
        assert '<details class="resumen-equipos" id="contador-equipos">' in html


@pytest.mark.django_db
class TestDashboardCuentaIgualQueElListado:
    @pytest.mark.parametrize('precalculado', [True, False])
    @pytest.mark.parametrize('superusuario', [True, False])
    def test_activos_iguales(self, client, precalculado, superusuario):
        empresa = EmpresaFactory()
        for codigo, estado in [('A', 'Activo'), ('B', 'En Calibración'), ('C', 'En Mantenimiento'),
                               ('D', 'Inactivo'), ('E', 'De Baja')]:
            EquipoFactory(empresa=empresa, codigo_interno=codigo, estado=estado)
        empresa.refresh_from_db()
        empresa.stats_fecha_calculo = date.today() if precalculado else None
        empresa.save(update_fields=['stats_fecha_calculo'])
        cache.clear()
        client.force_login(_super() if superusuario else _gerente(empresa))
        params = {'empresa_id': empresa.id} if superusuario else {}
        panel = client.get(reverse('core:dashboard'), params).context
        lista = client.get(reverse('core:home'), params).context['conteo']
        assert (panel['equipos_activos'], panel['equipos_inactivos'], panel['equipos_de_baja'],
                panel['total_equipos']) == (3, 1, 1, 5)
        assert lista == {'activos': 3, 'inactivos': 1, 'de_baja': 1, 'total': 5}

    def test_los_avisos_usan_una_clase_que_existe(self, client):
        """Antes salían como 'alert-alert-danger' (sin color)."""
        client.force_login(_super())
        html = client.get(reverse('core:home'), {'empresa_id': '999999'}).content.decode()
        assert 'class="alert alert-error ' in html and 'alert-alert-' not in html
        assert '--color-error: var(--color-error)' not in html


@pytest.mark.django_db
class TestElegirVariasSedes:
    @pytest.fixture
    def grupo5(self):
        matriz = EmpresaFactory(nombre='MATRIZ', listado_codigo='COD-MATRIZ')
        sedes = [EmpresaFactory(nombre=f'SEDE {i}', empresa_matriz=matriz, listado_codigo=f'COD-{i}')
                 for i in range(1, 6)]
        for i, empresa in enumerate([matriz] + sedes):
            EquipoFactory(empresa=empresa, codigo_interno=f'E{i}', nombre='Cinta')
        return matriz, sedes

    def _ver(self, client, **params):
        r = client.get(reverse('core:home'), params)
        return r, {e.codigo_interno for e in r.context['equipos']}

    def test_tres_de_cinco_sedes(self, client, grupo5):
        matriz, sedes = grupo5
        client.force_login(_gerente(matriz))
        r, codigos = self._ver(client, sede=[sedes[0].id, sedes[2].id, sedes[4].id])
        assert codigos == {'E1', 'E3', 'E5'}
        assert r.context['conteo']['total'] == 3
        assert [f['empresa'].nombre for f in r.context['resumen_sedes']] == ['SEDE 1', 'SEDE 3', 'SEDE 5']
        html = r.content.decode()
        assert 'en 3 de 6 sedes' in html and 'Total parcial (3 de 6 sedes)' in html
        assert 'resumen-etiqueta">Matriz' not in html  # la matriz no está entre las elegidas
        assert r.context['current_company_format_info'] == matriz

    def test_al_ordenar_o_filtrar_se_conservan_las_sedes(self, client, grupo5):
        matriz, sedes = grupo5
        client.force_login(_gerente(matriz))
        r, _ = self._ver(client, sede=[sedes[0].id, sedes[1].id])
        for clave in ('qs_sin_orden', 'qs_sin_estado', 'qs_sin_pagina'):
            assert f'sede={sedes[0].id}&sede={sedes[1].id}' in r.context[clave]

    def test_marcar_todas_equivale_al_grupo(self, client, grupo5):
        matriz, sedes = grupo5
        client.force_login(_gerente(matriz))
        html = self._ver(client, sede=[e.id for e in [matriz] + sedes])[0].content.decode()
        assert 'en todas las sedes' in html and 'Total parcial' not in html

    def test_una_sede_ajena_mezclada_se_ignora(self, client, grupo5):
        matriz, sedes = grupo5
        ajeno = EquipoFactory(empresa=EmpresaFactory(), codigo_interno='X')
        client.force_login(_con_permiso(_gerente(matriz)))
        params = {'sede': [sedes[0].id, sedes[1].id, ajeno.empresa_id]}
        assert self._ver(client, **params)[1] == {'E1', 'E2'}
        assert _codigos_excel(_excel(client, **params)) == {'E1', 'E2'}

    @pytest.mark.parametrize('rol', ['TECNICO', 'ADMINISTRADOR'])
    def test_sin_ser_gerente_de_la_matriz_no_aplica(self, client, grupo5, rol):
        matriz, sedes = grupo5
        client.force_login(UserFactory(empresa=matriz, rol_usuario=rol))
        assert self._ver(client, sede=[sedes[0].id, sedes[1].id])[1] == {'E0'}

    def test_excel_parcial_dice_que_sedes_incluye(self, client, grupo5):
        matriz, sedes = grupo5
        client.force_login(_con_permiso(_gerente(matriz)))
        params = {'sede': [sedes[0].id, sedes[2].id, sedes[4].id]}
        r = client.get(reverse('core:exportar_equipos_excel'), params)
        assert 'listado_equipos_3_sedes.xlsx' in r['Content-Disposition']
        libro = _excel(client, **params)
        assert _codigos_excel(libro) == {'E1', 'E3', 'E5'}
        hoja = libro['Equipos']
        assert 'COD-MATRIZ' in hoja['A3'].value
        assert hoja['A4'].value == 'LISTADO PARCIAL: 3 de 6 sedes — SEDE 1, SEDE 3, SEDE 5'
        assert hoja['A5'].value == 'Código Interno'
        totales = [f[0] for f in libro['Resumen'].iter_rows(min_row=6, values_only=True)]
        assert 'TOTAL PARCIAL (3 de 6 sedes)' in totales and 'TOTAL' not in totales

    def test_excel_completo_no_dice_parcial(self, client, grupo5):
        matriz, sedes = grupo5
        client.force_login(_con_permiso(_gerente(matriz)))
        hoja = _excel(client, sede='todas')['Equipos']
        assert 'matriz y 5 sedes' in hoja['A2'].value and hoja['A4'].value is None

    def test_superusuario_elige_sedes_dentro_del_grupo(self, client, grupo5):
        matriz, sedes = grupo5
        otro = EmpresaFactory(empresa_matriz=EmpresaFactory())
        client.force_login(_super())
        base = {'empresa_id': f'grupo-{matriz.id}'}
        r, codigos = self._ver(client, **base, sede=[matriz.id, sedes[1].id])
        assert codigos == {'E0', 'E2'} and r.context['sedes_filtro'] == [matriz] + sedes
        assert _codigos_excel(_excel(client, **base, sede=[matriz.id, sedes[1].id])) == {'E0', 'E2'}
        # Casillas que quedaron de otro grupo: se ignoran y se ve el grupo elegido completo
        assert self._ver(client, **base, sede=[otro.id])[1] == {f'E{i}' for i in range(6)}
