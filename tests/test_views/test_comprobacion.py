"""
Tests para comprobacion.py
"""
import pytest
import json
from datetime import date
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from core.models import Empresa, CustomUser, Equipo, Comprobacion
from core.views.comprobacion import safe_float, guardar_comprobacion_json

@pytest.fixture
def empresa_test():
    return Empresa.objects.create(nombre='Test',nit='900333444-5',email='test@test.com')

@pytest.fixture
def usuario_test(empresa_test):
    return CustomUser.objects.create_user(username='test',email='test@test.com',password='test',empresa=empresa_test)

@pytest.fixture
def equipo_test(empresa_test):
    return Equipo.objects.create(empresa=empresa_test,codigo_interno='EQ-001',nombre='Test',estado='Activo')

@pytest.fixture
def comprobacion_test(equipo_test):
    return Comprobacion.objects.create(equipo=equipo_test,fecha_comprobacion=date.today(),resultado='Aprobado',datos_comprobacion={'puntos_medicion':[{'nominal':50,'conformidad':'CONFORME'}]})

@pytest.fixture
def request_factory():
    return RequestFactory()

class TestSafeFloat:
    def test_safe_float_numero_valido(self):
        assert safe_float('123.45') == 123.45
    def test_safe_float_none(self):
        assert safe_float(None) == 0.0
    def test_safe_float_string_vacio(self):
        assert safe_float('') == 0.0
    def test_safe_float_invalido(self):
        assert safe_float('abc') == 0.0
    def test_safe_float_string_numerico(self):
        assert safe_float('42.5') == 42.5
    def test_safe_float_default_custom(self):
        assert safe_float('invalid', 99.9) == 99.9

@pytest.mark.django_db
class TestGuardarComprobacionJSON:
    def test_crear_nueva_comprobacion(self, request_factory, usuario_test, equipo_test):
        datos = {'puntos_medicion':[{'nominal':50,'conformidad':'CONFORME'}]}
        request = request_factory.post('/', data=json.dumps(datos), content_type='application/json')
        request.user = usuario_test
        response = guardar_comprobacion_json(request, equipo_test.id)
        assert response.status_code == 200
        assert json.loads(response.content)['success'] is True

    def test_actualizar_existente(self, request_factory, usuario_test, equipo_test, comprobacion_test):
        datos = {'comprobacion_id': comprobacion_test.id, 'puntos_medicion':[{'nominal':75,'conformidad':'CONFORME'}]}
        request = request_factory.post('/', data=json.dumps(datos), content_type='application/json')
        request.user = usuario_test
        response = guardar_comprobacion_json(request, equipo_test.id)
        assert response.status_code == 200

    def test_resultado_aprobado(self, request_factory, usuario_test, equipo_test):
        datos = {'puntos_medicion':[{'conformidad':'CONFORME'},{'conformidad':'CONFORME'}]}
        request = request_factory.post('/', data=json.dumps(datos), content_type='application/json')
        request.user = usuario_test
        response = guardar_comprobacion_json(request, equipo_test.id)
        comp = Comprobacion.objects.get(id=json.loads(response.content)['comprobacion_id'])
        assert comp.resultado == 'Aprobado'

    def test_resultado_no_aprobado(self, request_factory, usuario_test, equipo_test):
        datos = {'puntos_medicion':[{'conformidad':'CONFORME'},{'conformidad':'NO CONFORME'}]}
        request = request_factory.post('/', data=json.dumps(datos), content_type='application/json')
        request.user = usuario_test
        response = guardar_comprobacion_json(request, equipo_test.id)
        comp = Comprobacion.objects.get(id=json.loads(response.content)['comprobacion_id'])
        assert comp.resultado == 'No Aprobado'

    def test_sin_autenticacion(self, request_factory, equipo_test):
        request = request_factory.post('/', data=json.dumps({}), content_type='application/json')
        request.user = AnonymousUser()
        response = guardar_comprobacion_json(request, equipo_test.id)
        assert response.status_code == 302

    def test_multitenancy(self, request_factory, usuario_test):
        otra = Empresa.objects.create(nombre='Otra',nit='999')
        otro = Equipo.objects.create(empresa=otra,codigo_interno='EQ-OTRO',nombre='Otro')
        request = request_factory.post('/', data=json.dumps({}), content_type='application/json')
        request.user = usuario_test
        response = guardar_comprobacion_json(request, otro.id)
        # La función captura Http404 y retorna JsonResponse con error 500
        assert response.status_code == 500
        assert json.loads(response.content)['success'] is False

    def test_json_invalido(self, request_factory, usuario_test, equipo_test):
        request = request_factory.post('/', data='invalid', content_type='application/json')
        request.user = usuario_test
        response = guardar_comprobacion_json(request, equipo_test.id)
        assert response.status_code == 500

    def test_puntos_vacios(self, request_factory, usuario_test, equipo_test):
        datos = {'puntos_medicion':[]}
        request = request_factory.post('/', data=json.dumps(datos), content_type='application/json')
        request.user = usuario_test
        response = guardar_comprobacion_json(request, equipo_test.id)
        assert response.status_code == 200

@pytest.mark.django_db
class TestEdgeCases:
    def test_sin_conformidad(self, request_factory, usuario_test, equipo_test):
        datos = {'puntos_medicion':[{'nominal':10}]}
        request = request_factory.post('/', data=json.dumps(datos), content_type='application/json')
        request.user = usuario_test
        response = guardar_comprobacion_json(request, equipo_test.id)
        assert response.status_code == 200

    def test_comprobacion_inexistente(self, request_factory, usuario_test, equipo_test):
        datos = {'comprobacion_id': 99999, 'puntos_medicion':[]}
        request = request_factory.post('/', data=json.dumps(datos), content_type='application/json')
        request.user = usuario_test
        response = guardar_comprobacion_json(request, equipo_test.id)
        # La función captura la excepción y retorna JsonResponse con error 500
        assert response.status_code == 500
        assert json.loads(response.content)['success'] is False

    def test_datos_numericos_extremos(self, request_factory, usuario_test, equipo_test):
        datos = {'puntos_medicion':[{'nominal':0.0001},{'nominal':999999.999}]}
        request = request_factory.post('/', data=json.dumps(datos), content_type='application/json')
        request.user = usuario_test
        response = guardar_comprobacion_json(request, equipo_test.id)
        assert response.status_code == 200
