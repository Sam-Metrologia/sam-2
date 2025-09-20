# core/tests/test_storage.py
# Tests específicos para cálculo de almacenamiento

from django.test import TestCase
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from unittest.mock import Mock, patch
from core.models import Empresa, Equipo, Calibracion, Mantenimiento, Comprobacion


class StorageCalculationTest(TestCase):
    """Tests para cálculos de almacenamiento."""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa Storage Test",
            nit="storage123",
            limite_almacenamiento_mb=100
        )

        self.equipo = Equipo.objects.create(
            codigo_interno="STOR001",
            nombre="Equipo Storage",
            empresa=self.empresa,
            tipo_equipo="Equipo de Medición"
        )

    @patch('django.core.files.storage.default_storage.exists')
    @patch('django.core.files.storage.default_storage.size')
    def test_storage_calculation_with_files(self, mock_size, mock_exists):
        """Test cálculo de storage con archivos simulados."""
        # Mock responses
        mock_exists.return_value = True
        mock_size.return_value = 1024 * 1024  # 1MB

        # Simular logo de empresa
        self.empresa.logo_empresa = Mock()
        self.empresa.logo_empresa.name = 'test_logo.png'

        # Simular archivo de equipo
        self.equipo.archivo_compra_pdf = Mock()
        self.equipo.archivo_compra_pdf.name = 'test_doc.pdf'
        self.equipo.save()

        # Crear calibración con archivo
        calibracion = Calibracion.objects.create(
            equipo=self.equipo,
            fecha_calibracion="2023-01-15",
            resultado="Aprobado"
        )
        calibracion.documento_calibracion = Mock()
        calibracion.documento_calibracion.name = 'test_cal.pdf'

        # Calcular storage
        total_mb = self.empresa.get_total_storage_used_mb()

        # Verificar que se calculó correctamente
        # 3 archivos × 1MB cada uno = 3MB
        self.assertEqual(total_mb, 3.0)

        # Verificar porcentaje
        percentage = self.empresa.get_storage_usage_percentage()
        self.assertEqual(percentage, 3.0)  # 3MB de 100MB = 3%

    def test_storage_calculation_no_files(self):
        """Test cálculo de storage sin archivos."""
        total_mb = self.empresa.get_total_storage_used_mb()
        self.assertEqual(total_mb, 0.0)

        percentage = self.empresa.get_storage_usage_percentage()
        self.assertEqual(percentage, 0.0)

    @patch('django.core.files.storage.default_storage.exists')
    @patch('django.core.files.storage.default_storage.size')
    def test_storage_calculation_with_errors(self, mock_size, mock_exists):
        """Test que los errores en cálculo no rompen el sistema."""
        # Simular error en storage.exists()
        mock_exists.side_effect = Exception("Storage error")

        # Agregar archivo a equipo
        self.equipo.archivo_compra_pdf = Mock()
        self.equipo.archivo_compra_pdf.name = 'test_doc.pdf'
        self.equipo.save()

        # El cálculo debe funcionar sin errores (manejando la excepción)
        total_mb = self.empresa.get_total_storage_used_mb()
        self.assertEqual(total_mb, 0.0)  # Debe retornar 0 por los errores

    def test_storage_status_boundaries(self):
        """Test límites exactos de clases de estado de storage."""
        # Test límites específicos
        test_cases = [
            (0, 'text-green-700'),     # 0%
            (49, 'text-green-700'),    # 49%
            (50, 'text-orange-700'),   # 50%
            (74, 'text-orange-700'),   # 74%
            (75, 'text-yellow-700'),   # 75%
            (89, 'text-yellow-700'),   # 89%
            (90, 'text-red-700'),      # 90%
            (100, 'text-red-700'),     # 100%
        ]

        for percentage, expected_class in test_cases:
            with patch.object(self.empresa, 'get_storage_usage_percentage', return_value=percentage):
                status_class = self.empresa.get_storage_status_class()
                self.assertIn(expected_class, status_class,
                            f"Percentage {percentage}% should return class containing {expected_class}")

    def test_storage_calculation_multiple_file_types(self):
        """Test cálculo con múltiples tipos de archivos."""
        with patch('django.core.files.storage.default_storage.exists', return_value=True), \
             patch('django.core.files.storage.default_storage.size', return_value=512 * 1024):  # 0.5MB cada archivo

            # Logo empresa
            self.empresa.logo_empresa = Mock()
            self.empresa.logo_empresa.name = 'logo.png'

            # Múltiples archivos de equipo
            self.equipo.archivo_compra_pdf = Mock()
            self.equipo.archivo_compra_pdf.name = 'compra.pdf'

            self.equipo.manual_pdf = Mock()
            self.equipo.manual_pdf.name = 'manual.pdf'

            self.equipo.imagen_equipo = Mock()
            self.equipo.imagen_equipo.name = 'imagen.jpg'
            self.equipo.save()

            # Calibración con múltiples archivos
            calibracion = Calibracion.objects.create(
                equipo=self.equipo,
                fecha_calibracion="2023-01-15",
                resultado="Aprobado"
            )
            calibracion.documento_calibracion = Mock()
            calibracion.documento_calibracion.name = 'cal_doc.pdf'

            calibracion.confirmacion_metrologica_pdf = Mock()
            calibracion.confirmacion_metrologica_pdf.name = 'cal_conf.pdf'

            # Mantenimiento
            mantenimiento = Mantenimiento.objects.create(
                equipo=self.equipo,
                fecha_mantenimiento="2023-02-15",
                tipo_mantenimiento="Preventivo"
            )
            mantenimiento.documento_mantenimiento = Mock()
            mantenimiento.documento_mantenimiento.name = 'mant_doc.pdf'

            # Comprobación
            comprobacion = Comprobacion.objects.create(
                equipo=self.equipo,
                fecha_comprobacion="2023-03-15",
                resultado="Aprobado"
            )
            comprobacion.documento_comprobacion = Mock()
            comprobacion.documento_comprobacion.name = 'comp_doc.pdf'

            # Calcular storage total
            total_mb = self.empresa.get_total_storage_used_mb()

            # 8 archivos × 0.5MB = 4MB total
            self.assertEqual(total_mb, 4.0)

    def test_storage_percentage_edge_cases(self):
        """Test casos extremos de porcentajes de storage."""
        # Límite 0 (debería retornar 0% para evitar división por cero)
        self.empresa.limite_almacenamiento_mb = 0
        percentage = self.empresa.get_storage_usage_percentage()
        self.assertEqual(percentage, 0)

        # Usage mayor al límite (debería retornar máximo 100%)
        with patch.object(self.empresa, 'get_total_storage_used_mb', return_value=150.0):
            self.empresa.limite_almacenamiento_mb = 100
            percentage = self.empresa.get_storage_usage_percentage()
            self.assertEqual(percentage, 100)  # Máximo 100%