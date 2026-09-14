"""
Tests para los signals de core/signals.py que borran del storage los
archivos reales (FileField/ImageField) al eliminar un registro.

Antes de esto, borrar un registro (Equipo, Calibracion, Empresa, etc.)
solo quitaba la fila de la base de datos — el archivo seguía existiendo
en el storage para siempre, huérfano.
"""
import pytest
from django.core.files.storage import default_storage

from core.models import Equipo, Documento
from tests.factories import EmpresaFactory, EquipoFactory


@pytest.mark.django_db
class TestLimpiezaDeArchivosAlEliminar:

    def test_borrar_equipo_borra_su_imagen_del_storage(self, sample_image):
        empresa = EmpresaFactory()
        equipo = EquipoFactory(empresa=empresa)
        equipo.imagen_equipo = sample_image
        equipo.save()
        ruta = equipo.imagen_equipo.name

        assert default_storage.exists(ruta)

        equipo.delete()

        assert not default_storage.exists(ruta)

    def test_borrar_empresa_borra_su_logo_del_storage(self, sample_image):
        empresa = EmpresaFactory()
        empresa.logo_empresa = sample_image
        empresa.save()
        ruta = empresa.logo_empresa.name

        assert default_storage.exists(ruta)

        empresa.delete()

        assert not default_storage.exists(ruta)

    def test_borrar_empresa_en_cascada_borra_imagenes_de_sus_equipos(self, sample_image):
        """El caso real: borrar la empresa completa (cleanup de 180 días) debe
        limpiar también los archivos de todo lo que se borra en cascada."""
        empresa = EmpresaFactory()
        equipo = EquipoFactory(empresa=empresa)
        equipo.imagen_equipo = sample_image
        equipo.save()
        ruta = equipo.imagen_equipo.name

        assert default_storage.exists(ruta)

        empresa.delete()

        assert not default_storage.exists(ruta)
        assert not Equipo.objects.filter(pk=equipo.pk).exists()

    def test_borrar_documento_borra_su_archivo_del_storage(self, sample_pdf):
        empresa = EmpresaFactory()
        ruta = 'pdfs/documento_test.pdf'
        default_storage.save(ruta, sample_pdf)
        documento = Documento.objects.create(
            nombre_archivo='documento_test.pdf',
            archivo_s3_path=ruta,
            empresa=empresa,
        )

        assert default_storage.exists(ruta)

        documento.delete()

        assert not default_storage.exists(ruta)

    def test_equipo_sin_archivo_se_borra_sin_error(self):
        """No debe reventar si el equipo nunca tuvo imagen."""
        equipo = EquipoFactory()
        equipo.delete()  # no debe lanzar excepción
