#!/usr/bin/env python
"""
TEST INTEGRAL SIMPLIFICADO - SAM METROLOGIA
==========================================
Script para detectar errores antes del despliegue
"""

import os
import sys
import django
from datetime import datetime, date, timedelta
import random
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from core.models import (
    Empresa, Equipo, Proveedor, Procedimiento, Ubicacion,
    Calibracion, Mantenimiento, Comprobacion, CustomUser
)

class TestSimple:
    def __init__(self):
        self.resultados = {
            'empresas': 0,
            'equipos': 0,
            'proveedores': 0,
            'actividades': 0,
            'errores': [],
            'tests_ok': 0,
            'tests_error': 0
        }

    def ejecutar_test(self):
        print("="*50)
        print("TEST INTEGRAL SAM METROLOGIA")
        print("="*50)
        print(f"Inicio: {datetime.now()}")

        try:
            self.limpiar_datos_anteriores()
            self.crear_datos_test()
            self.test_funcionalidades()
            self.mostrar_resultados()
        except Exception as e:
            print(f"ERROR CRITICO: {e}")
            self.resultados['errores'].append(str(e))

    def limpiar_datos_anteriores(self):
        print("\n1. Limpiando datos anteriores...")
        try:
            # Eliminar datos de test previos
            Empresa.objects.filter(nombre__startswith='TEST_').delete()
            Proveedor.objects.filter(nombre_empresa__startswith='TEST_').delete()
            CustomUser.objects.filter(username__startswith='test_').delete()
            print("   [OK] Datos anteriores eliminados")
        except Exception as e:
            print(f"   [ERROR] {e}")
            self.resultados['errores'].append(f"Limpieza: {e}")

    def crear_datos_test(self):
        print("\n2. Creando datos de prueba...")

        # Crear 5 empresas
        self.crear_empresas()

        # Crear proveedores
        self.crear_proveedores()

        # Crear equipos masivos
        self.crear_equipos()

        # Crear actividades
        self.crear_actividades()

    def crear_empresas(self):
        print("   2.1 Creando 5 empresas...")
        import time
        timestamp = int(time.time())
        empresas_data = [
            {'nombre': 'TEST_MetroTech S.A.S', 'nit': f'900{timestamp}-1'},
            {'nombre': 'TEST_InduCal Ltda', 'nit': f'800{timestamp}-2'},
            {'nombre': 'TEST_PreciMed S.A.', 'nit': f'890{timestamp}-3'},
            {'nombre': 'TEST_QualityMet', 'nit': f'901{timestamp}-4'},
            {'nombre': 'TEST_TecnoMetro', 'nit': f'892{timestamp}-5'}
        ]

        self.empresas = []
        for data in empresas_data:
            try:
                empresa = Empresa.objects.create(
                    nombre=data['nombre'],
                    nit=data['nit'],
                    direccion='Calle Test 123',
                    telefono='1234567',
                    email='test@test.com',
                    limite_equipos_empresa=50,
                    limite_almacenamiento_mb=500,
                    estado_suscripcion='Activo',
                    fecha_inicio_plan=date.today()
                )
                self.empresas.append(empresa)
                self.resultados['empresas'] += 1

                # Crear ubicaciones
                for i in range(2):
                    Ubicacion.objects.create(
                        nombre=f'Ubicacion {i+1} - {empresa.nombre}',
                        descripcion='Test Location Description',
                        empresa=empresa
                    )

            except Exception as e:
                self.resultados['errores'].append(f"Error empresa {data['nombre']}: {e}")

        print(f"       [OK] {len(self.empresas)} empresas creadas")

    def crear_proveedores(self):
        print("   2.2 Creando 10 proveedores...")
        self.proveedores = []
        if not self.empresas:
            print("       [ERROR] No hay empresas creadas para asignar proveedores")
            return

        import time
        timestamp = int(time.time())

        for i in range(10):
            try:
                empresa = random.choice(self.empresas)
                proveedor = Proveedor.objects.create(
                    nombre_empresa=f'TEST_Proveedor_{timestamp}_{i+1}',
                    empresa=empresa,
                    tipo_servicio='Calibración',
                    nombre_contacto='Contacto Test',
                    numero_contacto='123456789',
                    correo_electronico=f'proveedor{timestamp}{i}@test.com',
                    alcance='Instrumentos de medición general',
                    servicio_prestado='Calibración y mantenimiento de equipos'
                )
                self.proveedores.append(proveedor)
                self.resultados['proveedores'] += 1
            except Exception as e:
                self.resultados['errores'].append(f"Error proveedor {i}: {e}")

        print(f"       [OK] {len(self.proveedores)} proveedores creados")

    def crear_equipos(self):
        print("   2.3 Creando 150+ equipos...")
        self.equipos = []

        tipos = ['Multimetro', 'Balanza', 'Termometro', 'Osciloscopio', 'pH Metro']
        marcas = ['Fluke', 'Mettler', 'Testo', 'Keysight', 'Omega']

        for empresa in self.empresas:
            ubicaciones = Ubicacion.objects.filter(empresa=empresa)
            equipos_por_empresa = random.randint(30, 40)

            for i in range(equipos_por_empresa):
                try:
                    equipo = Equipo.objects.create(
                        codigo_interno=f'EQ-{empresa.id}-{i+1:03d}',
                        nombre=f'{random.choice(tipos)} {random.choice(marcas)}',
                        empresa=empresa,
                        marca=random.choice(marcas),
                        modelo=f'Model-{random.randint(1000, 9999)}',
                        numero_serie=f'SN{random.randint(100000, 999999)}',
                        ubicacion=random.choice(ubicaciones).nombre if ubicaciones else 'Almacén Principal',
                        responsable='Tecnico Test',
                        estado=random.choice(['Activo', 'Activo', 'Activo', 'Inactivo']),
                        fecha_adquisicion=date.today() - timedelta(days=random.randint(30, 730)),
                        frecuencia_calibracion_meses=12,
                        frecuencia_mantenimiento_meses=6,
                        frecuencia_comprobacion_meses=3
                    )

                    # Calcular próximas fechas
                    equipo.calcular_proxima_calibracion()
                    equipo.calcular_proximo_mantenimiento()
                    equipo.calcular_proxima_comprobacion()
                    equipo.save()

                    self.equipos.append(equipo)
                    self.resultados['equipos'] += 1

                except Exception as e:
                    self.resultados['errores'].append(f"Error equipo {i}: {e}")

            print(f"       Empresa {empresa.nombre}: {equipos_por_empresa} equipos")

        print(f"       [OK] {len(self.equipos)} equipos totales creados")

    def crear_actividades(self):
        print("   2.4 Creando actividades...")

        if not self.equipos:
            print("       [ERROR] No hay equipos creados")
            return

        if not self.proveedores:
            print("       [ERROR] No hay proveedores creados para actividades")
            return

        # Crear actividades para 50% de equipos
        equipos_con_actividades = random.sample(self.equipos, len(self.equipos) // 2)

        for equipo in equipos_con_actividades:
            try:
                proveedor = random.choice(self.proveedores)

                # 70% probabilidad de calibración
                if random.random() < 0.7:
                    Calibracion.objects.create(
                        equipo=equipo,
                        fecha_calibracion=date.today() - timedelta(days=random.randint(1, 365)),
                        proveedor=proveedor,
                        nombre_proveedor=proveedor.nombre_empresa,
                        resultado='Conforme',
                        numero_certificado=f'CERT-{random.randint(100000, 999999)}'
                    )
                    self.resultados['actividades'] += 1

                # 50% probabilidad de mantenimiento
                if random.random() < 0.5:
                    Mantenimiento.objects.create(
                        equipo=equipo,
                        fecha_mantenimiento=date.today() - timedelta(days=random.randint(1, 180)),
                        tipo_mantenimiento='Preventivo',
                        proveedor=proveedor,
                        nombre_proveedor=proveedor.nombre_empresa,
                        responsable='Tecnico Test',
                        costo=Decimal('100000.00')
                    )
                    self.resultados['actividades'] += 1

                # 30% probabilidad de comprobación
                if random.random() < 0.3:
                    Comprobacion.objects.create(
                        equipo=equipo,
                        fecha_comprobacion=date.today() - timedelta(days=random.randint(1, 90)),
                        proveedor=proveedor,
                        nombre_proveedor=proveedor.nombre_empresa,
                        responsable='QC Test',
                        resultado='Satisfactorio'
                    )
                    self.resultados['actividades'] += 1

            except Exception as e:
                self.resultados['errores'].append(f"Error actividad equipo {equipo.codigo_interno}: {e}")

        print(f"       [OK] {self.resultados['actividades']} actividades creadas")

    def test_funcionalidades(self):
        print("\n3. Probando funcionalidades criticas...")

        tests = [
            ("Import views modulares", self.test_views_import),
            ("Queries equipos optimizadas", self.test_queries_equipos),
            ("Calculo fechas automatico", self.test_calculo_fechas),
            ("Filtros de equipos", self.test_filtros),
            ("Validaciones empresa", self.test_validaciones),
            ("Integridad de datos", self.test_integridad)
        ]

        for nombre, test_func in tests:
            try:
                print(f"   3.{tests.index((nombre, test_func)) + 1} {nombre}...")
                resultado = test_func()
                if resultado:
                    print(f"       [OK] {nombre}")
                    self.resultados['tests_ok'] += 1
                else:
                    print(f"       [ERROR] {nombre}")
                    self.resultados['tests_error'] += 1
            except Exception as e:
                print(f"       [ERROR] {nombre}: {e}")
                self.resultados['tests_error'] += 1
                self.resultados['errores'].append(f"{nombre}: {e}")

    def test_views_import(self):
        """Test import views modulares"""
        try:
            # Test modular views import
            from core.views import dashboard, equipment, activities, companies, reports
            # Test classic views that should exist
            from core.views import listar_empresas
            return True
        except Exception as e:
            self.resultados['errores'].append(f"Views import error: {e}")
            return False

    def test_queries_equipos(self):
        """Test queries optimizadas"""
        try:
            from core.optimizations import OptimizedQueries
            equipos = OptimizedQueries.get_equipos_optimized()
            return equipos.count() > 0
        except:
            return False

    def test_calculo_fechas(self):
        """Test cálculo de fechas automático"""
        try:
            if not self.equipos:
                return False
            equipo = self.equipos[0]
            equipo.calcular_proxima_calibracion()
            return True
        except:
            return False

    def test_filtros(self):
        """Test filtros de equipos"""
        try:
            activos = Equipo.objects.filter(estado='Activo').count()
            return activos > 0
        except:
            return False

    def test_validaciones(self):
        """Test validaciones de empresa"""
        try:
            if not self.empresas:
                return False
            empresa = self.empresas[0]
            limite = empresa.get_limite_equipos()
            return limite is not None
        except:
            return False

    def test_integridad(self):
        """Test integridad de datos"""
        try:
            equipos_sin_empresa = Equipo.objects.filter(empresa__isnull=True).count()
            return equipos_sin_empresa == 0
        except:
            return False

    def mostrar_resultados(self):
        print("\n" + "="*50)
        print("RESULTADOS FINALES")
        print("="*50)

        print(f"Empresas creadas: {self.resultados['empresas']}")
        print(f"Equipos creados: {self.resultados['equipos']}")
        print(f"Proveedores creados: {self.resultados['proveedores']}")
        print(f"Actividades creadas: {self.resultados['actividades']}")

        print(f"\nTests pasados: {self.resultados['tests_ok']}")
        print(f"Tests fallidos: {self.resultados['tests_error']}")

        if self.resultados['errores']:
            print(f"\nErrores encontrados ({len(self.resultados['errores'])}):")
            for i, error in enumerate(self.resultados['errores'][:5], 1):
                print(f"  {i}. {error}")
            if len(self.resultados['errores']) > 5:
                print(f"  ... y {len(self.resultados['errores']) - 5} más")

        # Score final
        total_tests = self.resultados['tests_ok'] + self.resultados['tests_error']
        if total_tests > 0:
            score = (self.resultados['tests_ok'] / total_tests) * 100
        else:
            score = 0

        print(f"\nSCORE FINAL: {score:.1f}%")

        if score >= 90:
            print("VEREDICTO: SISTEMA LISTO PARA PRODUCCION")
        elif score >= 70:
            print("VEREDICTO: REVISAR ERRORES ANTES DE DEPLOY")
        else:
            print("VEREDICTO: NO DESPLEGAR - ERRORES CRITICOS")

        print(f"\nFin: {datetime.now()}")
        print("="*50)

if __name__ == "__main__":
    test = TestSimple()
    test.ejecutar_test()