"""
Tests directos para core/templatetags/.

Cubre:
- math_filters.py: div, mul, abs_value, custom_zip (líneas 11-14, 22-25, 33-36, 44)
- custom_filters.py: sanitize_html, cop, mul, min_value, make_list, add, abs_value
  (líneas 43-55, 67-68, 73-76, 81-84, 89-92, 97-100, 105-108)
- file_tags.py: rutas None / sin archivo (líneas 18, 36, 46-47, 55-56, 64, 71-72, 112, 125-126)
"""
import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# math_filters
# ---------------------------------------------------------------------------

class TestMathFilters:
    """Tests para core/templatetags/math_filters.py."""

    def setup_method(self):
        from core.templatetags import math_filters
        self.div = math_filters.div
        self.mul = math_filters.mul
        self.abs_value = math_filters.abs_value
        self.custom_zip = math_filters.custom_zip

    # --- div ---
    def test_div_numeros_validos(self):
        assert self.div(10, 2) == 5.0

    def test_div_cadena_numerica(self):
        assert self.div('20', '4') == 5.0

    def test_div_por_cero(self):
        assert self.div(10, 0) == 0.0

    def test_div_valor_no_numerico(self):
        assert self.div('abc', 2) == 0.0

    def test_div_arg_no_numerico(self):
        assert self.div(10, 'xyz') == 0.0

    # --- mul ---
    def test_mul_numeros_validos(self):
        assert self.mul(3, 4) == 12.0

    def test_mul_cadena_numerica(self):
        assert self.mul('5', '6') == 30.0

    def test_mul_valor_no_numerico(self):
        assert self.mul('abc', 3) == 0.0

    def test_mul_arg_no_numerico(self):
        assert self.mul(3, None) == 0.0

    # --- abs_value ---
    def test_abs_value_negativo(self):
        assert self.abs_value(-7) == 7.0

    def test_abs_value_positivo(self):
        assert self.abs_value(5) == 5.0

    def test_abs_value_no_numerico(self):
        assert self.abs_value('abc') == 0.0

    def test_abs_value_none(self):
        assert self.abs_value(None) == 0.0

    # --- custom_zip ---
    def test_custom_zip_listas(self):
        result = list(self.custom_zip([1, 2, 3], ['a', 'b', 'c']))
        assert result == [(1, 'a'), (2, 'b'), (3, 'c')]

    def test_custom_zip_listas_vacias(self):
        result = list(self.custom_zip([], []))
        assert result == []


# ---------------------------------------------------------------------------
# custom_filters
# ---------------------------------------------------------------------------

class TestCustomFilters:
    """Tests para core/templatetags/custom_filters.py."""

    def setup_method(self):
        from core.templatetags import custom_filters
        self.sanitize_html = custom_filters.sanitize_html
        self.cop = custom_filters.cop
        self.mul = custom_filters.mul
        self.min_value = custom_filters.min_value
        self.make_list = custom_filters.make_list
        self.add = custom_filters.add
        self.abs_value = custom_filters.abs_value

    # --- sanitize_html ---
    def test_sanitize_html_vacio(self):
        assert self.sanitize_html('') == ''

    def test_sanitize_html_none(self):
        assert self.sanitize_html(None) == ''

    def test_sanitize_html_con_contenido(self):
        """Cubre la rama con nh3 (líneas 43-51)."""
        result = self.sanitize_html('<b>Texto</b>')
        # Debe retornar contenido marcado como seguro
        assert 'Texto' in str(result)

    def test_sanitize_html_strip_script(self):
        """nh3 elimina scripts."""
        result = self.sanitize_html('<script>alert("xss")</script><p>ok</p>')
        assert 'script' not in str(result)
        assert 'ok' in str(result)

    # --- cop ---
    def test_cop_entero(self):
        assert self.cop(200000) == '$200.000'

    def test_cop_string_numerico(self):
        assert self.cop('2000000') == '$2.000.000'

    def test_cop_valor_invalido(self):
        """Cubre except (ValueError, TypeError) en cop (líneas 67-68)."""
        result = self.cop('no-es-numero')
        assert result == 'no-es-numero'

    def test_cop_none(self):
        """None lanza TypeError → retorna value."""
        result = self.cop(None)
        assert result is None

    # --- mul ---
    def test_mul_enteros_validos(self):
        """Cubre líneas 73-74."""
        assert self.mul(4, 5) == 20

    def test_mul_valor_invalido(self):
        """Cubre líneas 75-76 (except)."""
        assert self.mul('abc', 3) == 0

    def test_mul_none(self):
        assert self.mul(None, 3) == 0

    # --- min_value ---
    def test_min_value_retorna_menor(self):
        """Cubre líneas 81-82."""
        assert self.min_value(3, 10) == 3

    def test_min_value_arg_es_menor(self):
        assert self.min_value(10, 5) == 5

    def test_min_value_invalido(self):
        """Cubre líneas 83-84 (except)."""
        result = self.min_value('abc', 10)
        assert result == 'abc'

    def test_min_value_none(self):
        result = self.min_value(None, 10)
        assert result is None

    # --- make_list ---
    def test_make_list_entero(self):
        """Cubre líneas 89-90."""
        assert self.make_list(3) == [1, 2, 3]

    def test_make_list_string_numerico(self):
        assert self.make_list('5') == [1, 2, 3, 4, 5]

    def test_make_list_invalido(self):
        """Cubre líneas 91-92 (except)."""
        assert self.make_list('abc') == []

    def test_make_list_cero(self):
        assert self.make_list(0) == []

    # --- add ---
    def test_add_enteros(self):
        """Cubre líneas 97-98."""
        assert self.add(5, 3) == 8

    def test_add_string_numerico(self):
        assert self.add('10', '20') == 30

    def test_add_invalido(self):
        """Cubre líneas 99-100 (except)."""
        result = self.add('abc', 3)
        assert result == 'abc'

    def test_add_none(self):
        result = self.add(None, 3)
        assert result is None

    # --- abs_value ---
    def test_abs_value_negativo(self):
        """Cubre líneas 105-106."""
        assert self.abs_value(-9) == 9

    def test_abs_value_positivo(self):
        assert self.abs_value(7) == 7

    def test_abs_value_invalido(self):
        """Cubre líneas 107-108 (except)."""
        result = self.abs_value('xyz')
        assert result == 'xyz'

    def test_abs_value_none(self):
        result = self.abs_value(None)
        assert result is None


# ---------------------------------------------------------------------------
# file_tags — rutas de retorno vacío/None (fáciles de cubrir)
# ---------------------------------------------------------------------------

class TestFileTags:
    """Tests para core/templatetags/file_tags.py — rutas None."""

    def setup_method(self):
        from core.templatetags import file_tags
        self.secure_file_url = file_tags.secure_file_url
        self.empresa_logo_url = file_tags.empresa_logo_url
        self.equipo_imagen_url = file_tags.equipo_imagen_url
        self.has_file = file_tags.has_file
        self.pdf_image_url = file_tags.pdf_image_url
        self.storage_quota_info = file_tags.storage_quota_info
        self.display_image = file_tags.display_image

    def test_secure_file_url_none(self):
        """Línea 18: file_field=None → retorna ''."""
        assert self.secure_file_url(None) == ''

    def test_secure_file_url_false(self):
        assert self.secure_file_url(False) == ''

    def test_secure_file_url_sin_name(self):
        """Línea 36: file_field sin atributo 'name' → retorna ''."""
        obj = MagicMock(spec=[])  # no tiene atributo 'name'
        result = self.secure_file_url(obj)
        assert result == ''

    def test_secure_file_url_name_vacio(self):
        """Línea 36: file_field.name es vacío → retorna ''."""
        obj = MagicMock()
        obj.name = ''
        result = self.secure_file_url(obj)
        assert result == ''

    def test_empresa_logo_url_none(self):
        """Líneas 46-47: empresa=None → retorna ''."""
        assert self.empresa_logo_url(None) == ''

    def test_empresa_logo_url_sin_logo(self):
        """Líneas 46-47: empresa sin logo_empresa → retorna ''."""
        empresa = MagicMock()
        empresa.logo_empresa = None
        assert self.empresa_logo_url(empresa) == ''

    def test_equipo_imagen_url_none(self):
        """Líneas 55-56: equipo=None → retorna ''."""
        assert self.equipo_imagen_url(None) == ''

    def test_equipo_imagen_url_sin_imagen(self):
        """Líneas 55-56: equipo sin imagen_equipo → retorna ''."""
        equipo = MagicMock()
        equipo.imagen_equipo = None
        assert self.equipo_imagen_url(equipo) == ''

    def test_has_file_none(self):
        """Línea 64: file_field=None → False."""
        assert self.has_file(None) is False

    def test_has_file_sin_name(self):
        """Línea 64: objeto sin atributo name → False."""
        assert self.has_file(object()) is False

    def test_has_file_name_vacio(self):
        """Línea 64: name vacío → False."""
        obj = MagicMock()
        obj.name = ''
        assert self.has_file(obj) is False

    def test_has_file_con_name(self):
        """Línea 64: campo con name → True."""
        obj = MagicMock()
        obj.name = 'archivo.pdf'
        assert self.has_file(obj) is True

    def test_pdf_image_url_none(self):
        """Líneas 71-72: file_field=None → retorna ''."""
        assert self.pdf_image_url(None) == ''

    def test_pdf_image_url_false(self):
        assert self.pdf_image_url(False) == ''

    def test_storage_quota_info_none(self):
        """Líneas 125-126: empresa=None → retorna {}."""
        assert self.storage_quota_info(None) == {}

    def test_display_image_none(self):
        """Líneas 112-118: file_field=None → retorna dict con image_url=''."""
        result = self.display_image(None)
        assert isinstance(result, dict)
        assert result['image_url'] == ''
        assert result['has_image'] is False
