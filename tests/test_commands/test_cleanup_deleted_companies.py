"""
Tests para el comando cleanup_deleted_companies — borrado permanente de
empresas eliminadas hace 180+ días, junto con sus usuarios huérfanos.
"""
import pytest
from datetime import timedelta
from io import StringIO
from django.core.management import call_command
from django.utils import timezone

from core.models import Empresa, CustomUser
from tests.factories import EmpresaFactory, UserFactory


def _soft_delete_hace(empresa, dias):
    empresa.soft_delete(reason='Test')
    empresa.deleted_at = timezone.now() - timedelta(days=dias)
    empresa.save(update_fields=['deleted_at'])


@pytest.mark.django_db
class TestCleanupDeletedCompanies:

    def test_dry_run_no_borra_nada(self):
        empresa = EmpresaFactory()
        _soft_delete_hace(empresa, 200)

        call_command('cleanup_deleted_companies', stdout=StringIO())

        assert Empresa.objects.filter(pk=empresa.pk).exists()

    def test_no_elimina_antes_de_180_dias(self):
        empresa = EmpresaFactory()
        _soft_delete_hace(empresa, 30)

        call_command('cleanup_deleted_companies', execute=True, stdout=StringIO())

        assert Empresa.objects.filter(pk=empresa.pk).exists()

    def test_elimina_empresa_despues_de_180_dias(self):
        empresa = EmpresaFactory()
        _soft_delete_hace(empresa, 200)

        call_command('cleanup_deleted_companies', execute=True, stdout=StringIO())

        assert not Empresa.objects.filter(pk=empresa.pk).exists()

    def test_borra_usuarios_huerfanos_junto_con_la_empresa(self):
        empresa = EmpresaFactory()
        usuario = UserFactory(empresa=empresa)
        _soft_delete_hace(empresa, 200)

        call_command('cleanup_deleted_companies', execute=True, stdout=StringIO())

        assert not CustomUser.objects.filter(pk=usuario.pk).exists()

    def test_no_toca_usuarios_de_otras_empresas(self):
        empresa_a_borrar = EmpresaFactory()
        empresa_activa = EmpresaFactory()
        usuario_activo = UserFactory(empresa=empresa_activa)
        _soft_delete_hace(empresa_a_borrar, 200)

        call_command('cleanup_deleted_companies', execute=True, stdout=StringIO())

        assert CustomUser.objects.filter(pk=usuario_activo.pk).exists()
        assert Empresa.objects.filter(pk=empresa_activa.pk).exists()

    def test_dry_run_no_borra_usuarios(self):
        empresa = EmpresaFactory()
        usuario = UserFactory(empresa=empresa)
        _soft_delete_hace(empresa, 200)

        call_command('cleanup_deleted_companies', stdout=StringIO())

        assert CustomUser.objects.filter(pk=usuario.pk).exists()

    def test_company_id_especifico(self):
        empresa = EmpresaFactory()
        _soft_delete_hace(empresa, 200)

        call_command('cleanup_deleted_companies', execute=True, company_id=empresa.pk, stdout=StringIO())

        assert not Empresa.objects.filter(pk=empresa.pk).exists()

    def test_dias_personalizados(self):
        empresa = EmpresaFactory()
        _soft_delete_hace(empresa, 95)

        # Con retención de 90 días, ya está elegible aunque no lleve 180
        call_command('cleanup_deleted_companies', execute=True, days=90, stdout=StringIO())

        assert not Empresa.objects.filter(pk=empresa.pk).exists()
